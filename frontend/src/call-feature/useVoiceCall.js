/**
 * useVoiceCall — React hook for full-duplex voice negotiation.
 *
 * Production-quality, low-latency voice call:
 * - AudioWorklet for off-main-thread audio processing (no glitches)
 * - Client-side VAD to suppress silent frames (~60-80% bandwidth savings)
 * - Real-time RMS energy for authentic waveform visualization
 * - WebSocket reconnection with exponential backoff
 * - JWT auth on WebSocket connection
 * - Mute/unmute without releasing microphone
 * - Volume control via GainNode
 * - Ping/pong RTT measurement for connection quality
 * - Auto-flush STT on silence timeout
 * - Keyboard shortcuts (Escape=end, M=mute)
 * - Memory-safe audio queue with max size
 */
import { useState, useRef, useCallback, useEffect } from 'react';

// ── Derive URLs from environment or window.location ────────────────
function _getBaseUrls() {
    const envApi = import.meta.env.VITE_API_URL || import.meta.env.VITE_BACKEND_URL;
    if (envApi) {
        const http = envApi.replace(/\/+$/, '');
        const ws = http.replace(/^http/, 'ws');
        return { http, ws };
    }
    // Fallback: same host as frontend, port 8000
    const proto = window.location.protocol;
    const host = window.location.hostname;
    return {
        http: `${proto}//${host}:8000`,
        ws: `${proto === 'https:' ? 'wss' : 'ws'}://${host}:8000`,
    };
}

const { http: VOICE_API_BASE, ws: VOICE_WS_BASE } = _getBaseUrls();

// ── Audio helpers ──────────────────────────────────────────────────

/** Convert Int16Array PCM to base64 string. */
function pcmToBase64(pcmData) {
    const uint8 = new Uint8Array(pcmData.buffer, pcmData.byteOffset, pcmData.byteLength);
    let binary = '';
    for (let i = 0; i < uint8.byteLength; i++) {
        binary += String.fromCharCode(uint8[i]);
    }
    return btoa(binary);
}

/**
 * Decode base64 audio to an AudioBuffer for playback.
 *
 * Strategy:
 *  1. Convert base64 → Uint8Array of bytes
 *  2. If it has a RIFF/WAV header → use native decodeAudioData (handles sample rate)
 *  3. Otherwise wrap raw PCM in a proper WAV header → decodeAudioData
 *  4. Last resort: manually create AudioBuffer from PCM samples
 */
async function decodeBase64Audio(audioCtx, base64Audio, sampleRate = 24000) {
    const binaryStr = atob(base64Audio);
    const bytes = new Uint8Array(binaryStr.length);
    for (let i = 0; i < binaryStr.length; i++) {
        bytes[i] = binaryStr.charCodeAt(i);
    }

    // Strategy 1: Already a valid WAV/RIFF — let the browser decode natively
    const hasWavHeader = bytes.length > 44 &&
        bytes[0] === 0x52 && bytes[1] === 0x49 &&
        bytes[2] === 0x46 && bytes[3] === 0x46; // "RIFF"

    if (hasWavHeader) {
        try {
            // Clone the buffer because decodeAudioData detaches it
            return await audioCtx.decodeAudioData(bytes.buffer.slice(0));
        } catch (e) {
            console.warn('WAV decodeAudioData failed, trying manual:', e);
        }
    }

    // Strategy 2: Wrap raw PCM in a proper WAV header and decode natively
    try {
        const wavBuf = wrapPCMinWAV(hasWavHeader ? bytes.slice(44) : bytes, sampleRate);
        return await audioCtx.decodeAudioData(wavBuf);
    } catch (e2) {
        console.warn('WAV-wrapped decodeAudioData failed, manual fallback:', e2);
    }

    // Strategy 3: Manual PCM → AudioBuffer (last resort)
    return rawPCMtoAudioBuffer(audioCtx, hasWavHeader ? bytes.slice(44) : bytes, sampleRate);
}

/** Wrap raw PCM Int16 LE bytes in a valid WAV header. */
function wrapPCMinWAV(pcmBytes, sampleRate) {
    const numChannels = 1;
    const bitsPerSample = 16;
    const byteRate = sampleRate * numChannels * (bitsPerSample / 8);
    const blockAlign = numChannels * (bitsPerSample / 8);
    const dataSize = pcmBytes.length;
    const buffer = new ArrayBuffer(44 + dataSize);
    const view = new DataView(buffer);
    const w = (off, s) => { for (let i = 0; i < s.length; i++) view.setUint8(off + i, s.charCodeAt(i)); };
    w(0, 'RIFF');
    view.setUint32(4, 36 + dataSize, true);
    w(8, 'WAVE');
    w(12, 'fmt ');
    view.setUint32(16, 16, true);
    view.setUint16(20, 1, true);
    view.setUint16(22, numChannels, true);
    view.setUint32(24, sampleRate, true);
    view.setUint32(28, byteRate, true);
    view.setUint16(32, blockAlign, true);
    view.setUint16(34, bitsPerSample, true);
    w(36, 'data');
    view.setUint32(40, dataSize, true);
    new Uint8Array(buffer, 44).set(pcmBytes);
    return buffer;
}

/** Convert raw PCM Int16 LE bytes to AudioBuffer directly. */
function rawPCMtoAudioBuffer(audioCtx, pcmBytes, sampleRate) {
    const numSamples = Math.floor(pcmBytes.length / 2);
    if (numSamples === 0) return audioCtx.createBuffer(1, 1, sampleRate);
    const audioBuffer = audioCtx.createBuffer(1, numSamples, sampleRate);
    const channelData = audioBuffer.getChannelData(0);
    const view = new DataView(pcmBytes.buffer, pcmBytes.byteOffset, pcmBytes.byteLength);
    for (let i = 0; i < numSamples; i++) {
        channelData[i] = view.getInt16(i * 2, true) / 32768;
    }
    return audioBuffer;
}

// ── Constants ──────────────────────────────────────────────────────
const MAX_AUDIO_QUEUE = 30;       // Max queued audio chunks (increased for longer AI responses)
const RECONNECT_MAX_ATTEMPTS = 3;
const RECONNECT_BASE_DELAY = 500; // ms
const PING_INTERVAL = 5000;       // ms

// ════════════════════════════════════════════════════════════════════
// ██  HOOK
// ════════════════════════════════════════════════════════════════════

export default function useVoiceCall({ sessionId }) {
    // ── Connection state ───────────────────────────────────────────
    const [isCallActive, setIsCallActive] = useState(false);
    const [callStatus, setCallStatus] = useState('idle');
    const [error, setError] = useState(null);
    const [callDuration, setCallDuration] = useState(0);

    // ── Audio state ────────────────────────────────────────────────
    const [isMuted, setIsMuted] = useState(false);
    const [volume, setVolume] = useState(1.0);      // 0–1
    const [userEnergy, setUserEnergy] = useState(0); // RMS 0–1
    const [aiEnergy, setAiEnergy] = useState(0);     // RMS for AI playback
    const [connectionQuality, setConnectionQuality] = useState('good'); // good|fair|poor

    // ── Transcripts ────────────────────────────────────────────────
    const [userTranscript, setUserTranscript] = useState('');
    const [aiTranscript, setAiTranscript] = useState('');
    const [callHistory, setCallHistory] = useState([]);

    // ── Refs ───────────────────────────────────────────────────────
    const wsRef = useRef(null);
    const mediaStreamRef = useRef(null);
    const audioContextRef = useRef(null);
    const workletNodeRef = useRef(null);
    const playbackCtxRef = useRef(null);
    const gainNodeRef = useRef(null);
    const analyserRef = useRef(null);
    const audioQueueRef = useRef([]);
    const isPlayingRef = useRef(false);
    const callStartRef = useRef(null);
    const timerRef = useRef(null);
    const pingIntervalRef = useRef(null);
    const reconnectAttemptsRef = useRef(0);
    const isMutedRef = useRef(false);
    const volumeRef = useRef(1.0);
    const energyRafRef = useRef(null);

    // Keep refs in sync
    useEffect(() => { isMutedRef.current = isMuted; }, [isMuted]);
    useEffect(() => {
        volumeRef.current = volume;
        if (gainNodeRef.current) gainNodeRef.current.gain.value = volume;
    }, [volume]);

    // ── Call duration timer ────────────────────────────────────────
    useEffect(() => {
        if (isCallActive && callStartRef.current) {
            timerRef.current = setInterval(() => {
                setCallDuration(Math.floor((Date.now() - callStartRef.current) / 1000));
            }, 1000);
        }
        return () => { if (timerRef.current) clearInterval(timerRef.current); };
    }, [isCallActive]);

    // ── Keyboard shortcuts ─────────────────────────────────────────
    useEffect(() => {
        if (!isCallActive) return;
        const handler = (e) => {
            if (e.key === 'Escape') endCall();
            if (e.key === 'm' || e.key === 'M') toggleMute();
        };
        window.addEventListener('keydown', handler);
        return () => window.removeEventListener('keydown', handler);
    }, [isCallActive]);

    // ────────────────────────────────────────────────────────────────
    // Start Call
    // ────────────────────────────────────────────────────────────────
    const startCall = useCallback(async () => {
        if (!sessionId) { setError('No active session'); return; }

        setError(null);
        setCallStatus('connecting');
        setCallHistory([]);
        setUserTranscript('');
        setAiTranscript('');
        setConnectionQuality('good');
        reconnectAttemptsRef.current = 0;

        // 1. Validate session
        try {
            const resp = await fetch(`${VOICE_API_BASE}/api/v1/voice/validate/${sessionId}`);
            if (!resp.ok) {
                const data = await resp.json().catch(() => ({}));
                setError(data.error || 'Session not found. Please start a new negotiation.');
                setCallStatus('idle');
                return;
            }
            const data = await resp.json();
            if (!data.valid) {
                setError(data.error || 'Session expired. Please start a new negotiation.');
                setCallStatus('idle');
                return;
            }
        } catch {
            setError('Cannot reach voice server. Make sure the backend is running.');
            setCallStatus('idle');
            return;
        }

        // 2. Request microphone
        let stream;
        try {
            stream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    sampleRate: { ideal: 48000 },
                    channelCount: 1,
                    echoCancellation: true,
                    noiseSuppression: true,
                    autoGainControl: true,
                },
            });
            mediaStreamRef.current = stream;
        } catch {
            setError('Microphone access denied. Please allow microphone and try again.');
            setCallStatus('idle');
            return;
        }

        // 3. Connect WebSocket
        await connectWebSocket(stream);
    }, [sessionId]);

    // ────────────────────────────────────────────────────────────────
    // WebSocket connect (supports reconnection)
    // ────────────────────────────────────────────────────────────────
    const connectWebSocket = useCallback(async (stream) => {
        const token = localStorage.getItem('trademind_token') || '';
        const wsUrl = `${VOICE_WS_BASE}/api/v1/voice/ws/${sessionId}?token=${encodeURIComponent(token)}`;

        try {
            const ws = new WebSocket(wsUrl);
            wsRef.current = ws;

            ws.onopen = () => {
                setIsCallActive(true);
                setCallStatus('listening');
                callStartRef.current = callStartRef.current || Date.now();
                reconnectAttemptsRef.current = 0;
                startAudioCapture(stream, ws);
                startPingLoop(ws);
            };

            ws.onmessage = (event) => {
                try {
                    handleServerMessage(JSON.parse(event.data));
                } catch (e) {
                    console.warn('Bad WS message:', e);
                }
            };

            ws.onerror = () => {
                setError('Voice connection error');
            };

            ws.onclose = (e) => {
                console.log('Voice WS closed:', e.code, e.reason);
                stopPingLoop();

                // Attempt reconnect on unexpected close
                if (e.code !== 1000 && e.code < 4000 && reconnectAttemptsRef.current < RECONNECT_MAX_ATTEMPTS) {
                    reconnectAttemptsRef.current++;
                    const delay = RECONNECT_BASE_DELAY * Math.pow(2, reconnectAttemptsRef.current - 1);
                    setError(`Reconnecting... (attempt ${reconnectAttemptsRef.current})`);
                    setTimeout(() => {
                        if (mediaStreamRef.current) connectWebSocket(mediaStreamRef.current);
                    }, delay);
                    return;
                }

                stopAudioCapture();
                setIsCallActive(false);
                setCallStatus('idle');
            };
        } catch {
            setError('Failed to connect to voice server');
            setCallStatus('idle');
            stopAudioCapture();
        }
    }, [sessionId]);

    // ────────────────────────────────────────────────────────────────
    // Ping/pong RTT measurement
    // ────────────────────────────────────────────────────────────────
    const startPingLoop = useCallback((ws) => {
        pingIntervalRef.current = setInterval(() => {
            if (ws.readyState === WebSocket.OPEN) {
                ws._pingTs = Date.now();
                ws.send(JSON.stringify({ type: 'ping' }));
            }
        }, PING_INTERVAL);
    }, []);

    const stopPingLoop = useCallback(() => {
        if (pingIntervalRef.current) { clearInterval(pingIntervalRef.current); pingIntervalRef.current = null; }
    }, []);

    // ────────────────────────────────────────────────────────────────
    // AudioWorklet capture (off main thread)
    // ────────────────────────────────────────────────────────────────
    const startAudioCapture = useCallback(async (stream, ws) => {
        try {
            const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
            audioContextRef.current = audioCtx;

            // Resume if suspended (browser auto-suspend policy)
            if (audioCtx.state === 'suspended') await audioCtx.resume();

            // Try AudioWorklet first, fallback to ScriptProcessor
            let useWorklet = true;
            try {
                await audioCtx.audioWorklet.addModule('/voice-processor.js');
            } catch {
                console.warn('AudioWorklet not available, falling back to ScriptProcessor');
                useWorklet = false;
            }

            const source = audioCtx.createMediaStreamSource(stream);

            if (useWorklet) {
                const workletNode = new AudioWorkletNode(audioCtx, 'voice-processor', {
                    channelCount: 1,
                    channelCountMode: 'explicit',
                });
                workletNodeRef.current = workletNode;

                // Tell processor our sample rate
                workletNode.port.postMessage({ type: 'init', sampleRate: audioCtx.sampleRate });
                workletNode.port.postMessage({ type: 'mute', muted: isMutedRef.current });

                workletNode.port.onmessage = (e) => {
                    const msg = e.data;
                    if (msg.type === 'audio' && ws.readyState === WebSocket.OPEN) {
                        const b64 = pcmToBase64(msg.pcm16);
                        ws.send(JSON.stringify({ type: 'audio', data: b64 }));
                    } else if (msg.type === 'energy') {
                        setUserEnergy(Math.min(1, msg.rms * 10)); // Scale for visualization
                    }
                };

                source.connect(workletNode);
                workletNode.connect(audioCtx.destination); // Needed for processing
            } else {
                // Fallback: ScriptProcessor (deprecated but works everywhere)
                const processor = audioCtx.createScriptProcessor(4096, 1, 1);
                workletNodeRef.current = processor;

                processor.onaudioprocess = (e) => {
                    if (ws.readyState !== WebSocket.OPEN || isMutedRef.current) return;
                    const input = e.inputBuffer.getChannelData(0);

                    // Simple energy check (VAD)
                    let sum = 0;
                    for (let i = 0; i < input.length; i++) sum += input[i] * input[i];
                    const rms = Math.sqrt(sum / input.length);
                    setUserEnergy(Math.min(1, rms * 10));

                    if (rms < 0.005) return; // Skip silence

                    // Downsample to 16kHz
                    const ratio = audioCtx.sampleRate / 16000;
                    const newLen = Math.round(input.length / ratio);
                    const pcm = new Int16Array(newLen);
                    for (let i = 0; i < newLen; i++) {
                        const idx = Math.round(i * ratio);
                        const s = Math.max(-1, Math.min(1, input[idx] || 0));
                        pcm[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
                    }

                    const b64 = pcmToBase64(pcm);
                    ws.send(JSON.stringify({ type: 'audio', data: b64 }));
                };

                source.connect(processor);
                processor.connect(audioCtx.destination);
            }
        } catch (e) {
            console.error('Audio capture error:', e);
            setError('Failed to capture audio');
        }
    }, []);

    const stopAudioCapture = useCallback(() => {
        if (workletNodeRef.current) {
            workletNodeRef.current.disconnect();
            workletNodeRef.current = null;
        }
        if (audioContextRef.current) {
            audioContextRef.current.close().catch(() => {});
            audioContextRef.current = null;
        }
        if (mediaStreamRef.current) {
            mediaStreamRef.current.getTracks().forEach(t => t.stop());
            mediaStreamRef.current = null;
        }
        if (energyRafRef.current) {
            cancelAnimationFrame(energyRafRef.current);
            energyRafRef.current = null;
        }
    }, []);

    // ────────────────────────────────────────────────────────────────
    // Mute toggle
    // ────────────────────────────────────────────────────────────────
    const toggleMute = useCallback(() => {
        setIsMuted(prev => {
            const next = !prev;
            // Tell worklet
            if (workletNodeRef.current?.port?.postMessage) {
                workletNodeRef.current.port.postMessage({ type: 'mute', muted: next });
            }
            return next;
        });
    }, []);

    // ────────────────────────────────────────────────────────────────
    // Handle messages from backend
    // ────────────────────────────────────────────────────────────────
    const handleServerMessage = useCallback((msg) => {
        switch (msg.type) {
            case 'status':
                setCallStatus(msg.status);
                break;

            case 'user_transcript':
                if (msg.is_final) {
                    setCallHistory(prev => [...prev, {
                        sender: 'user',
                        text: msg.text,
                        timestamp: new Date(),
                    }]);
                    setUserTranscript('');
                } else {
                    setUserTranscript(msg.text);
                }
                break;

            case 'ai_transcript':
                setAiTranscript(msg.text);
                setCallHistory(prev => [...prev, {
                    sender: 'bot',
                    text: msg.text,
                    timestamp: new Date(),
                    meta: {
                        pricing: msg.pricing,
                        has_price_offer: msg.has_price_offer,
                        round_number: msg.round_number,
                        can_continue: msg.can_continue,
                        rounds_remaining: msg.rounds_remaining,
                        status: msg.status,
                    },
                }]);
                break;

            case 'ai_audio':
                queueAudioPlayback(msg.data, msg.content_type, msg.sample_rate || 24000);
                break;

            case 'ai_audio_end':
                setAiTranscript('');
                setAiEnergy(0);
                break;

            case 'pong': {
                // Calculate RTT
                const ws = wsRef.current;
                if (ws && ws._pingTs) {
                    const rtt = Date.now() - ws._pingTs;
                    if (rtt < 200) setConnectionQuality('good');
                    else if (rtt < 500) setConnectionQuality('fair');
                    else setConnectionQuality('poor');
                }
                break;
            }

            case 'error':
                setError(msg.message);
                break;

            default:
                break;
        }
    }, []);

    // ────────────────────────────────────────────────────────────────
    // Audio playback with GainNode + AnalyserNode
    // ────────────────────────────────────────────────────────────────
    const queueAudioPlayback = useCallback((base64Audio, contentType, sampleRate = 24000) => {
        // Memory guard: cap queue
        if (audioQueueRef.current.length >= MAX_AUDIO_QUEUE) {
            audioQueueRef.current.shift(); // Drop oldest
        }
        audioQueueRef.current.push({ base64Audio, contentType, sampleRate });
        if (!isPlayingRef.current) playNextAudio();
    }, []);

    const playNextAudio = useCallback(async () => {
        if (audioQueueRef.current.length === 0) {
            isPlayingRef.current = false;
            setAiEnergy(0);
            return;
        }

        isPlayingRef.current = true;
        const { base64Audio, sampleRate } = audioQueueRef.current.shift();

        try {
            // Use a single persistent playback context at 24kHz (Sarvam output rate)
            if (!playbackCtxRef.current || playbackCtxRef.current.state === 'closed') {
                const ctx = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 24000 });
                playbackCtxRef.current = ctx;

                // Create gain + analyser chain
                const gain = ctx.createGain();
                gain.gain.value = volumeRef.current;
                gainNodeRef.current = gain;

                const analyser = ctx.createAnalyser();
                analyser.fftSize = 256;
                analyserRef.current = analyser;

                gain.connect(analyser);
                analyser.connect(ctx.destination);

                // Start energy monitoring for AI waveform
                startAiEnergyMonitor(analyser);
            }

            // Resume if suspended
            if (playbackCtxRef.current.state === 'suspended') {
                await playbackCtxRef.current.resume();
            }

            const audioBuffer = await decodeBase64Audio(playbackCtxRef.current, base64Audio, sampleRate || 24000);
            console.log(`Playing audio: ${audioBuffer.duration.toFixed(2)}s @ ${audioBuffer.sampleRate}Hz, ${audioBuffer.length} samples`);
            const source = playbackCtxRef.current.createBufferSource();
            source.buffer = audioBuffer;
            source.connect(gainNodeRef.current);
            source.onended = () => playNextAudio();
            source.start();
        } catch (e) {
            console.warn('Audio playback error:', e);
            playNextAudio(); // Skip broken chunk
        }
    }, []);

    /** Poll AnalyserNode for AI playback energy. */
    const startAiEnergyMonitor = useCallback((analyser) => {
        const data = new Uint8Array(analyser.frequencyBinCount);
        const tick = () => {
            if (!analyser || !isPlayingRef.current) {
                setAiEnergy(0);
                energyRafRef.current = null;
                return;
            }
            analyser.getByteTimeDomainData(data);
            let sum = 0;
            for (let i = 0; i < data.length; i++) {
                const v = (data[i] - 128) / 128;
                sum += v * v;
            }
            setAiEnergy(Math.min(1, Math.sqrt(sum / data.length) * 8));
            energyRafRef.current = requestAnimationFrame(tick);
        };
        tick();
    }, []);

    const stopPlayback = useCallback(() => {
        audioQueueRef.current = [];
        isPlayingRef.current = false;
        setAiEnergy(0);
        // Cancel RAF loop before closing context
        if (energyRafRef.current) {
            cancelAnimationFrame(energyRafRef.current);
            energyRafRef.current = null;
        }
        if (playbackCtxRef.current && playbackCtxRef.current.state !== 'closed') {
            playbackCtxRef.current.close().catch(() => {});
            playbackCtxRef.current = null;
            gainNodeRef.current = null;
            analyserRef.current = null;
        }
    }, []);

    // ────────────────────────────────────────────────────────────────
    // End call
    // ────────────────────────────────────────────────────────────────
    const endCall = useCallback(() => {
        if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
            wsRef.current.send(JSON.stringify({ type: 'end_call' }));
            wsRef.current.close(1000, 'User ended call');
        }
        wsRef.current = null;
        reconnectAttemptsRef.current = RECONNECT_MAX_ATTEMPTS; // Prevent reconnect

        stopPingLoop();
        stopAudioCapture();
        stopPlayback();

        setIsCallActive(false);
        setCallStatus('idle');
        setUserTranscript('');
        setAiTranscript('');
        setUserEnergy(0);
        setAiEnergy(0);
        setIsMuted(false);
    }, [stopAudioCapture, stopPlayback, stopPingLoop]);

    // Cleanup on unmount
    useEffect(() => {
        return () => {
            reconnectAttemptsRef.current = RECONNECT_MAX_ATTEMPTS;
            if (wsRef.current) wsRef.current.close();
            stopAudioCapture();
            stopPlayback();
            stopPingLoop();
            if (timerRef.current) clearInterval(timerRef.current);
        };
    }, []);

    return {
        // State
        isCallActive,
        callStatus,
        error,
        callDuration,
        isMuted,
        volume,
        userEnergy,
        aiEnergy,
        connectionQuality,
        userTranscript,
        aiTranscript,
        callHistory,

        // Actions
        startCall,
        endCall,
        toggleMute,
        setVolume,
        setError,
    };
}
