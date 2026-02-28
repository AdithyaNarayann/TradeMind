"""
Voice Call Routes — WebSocket endpoint for real-time voice negotiation.

Protocol:
    Client → Server:
        { type: "audio", data: "<base64 PCM 16kHz>" }
        { type: "end_call" }
        { type: "flush" }
        { type: "ping" }

    Server → Client:
        { type: "user_transcript", text: "...", is_final: bool }
        { type: "ai_transcript", text: "...", pricing: {...} }
        { type: "ai_audio", data: "<base64 audio>", content_type: "audio/wav" }
        { type: "ai_audio_end" }
        { type: "status", status: "connecting"|"listening"|"processing"|"speaking" }
        { type: "error", message: "..." }
        { type: "pong", ts: <server_ms> }
"""
import asyncio
import json
import time
from uuid import UUID

import jwt as pyjwt
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from fastapi.responses import JSONResponse
import structlog

from ..core.config import get_settings
from ..core.engine import NegotiationEngine
from .voice_handler import VoiceCallHandler

logger = structlog.get_logger(__name__)
settings = get_settings()

voice_router = APIRouter(prefix="/api/v1/voice", tags=["Voice Call"])


def _verify_ws_token(token: str) -> dict:
    """Verify JWT token for WebSocket connections (no Depends available)."""
    if not token:
        return None
    try:
        payload = pyjwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
        return {
            "id": int(payload["sub"]),
            "email": payload.get("email", ""),
            "full_name": payload.get("full_name", ""),
        }
    except pyjwt.ExpiredSignatureError:
        return None
    except pyjwt.InvalidTokenError:
        return None


@voice_router.get("/health")
async def voice_health():
    """Check if voice call feature is available."""
    has_key = bool(settings.sarvam_api_key)
    return {
        "voice_available": has_key,
        "stt_model": settings.sarvam_stt_model,
        "tts_model": settings.sarvam_tts_model,
        "language": settings.sarvam_language,
    }


@voice_router.get("/validate/{session_id}")
async def validate_voice_session(session_id: str):
    """
    Validate that a session exists and is active before starting a voice call.
    Call this before opening the WebSocket.
    """
    try:
        engine = NegotiationEngine()
        session_uuid = UUID(session_id)
        session = engine.session_manager.get_session(session_uuid)
        if session is None:
            return JSONResponse(
                status_code=404,
                content={"valid": False, "error": "Session not found or expired"},
            )
        return {
            "valid": True,
            "session_id": session_id,
            "product_name": session.product.product_name,
            "current_round": session.pricing_state.current_round if session.pricing_state else 0,
            "max_rounds": session.strategy.max_rounds,
        }
    except Exception as e:
        return JSONResponse(
            status_code=400,
            content={"valid": False, "error": str(e)},
        )


@voice_router.websocket("/ws/{session_id}")
async def voice_call_websocket(websocket: WebSocket, session_id: str, token: str = Query(default="")):
    """
    Full-duplex voice call WebSocket endpoint.

    Accepts `?token=<jwt>` query param for authentication.

    Flow:
    1. Client connects with JWT token
    2. Server validates token + session
    3. Server opens Sarvam STT + TTS WebSockets
    4. Bidirectional audio streaming begins
    5. On disconnect or end_call, everything is cleaned up
    """
    # ── JWT Authentication (optional — session validation is the real gate) ──
    user = _verify_ws_token(token) if token else None
    if user:
        logger.info("voice_ws_authenticated", session_id=session_id, user_id=user["id"])
    else:
        logger.info("voice_ws_anonymous", session_id=session_id)

    await websocket.accept()
    logger.info("voice_ws_connected", session_id=session_id)

    # Validate session exists
    try:
        engine = NegotiationEngine()
        session_uuid = UUID(session_id)
        session = engine.session_manager.get_session(session_uuid)
        if session is None:
            await websocket.send_json({
                "type": "error",
                "message": "Session not found or expired. Please start a new negotiation.",
            })
            await websocket.close(code=4004, reason="Session not found")
            return
    except Exception as e:
        await websocket.send_json({
            "type": "error",
            "message": f"Invalid session: {str(e)}",
        })
        await websocket.close(code=4000, reason="Invalid session")
        return

    # Check Sarvam API key
    if not settings.sarvam_api_key:
        await websocket.send_json({
            "type": "error",
            "message": "Voice service not configured. Please set SARVAM_API_KEY.",
        })
        await websocket.close(code=4003, reason="Voice not configured")
        return

    # Create handler and start the call
    handler = VoiceCallHandler(session_id=session_id, client_ws=websocket)

    # Run handler.start() and client receive loop concurrently
    async def client_receive_loop():
        """Read messages from client and forward to handler."""
        try:
            while handler.is_active:
                raw = await websocket.receive_text()
                await handler.handle_client_message(raw)
        except WebSocketDisconnect:
            logger.info("voice_ws_disconnected", session_id=session_id)
            handler.is_active = False
        except Exception as e:
            logger.error("voice_ws_receive_error", error=str(e))
            handler.is_active = False

    try:
        # Run both concurrently: the handler's main loop and the client message receiver
        await asyncio.gather(
            handler.start(),
            client_receive_loop(),
            return_exceptions=True,
        )
    except Exception as e:
        logger.error("voice_call_fatal", session_id=session_id, error=str(e))
    finally:
        # Note: handler.start() already calls cleanup() in its own finally block.
        # We only close the WebSocket here — no double cleanup.
        try:
            await websocket.close()
        except Exception:
            pass
        logger.info("voice_ws_closed", session_id=session_id)
