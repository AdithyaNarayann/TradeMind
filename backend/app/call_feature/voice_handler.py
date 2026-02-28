"""
Voice Call Handler — Orchestrates a full-duplex voice negotiation call.

Manages the connection between:
- Client WebSocket (browser mic/speaker)
- Sarvam STT WebSocket (speech → text)
- Sarvam TTS WebSocket (text → speech)
- Negotiation Engine (process_chat)

Low-latency design:
- Sentence-level TTS: splits AI response into sentences and starts speaking
  the first sentence while later sentences are still being synthesized.
- Audio size cap: rejects oversized chunks to prevent abuse.
- Silence timeout: auto-flushes STT after 2.5s of no audio.
- Parallel TTS: queues sentences concurrently for minimal gap between them.
"""
import asyncio
import base64
import json
import re
import time
from typing import Optional
from uuid import UUID

import structlog

from ..core.config import get_settings
from ..core.engine import NegotiationEngine
from ..models import ChatMessage
from .sarvam_service import SarvamSTTStream, SarvamTTSStream, sarvam_tts_rest

logger = structlog.get_logger(__name__)
settings = get_settings()

# Maximum base64 audio chunk size (64 KB decoded ≈ 87 KB base64)
MAX_AUDIO_CHUNK_B64 = 90_000

# Silence timeout: auto-flush STT if no audio received for this duration
SILENCE_TIMEOUT_S = 1.5

# Split AI text into sentences for streaming TTS
_SENTENCE_RE = re.compile(r'(?<=[.!?])\s+|(?<=\n)')


def _split_sentences(text: str) -> list[str]:
    """Split text into sentence chunks for streaming TTS."""
    parts = _SENTENCE_RE.split(text.strip())
    # Merge very short fragments into previous
    merged = []
    for p in parts:
        p = p.strip()
        if not p:
            continue
        if merged and len(merged[-1]) < 20:
            merged[-1] = merged[-1] + " " + p
        else:
            merged.append(p)
    return merged if merged else [text.strip()]


class VoiceCallHandler:
    """
    Full-duplex voice call handler for a single negotiation session.

    Lifecycle:
    1. Client connects via WebSocket
    2. We open Sarvam STT + TTS WebSockets
    3. Three concurrent tasks run:
       - stt_task: Sarvam STT transcripts → negotiation engine → TTS
       - tts_task: Sarvam TTS audio → client
       - silence_task: auto-flush after silence
    4. Interrupt detection: user speech during AI playback cancels TTS
    5. On disconnect, all resources are cleaned up
    """

    def __init__(self, session_id: str, client_ws):
        self.session_id = session_id
        self.client_ws = client_ws
        self.engine = NegotiationEngine()

        # Sarvam streams
        self.stt = SarvamSTTStream(language=settings.sarvam_language)
        self.tts = SarvamTTSStream(
            language=settings.sarvam_language,
            speaker=settings.sarvam_tts_speaker,
        )

        # State
        self.is_active = False
        self.is_ai_speaking = False
        self.call_start_time = None
        self._tasks = []
        self._tts_queue: asyncio.Queue[str | None] = asyncio.Queue()
        self._interrupt_event = asyncio.Event()
        self._pending_transcript = ""
        self._transcript_lock = asyncio.Lock()
        self._use_rest_tts = False  # Fallback flag
        self._last_audio_ts = 0.0  # Track last audio receive time
        self._silence_task: Optional[asyncio.Task] = None

    async def start(self):
        """Initialize connections and run the call loop."""
        self.is_active = True
        self.call_start_time = time.time()
        self._last_audio_ts = time.time()

        # Notify client we're setting up
        await self._send_client({
            "type": "status",
            "status": "connecting",
            "message": "Setting up voice connection...",
        })

        # Connect to Sarvam STT
        try:
            await self.stt.connect()
        except Exception as e:
            await self._send_client({
                "type": "error",
                "message": f"Failed to connect to speech recognition: {str(e)}",
            })
            return

        # Connect to Sarvam TTS (WebSocket)
        try:
            await self.tts.connect()
        except Exception as e:
            logger.warning("tts_ws_failed_using_rest", error=str(e))
            self._use_rest_tts = True

        await self._send_client({
            "type": "status",
            "status": "listening",
            "message": "Connected! Start speaking...",
        })

        # Run concurrent tasks
        try:
            self._tasks = [
                asyncio.create_task(self._stt_receive_loop(), name="stt_receive"),
                asyncio.create_task(self._tts_send_loop(), name="tts_send"),
                asyncio.create_task(self._silence_monitor(), name="silence_monitor"),
            ]
            # Wait until call ends
            await asyncio.gather(*self._tasks, return_exceptions=True)
        except Exception as e:
            logger.error("voice_call_error", error=str(e))
        finally:
            await self.cleanup()

    async def handle_client_message(self, raw_message: str):
        """Process a message from the client WebSocket."""
        try:
            msg = json.loads(raw_message)
            msg_type = msg.get("type", "")

            if msg_type == "audio":
                # Decode base64 audio and forward to STT
                audio_b64 = msg.get("data", "")
                if not audio_b64:
                    return

                # ── Size validation ─────────────────────────────────
                if len(audio_b64) > MAX_AUDIO_CHUNK_B64:
                    logger.warning("audio_chunk_too_large", size=len(audio_b64))
                    return  # Silently drop oversized chunks

                audio_bytes = base64.b64decode(audio_b64)
                self._last_audio_ts = time.time()
                await self.stt.send_audio(audio_bytes)

                # If AI is speaking and we detect audio input, trigger interrupt
                if self.is_ai_speaking:
                    await self._handle_interrupt()

            elif msg_type == "end_call":
                self.is_active = False
                for task in self._tasks:
                    task.cancel()

            elif msg_type == "flush":
                await self.stt.flush()

            elif msg_type == "ping":
                # Low-latency ping/pong for RTT measurement
                await self._send_client({
                    "type": "pong",
                    "ts": int(time.time() * 1000),
                })

        except json.JSONDecodeError:
            logger.warning("invalid_client_message")
        except Exception as e:
            logger.error("client_message_error", error=str(e))

    async def _silence_monitor(self):
        """Auto-flush STT after silence to reduce latency on final transcript."""
        try:
            while self.is_active:
                await asyncio.sleep(0.5)
                elapsed = time.time() - self._last_audio_ts
                if elapsed >= SILENCE_TIMEOUT_S and not self.is_ai_speaking:
                    # Silence detected — flush STT to finalize any pending transcript
                    await self.stt.flush()
                    self._last_audio_ts = time.time()  # Reset to avoid repeated flushes
        except asyncio.CancelledError:
            pass

    async def _stt_receive_loop(self):
        """
        Read transcripts from Sarvam STT and process them.
        
        On final transcript → send to negotiation engine → queue TTS response.
        """
        try:
            async for msg in self.stt.receive_transcripts():
                if not self.is_active:
                    break

                if msg["type"] == "transcript":
                    transcript = msg["transcript"].strip()
                    if not transcript:
                        continue

                    is_final = msg.get("is_final", False)

                    # Send live transcript to client
                    await self._send_client({
                        "type": "user_transcript",
                        "text": transcript,
                        "is_final": is_final,
                    })

                    if is_final and transcript:
                        # If AI was speaking, this is an interruption
                        if self.is_ai_speaking:
                            await self._handle_interrupt()

                        # Process through negotiation engine
                        await self._process_user_utterance(transcript)

                elif msg["type"] == "vad":
                    event = msg.get("event", "")
                    if event == "speech_start" and self.is_ai_speaking:
                        await self._handle_interrupt()

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error("stt_receive_loop_error", error=str(e))

    async def _process_user_utterance(self, text: str):
        """Send transcribed text to the negotiation engine and queue AI response."""
        await self._send_client({
            "type": "status",
            "status": "processing",
        })

        try:
            session_uuid = UUID(self.session_id)
            chat_msg = ChatMessage(message=text)
            # Run synchronous LLM call in thread executor to not block event loop
            loop = asyncio.get_running_loop()
            response = await loop.run_in_executor(
                None, self.engine.process_chat, session_uuid, chat_msg
            )

            ai_text = response.message
            if not ai_text:
                ai_text = "I'm sorry, could you please repeat that?"

            # Send AI text transcript to client
            await self._send_client({
                "type": "ai_transcript",
                "text": ai_text,
                "pricing": {
                    "decision": response.pricing.decision.value if response.pricing else None,
                    "counter_offer": str(response.pricing.counter_offer_price) if response.pricing and response.pricing.counter_offer_price else None,
                    "accepted_price": str(response.pricing.accepted_price) if response.pricing and response.pricing.accepted_price else None,
                } if response.pricing else None,
                "has_price_offer": response.has_price_offer,
                "round_number": response.round_number,
                "can_continue": response.can_continue,
                "rounds_remaining": response.rounds_remaining,
                "status": response.status.value if response.status else None,
            })

            # ── Sentence-level TTS streaming ────────────────────────
            # Split into sentences so first sentence starts playing immediately
            # while subsequent sentences are still being synthesized.
            sentences = _split_sentences(ai_text)
            for sentence in sentences:
                await self._tts_queue.put(sentence)

        except ValueError as e:
            error_msg = str(e)
            logger.warning("negotiation_error", error=error_msg)
            await self._send_client({
                "type": "ai_transcript",
                "text": error_msg,
            })
            await self._tts_queue.put(error_msg)
        except Exception as e:
            logger.error("process_utterance_error", error=str(e))
            await self._send_client({
                "type": "error",
                "message": "Failed to process your message. Please try again.",
            })

    async def _tts_send_loop(self):
        """
        Read text from TTS queue, synthesize via Sarvam, stream audio to client.
        Processes sentence-by-sentence for low latency.
        """
        try:
            while self.is_active:
                # Wait for text to speak
                text = await self._tts_queue.get()
                if text is None:
                    break

                self.is_ai_speaking = True
                self._interrupt_event.clear()

                await self._send_client({
                    "type": "status",
                    "status": "speaking",
                })

                try:
                    if self._use_rest_tts:
                        await self._tts_rest_fallback(text)
                    else:
                        await self._tts_websocket(text)
                except Exception as e:
                    logger.error("tts_error", error=str(e))
                    # Try REST fallback
                    if not self._use_rest_tts:
                        try:
                            await self._tts_rest_fallback(text)
                        except Exception:
                            pass

                # Only mark AI as done if queue is empty (all sentences spoken)
                if self._tts_queue.empty():
                    self.is_ai_speaking = False

                    await self._send_client({
                        "type": "ai_audio_end",
                    })
                    await self._send_client({
                        "type": "status",
                        "status": "listening",
                    })

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error("tts_send_loop_error", error=str(e))

    async def _tts_websocket(self, text: str):
        """Stream TTS via Sarvam WebSocket."""
        await self.tts.send_text(text)

        async for chunk in self.tts.receive_audio():
            if self._interrupt_event.is_set():
                break

            if chunk["type"] == "audio":
                await self._send_client({
                    "type": "ai_audio",
                    "data": chunk["audio"],
                    "content_type": chunk.get("content_type", "audio/wav"),
                    "sample_rate": 24000,
                })
            elif chunk["type"] == "completion":
                break
            elif chunk["type"] == "error":
                logger.warning("tts_chunk_error", msg=chunk.get("message"))
                break

    async def _tts_rest_fallback(self, text: str):
        """Use REST TTS API as fallback."""
        audio_b64 = await sarvam_tts_rest(
            text=text,
            language=settings.sarvam_language,
            speaker=settings.sarvam_tts_speaker,
        )
        if audio_b64 and not self._interrupt_event.is_set():
            await self._send_client({
                "type": "ai_audio",
                "data": audio_b64,
                "content_type": "audio/wav",
                "sample_rate": 24000,
            })

    async def _handle_interrupt(self):
        """Handle user interrupting the AI mid-speech."""
        if not self.is_ai_speaking:
            return

        logger.info("voice_call_interrupt", session=self.session_id)
        self._interrupt_event.set()
        self.tts.cancel()

        # Drain TTS queue
        while not self._tts_queue.empty():
            try:
                self._tts_queue.get_nowait()
            except asyncio.QueueEmpty:
                break

        self.is_ai_speaking = False

        await self._send_client({
            "type": "ai_audio_end",
        })
        await self._send_client({
            "type": "status",
            "status": "listening",
        })

        # Reconnect TTS for next utterance
        if not self._use_rest_tts:
            try:
                await self.tts.reconnect()
            except Exception:
                logger.warning("tts_reconnect_failed_using_rest")
                self._use_rest_tts = True

    async def _send_client(self, data: dict):
        """Send a JSON message to the client WebSocket."""
        try:
            await self.client_ws.send_json(data)
        except Exception as e:
            logger.warning("client_send_error", error=str(e))

    async def cleanup(self):
        """Clean up all resources."""
        self.is_active = False
        
        # Cancel tasks
        for task in self._tasks:
            if not task.done():
                task.cancel()

        # Close Sarvam connections
        await self.stt.close()
        await self.tts.close()

        logger.info(
            "voice_call_ended",
            session=self.session_id,
            duration_s=round(time.time() - self.call_start_time, 1) if self.call_start_time else 0,
        )
