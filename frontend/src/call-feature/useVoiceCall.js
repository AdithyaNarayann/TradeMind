/**
 * useVoiceCall — React hook for full-duplex voice negotiation.
 *
 * Manages:
 * - WebSocket connection to backend voice endpoint
 * - Microphone capture via MediaRecorder / AudioWorklet
 * - Audio playback of AI TTS responses
 * - Real-time transcripts for both sides
 * - Interrupt detection (user speaks while AI is talking)
 */
import { useState, useRef, useCallback, useEffect } from 'react';

const VOICE_WS_BASE = 'ws://127.0.0.1:8000/api/v1/voice';
const VOICE_API_BASE = 'http://127.0.0.1:8000/api/v1/voice';

/**
 * Downsample a Float32Array from source sample rate to 16kHz,
 * then convert to 16-bit PCM bytes.
 */
function downsampleTo16kPCM(float32Array, sourceSampleRate) {
    const ratio = sourceSampleRate / 16000;
    const newLength = Math.round(float32Array.length / ratio);
    const result = new Int16Array(newLength);
    for (let i = 0; i < newLength; i++) {
        const idx = Math.round(i * ratio);
        const sample = Math.max(-1, Math.min(1, float32Array[idx] || 0));
        result[i] = sample < 0 ? sample * 0x8000 : sample * 0x7FFF;
    }
    return result;
}

/**
 * Convert Int16Array PCM to base64 string.
 */
function pcmToBase64(pcmData) {
    const uint8 = new Uint8Array(pcmData.buffer);
    let binary = '';
    for (let i = 0; i < uint8.byteLength; i++) {
        binary += String.fromCharCode(uint8[i]);
    }
    return btoa(binary);
}

/**
 * Decode base64 audio to AudioBuffer for playback.
 */
async function decodeBase64Audio(audioCtx, base64Audio) {
    const binaryStr = atob(base64Audio);
    const bytes = new Uint8Array(binaryStr.length);
    for (let i = 0; i < binaryStr.length; i++) {
        bytes[i] = binaryStr.charCodeAt(i);
    }
    try {
        return await audioCtx.decodeAudioData(bytes.buffer.slice(0));
    } catch {
        // If decoding fails, try wrapping raw PCM in a WAV header
        const wavBuffer = wrapPCMinWAV(bytes, 24000);
        return await audioCtx.decodeAudioData(wavBuffer);
    }
}

/**
 * Wrap raw PCM bytes in a WAV header.
 */
function wrapPCMinWAV(pcmBytes, sampleRate = 24000) {
    const numChannels = 1;
    const bitsPerSample = 16;
    const byteRate = sampleRate * numChannels * (bitsPerSample / 8);
    const blockAlign = numChannels * (bitsPerSample / 8);
    const dataSize = pcmBytes.length;
    const headerSize = 44;
    const buffer = new ArrayBuffer(headerSize + dataSize);
    const view = new DataView(buffer);

    // RIFF header
    writeString(view, 0, 'RIFF');
    view.setUint32(4, 36 + dataSize, true);
    writeString(view, 8, 'WAVE');

    // fmt sub-chunk
    writeString(view, 12, 'fmt ');
    view.setUint32(16, 16, true);
    view.setUint16(20, 1, true); // PCM
    view.setUint16(22, numChannels, true);
    view.setUint32(24, sampleRate, true);
    view.setUint32(28, byteRate, true);
    view.setUint16(32, blockAlign, true);
    view.setUint16(34, bitsPerSample, true);

    // data sub-chunk
    writeString(view, 36, 'data');
    view.setUint32(40, dataSize, true);

    const uint8View = new Uint8Array(buffer);
    uint8View.set(pcmBytes, headerSize);
    return buffer;
}

function writeString(view, offset, str) {
    for (let i = 0; i < str.length; i++) {
        view.setUint8(offset + i, str.charCodeAt(i));
    }
}


export default function useVoiceCall({ sessionId }) {
    // Connection state
    const [isCallActive, setIsCallActive] = useState(false);
    const [callStatus, setCallStatus] = useState('idle'); // idle | connecting | listening | processing | speaking
    const [error, setError] = useState(null);
    const [callDuration, setCallDuration] = useState(0);

    // Transcripts
    const [userTranscript, setUserTranscript] = useState('');         // Current partial
    const [aiTranscript, setAiTranscript] = useState('');             // Current AI response
    const [callHistory, setCallHistory] = useState([]);               // Array of { sender, text, timestamp, meta }

    // Refs
    const wsRef = useRef(null);
    const mediaStreamRef = useRef(null);
    const audioContextRef = useRef(null);
    const processorRef = useRef(null);
    const playbackCtxRef = useRef(null);
    const audioQueueRef = useRef([]);
    const isPlayingRef = useRef(false);
    const callStartRef = useRef(null);
    const timerRef = useRef(null);

    // Timer for call duration
    useEffect(() => {
        if (isCallActive && callStartRef.current) {
            timerRef.current = setInterval(() => {
                setCallDuration(Math.floor((Date.now() - callStartRef.current) / 1000));
            }, 1000);
        }
        return () => {
            if (timerRef.current) clearInterval(timerRef.current);
        };
    }, [isCallActive]);

    /**
     * Start the voice call.
     */
    const startCall = useCallback(async () => {
        if (!sessionId) {
            setError('No active session');
            return;
        }

        setError(null);
        setCallStatus('connecting');
        setCallHistory([]);
        setUserTranscript('');
        setAiTranscript('');

        // 1. Validate session first
        try {
            const resp = await fetch(`${VOICE_API_BASE}/validate/${sessionId}`);
            const data = await resp.json();
            if (!data.valid) {
                setError(data.error || 'Invalid session');
                setCallStatus('idle');
                return;
            }
        } catch (e) {
            setError('Cannot reach voice server');
            setCallStatus('idle');
            return;
        }

        // 2. Request microphone access
        let stream;
        try {
            stream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    sampleRate: 16000,
                    channelCount: 1,
                    echoCancellation: true,
                    noiseSuppression: true,
                    autoGainControl: true,
                },
            });
            mediaStreamRef.current = stream;
        } catch (e) {
            setError('Microphone access denied. Please allow microphone access and try again.');
            setCallStatus('idle');
            return;
        }

        // 3. Open WebSocket to backend
        try {
            const ws = new WebSocket(`${VOICE_WS_BASE}/ws/${sessionId}`);
            wsRef.current = ws;

            ws.onopen = () => {
                setIsCallActive(true);
                setCallStatus('listening');
                callStartRef.current = Date.now();
                startAudioCapture(stream, ws);
            };

            ws.onmessage = (event) => {
                handleServerMessage(JSON.parse(event.data));
            };

            ws.onerror = (e) => {
                console.error('Voice WS error:', e);
                setError('Voice connection error');
            };

            ws.onclose = (e) => {
                console.log('Voice WS closed:', e.code, e.reason);
                stopAudioCapture();
                setIsCallActive(false);
                setCallStatus('idle');
            };
        } catch (e) {
            setError('Failed to connect to voice server');
            setCallStatus('idle');
            stopAudioCapture();
        }
    }, [sessionId]);

    /**
     * Start capturing microphone audio and sending to WebSocket.
     */
    const startAudioCapture = useCallback((stream, ws) => {
        try {
            const audioCtx = new (window.AudioContext || window.webkitAudioContext)({
                sampleRate: 48000, // Browser default, we'll downsample
            });
            audioContextRef.current = audioCtx;

            const source = audioCtx.createMediaStreamSource(stream);
            const processor = audioCtx.createScriptProcessor(4096, 1, 1);
            processorRef.current = processor;

            processor.onaudioprocess = (e) => {
                if (ws.readyState !== WebSocket.OPEN) return;

                const inputData = e.inputBuffer.getChannelData(0);
                const pcm16k = downsampleTo16kPCM(inputData, audioCtx.sampleRate);
                const base64 = pcmToBase64(pcm16k);

                ws.send(JSON.stringify({
                    type: 'audio',
                    data: base64,
                }));
            };

            source.connect(processor);
            processor.connect(audioCtx.destination); // Required for ScriptProcessor to fire
        } catch (e) {
            console.error('Audio capture error:', e);
            setError('Failed to capture audio');
        }
    }, []);

    /**
     * Stop mic capture.
     */
    const stopAudioCapture = useCallback(() => {
        if (processorRef.current) {
            processorRef.current.disconnect();
            processorRef.current = null;
        }
        if (audioContextRef.current) {
            audioContextRef.current.close().catch(() => { });
            audioContextRef.current = null;
        }
        if (mediaStreamRef.current) {
            mediaStreamRef.current.getTracks().forEach(t => t.stop());
            mediaStreamRef.current = null;
        }
    }, []);

    /**
     * Handle messages from the backend WebSocket.
     */
    const handleServerMessage = useCallback((msg) => {
        switch (msg.type) {
            case 'status':
                setCallStatus(msg.status);
                break;

            case 'user_transcript':
                if (msg.is_final) {
                    // Add to history
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
                queueAudioPlayback(msg.data, msg.content_type);
                break;

            case 'ai_audio_end':
                setAiTranscript('');
                break;

            case 'error':
                setError(msg.message);
                break;

            default:
                break;
        }
    }, []);

    /**
     * Queue and play AI audio chunks seamlessly.
     */
    const queueAudioPlayback = useCallback((base64Audio, contentType) => {
        audioQueueRef.current.push({ base64Audio, contentType });
        if (!isPlayingRef.current) {
            playNextAudio();
        }
    }, []);

    const playNextAudio = useCallback(async () => {
        if (audioQueueRef.current.length === 0) {
            isPlayingRef.current = false;
            return;
        }

        isPlayingRef.current = true;
        const { base64Audio } = audioQueueRef.current.shift();

        try {
            if (!playbackCtxRef.current || playbackCtxRef.current.state === 'closed') {
                playbackCtxRef.current = new (window.AudioContext || window.webkitAudioContext)();
            }
            const audioBuffer = await decodeBase64Audio(playbackCtxRef.current, base64Audio);
            const source = playbackCtxRef.current.createBufferSource();
            source.buffer = audioBuffer;
            source.connect(playbackCtxRef.current.destination);
            source.onended = () => playNextAudio();
            source.start();
        } catch (e) {
            console.warn('Audio playback error:', e);
            playNextAudio(); // Skip and play next
        }
    }, []);

    /**
     * Stop all AI audio playback (for interrupt).
     */
    const stopPlayback = useCallback(() => {
        audioQueueRef.current = [];
        isPlayingRef.current = false;
        if (playbackCtxRef.current && playbackCtxRef.current.state !== 'closed') {
            playbackCtxRef.current.close().catch(() => { });
            playbackCtxRef.current = null;
        }
    }, []);

    /**
     * End the voice call.
     */
    const endCall = useCallback(() => {
        // Send end_call to backend
        if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
            wsRef.current.send(JSON.stringify({ type: 'end_call' }));
            wsRef.current.close();
        }
        wsRef.current = null;

        stopAudioCapture();
        stopPlayback();

        setIsCallActive(false);
        setCallStatus('idle');
        setUserTranscript('');
        setAiTranscript('');
    }, [stopAudioCapture, stopPlayback]);

    // Cleanup on unmount
    useEffect(() => {
        return () => {
            if (wsRef.current) {
                wsRef.current.close();
            }
            stopAudioCapture();
            stopPlayback();
            if (timerRef.current) clearInterval(timerRef.current);
        };
    }, []);

    return {
        // State
        isCallActive,
        callStatus,
        error,
        callDuration,
        userTranscript,
        aiTranscript,
        callHistory,

        // Actions
        startCall,
        endCall,
        setError,
    };
}
