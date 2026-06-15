"""
Call Feature — Real-time voice negotiation via Sarvam AI.

This module provides:
- WebSocket endpoint for bidirectional voice streaming
- Sarvam AI STT (Speech-to-Text) integration
- Sarvam AI TTS (Text-to-Speech) integration
- Full-duplex call with interrupt support
"""
from .voice_routes import voice_router

__all__ = ["voice_router"]
