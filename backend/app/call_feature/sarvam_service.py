"""
Sarvam AI Voice Service — STT & TTS integration via WebSocket + REST.

Handles:
- Real-time Speech-to-Text streaming via Sarvam WebSocket
- Real-time Text-to-Speech streaming via Sarvam WebSocket
- REST fallback for TTS
"""
import asyncio
import base64
import json
from typing import AsyncGenerator, Optional, Callable, Awaitable

import httpx
import structlog

try:
    import websockets
    from websockets.asyncio.client import connect as ws_connect
except ImportError:
    # websockets 12+ moved connect
    import websockets
    ws_connect = websockets.connect

from ..core.config import get_settings

logger = structlog.get_logger(__name__)
settings = get_settings()


class SarvamSTTStream:
    """
    Manages a WebSocket connection to Sarvam Speech-to-Text.
    
    Accepts raw PCM 16kHz audio chunks, yields partial/final transcripts.
    Uses saaras:v3 model with VAD signals for interrupt detection.
    """

    def __init__(self, language: str = "en-IN", on_transcript: Optional[Callable] = None):
        self.language = language
        self.on_transcript = on_transcript
        self._ws = None
        self._connected = False
        self._cancelled = False

    async def connect(self):
        """Open WebSocket to Sarvam STT."""
        params = (
            f"?language-code={self.language}"
            f"&model={settings.sarvam_stt_model}"
            f"&mode=transcribe"
            f"&sample_rate=16000"
            f"&high_vad_sensitivity=true"
            f"&vad_signals=true"
        )
        url = settings.sarvam_stt_ws_url + params
        headers = {"Api-Subscription-Key": settings.sarvam_api_key}

        try:
            self._ws = await ws_connect(
                url,
                additional_headers=headers,
                ping_interval=20,
                ping_timeout=10,
                close_timeout=5,
            )
            self._connected = True
            logger.info("sarvam_stt_connected")
        except Exception as e:
            logger.error("sarvam_stt_connect_error", error=str(e))
            raise

    async def send_audio(self, audio_bytes: bytes):
        """Send a chunk of PCM 16kHz audio to Sarvam STT."""
        if not self._ws or not self._connected:
            return
        try:
            # Sarvam expects JSON with base64-encoded audio
            msg = json.dumps({
                "audio": {
                    "data": base64.b64encode(audio_bytes).decode("utf-8"),
                    "sample_rate": "16000",
                    "encoding": "audio/wav",
                }
            })
            await self._ws.send(msg)
        except Exception as e:
            logger.warning("sarvam_stt_send_error", error=str(e))

    async def flush(self):
        """Send flush signal to finalize current utterance."""
        if not self._ws or not self._connected:
            return
        try:
            await self._ws.send(json.dumps({"type": "flush"}))
        except Exception as e:
            logger.warning("sarvam_stt_flush_error", error=str(e))

    async def receive_transcripts(self) -> AsyncGenerator[dict, None]:
        """
        Yield transcript messages from Sarvam STT WebSocket.
        
        Each yields: { "type": "data"|"vad", "transcript": str, "is_final": bool }
        """
        if not self._ws:
            return
        try:
            async for raw_msg in self._ws:
                if self._cancelled:
                    break
                try:
                    msg = json.loads(raw_msg)
                    msg_type = msg.get("type", "data")

                    if msg_type == "data":
                        data = msg.get("data", {})
                        transcript = data.get("transcript", "")
                        if transcript:
                            yield {
                                "type": "transcript",
                                "transcript": transcript,
                                "is_final": True,
                                "metrics": data.get("metrics"),
                            }
                    elif msg_type == "vad":
                        # VAD signal — speech started/stopped
                        yield {
                            "type": "vad",
                            "event": msg.get("data", {}).get("event", ""),
                        }
                    else:
                        logger.debug("sarvam_stt_unknown_msg", msg=msg)
                except json.JSONDecodeError:
                    logger.warning("sarvam_stt_bad_json", raw=str(raw_msg)[:200])
        except websockets.exceptions.ConnectionClosed:
            logger.info("sarvam_stt_ws_closed")
        except Exception as e:
            if not self._cancelled:
                logger.error("sarvam_stt_receive_error", error=str(e))

    async def close(self):
        """Close the STT WebSocket."""
        self._cancelled = True
        self._connected = False
        if self._ws:
            try:
                await self._ws.close()
            except Exception:
                pass
            self._ws = None


class SarvamTTSStream:
    """
    Manages a WebSocket connection to Sarvam Text-to-Speech.
    
    Accepts text, yields base64-encoded audio chunks for streaming playback.
    Uses bulbul:v3-beta model.
    """

    def __init__(
        self,
        language: str = "en-IN",
        speaker: str = "Shubh",
    ):
        self.language = language
        self.speaker = speaker
        self._ws = None
        self._connected = False
        self._cancelled = False
        self._configured = False

    async def connect(self):
        """Open WebSocket to Sarvam TTS."""
        params = f"?model={settings.sarvam_tts_model}&send_completion_event=true"
        url = settings.sarvam_tts_ws_url + params
        headers = {"Api-Subscription-Key": settings.sarvam_api_key}

        try:
            self._ws = await ws_connect(
                url,
                additional_headers=headers,
                ping_interval=20,
                ping_timeout=10,
                close_timeout=5,
            )
            self._connected = True

            # Send initial config message
            config_msg = json.dumps({
                "type": "config",
                "data": {
                    "target_language_code": self.language,
                    "speaker": self.speaker.lower(),
                }
            })
            await self._ws.send(config_msg)
            self._configured = True
            logger.info("sarvam_tts_connected", speaker=self.speaker)
        except Exception as e:
            logger.error("sarvam_tts_connect_error", error=str(e))
            raise

    async def send_text(self, text: str):
        """Send text for TTS synthesis."""
        if not self._ws or not self._connected:
            return
        try:
            msg = json.dumps({
                "type": "text",
                "data": {"text": text}
            })
            await self._ws.send(msg)
            # Send flush to indicate end of text
            await self._ws.send(json.dumps({"type": "flush"}))
        except Exception as e:
            logger.warning("sarvam_tts_send_error", error=str(e))

    async def receive_audio(self) -> AsyncGenerator[dict, None]:
        """
        Yield audio chunks from Sarvam TTS WebSocket.
        
        Each yields: { "type": "audio"|"event", "audio": base64_str, "content_type": str }
        """
        if not self._ws:
            return
        try:
            async for raw_msg in self._ws:
                if self._cancelled:
                    break
                try:
                    msg = json.loads(raw_msg)
                    msg_type = msg.get("type", "")

                    if msg_type == "audio":
                        data = msg.get("data", {})
                        yield {
                            "type": "audio",
                            "audio": data.get("audio", ""),
                            "content_type": data.get("content_type", "audio/wav"),
                        }
                    elif msg_type == "event":
                        data = msg.get("data", {})
                        if data.get("event") == "completion":
                            yield {"type": "completion"}
                    elif msg_type == "error":
                        data = msg.get("data", {})
                        logger.error("sarvam_tts_error", error=data)
                        yield {"type": "error", "message": data.get("message", "TTS error")}
                    else:
                        logger.debug("sarvam_tts_unknown_msg", msg=msg)
                except json.JSONDecodeError:
                    logger.warning("sarvam_tts_bad_json", raw=str(raw_msg)[:200])
        except websockets.exceptions.ConnectionClosed:
            logger.info("sarvam_tts_ws_closed")
        except Exception as e:
            if not self._cancelled:
                logger.error("sarvam_tts_receive_error", error=str(e))

    def cancel(self):
        """Signal cancellation (for interrupt handling)."""
        self._cancelled = True

    async def close(self):
        """Close the TTS WebSocket."""
        self._cancelled = True
        self._connected = False
        self._configured = False
        if self._ws:
            try:
                await self._ws.close()
            except Exception:
                pass
            self._ws = None

    async def reconnect(self):
        """Close and reopen — used after interrupt to reset TTS state."""
        await self.close()
        self._cancelled = False
        await self.connect()


async def sarvam_tts_rest(text: str, language: str = "en-IN", speaker: str = "Shubh") -> Optional[str]:
    """
    Fallback REST API for Sarvam TTS.

    Returns base64-encoded audio string, or None on failure.
    """
    url = settings.sarvam_tts_rest_url
    headers = {
        "api-subscription-key": settings.sarvam_api_key,
        "Content-Type": "application/json",
    }
    payload = {
        "text": text,
        "target_language_code": language,
        "speaker": speaker.lower(),
        "model": "bulbul:v3",
        "speech_sample_rate": 24000,
        "enable_preprocessing": False,
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            audios = data.get("audios", [])
            return audios[0] if audios else None
    except Exception as e:
        logger.error("sarvam_tts_rest_error", error=str(e))
        return None
