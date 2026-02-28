/**
 * VoiceCall — Full-screen voice negotiation overlay.
 *
 * Neo-Brutalist design matching Trade Mind's theme:
 *  - Navy #001524, Teal #15616D, Cream #FFECD1, Orange #FF7D00, Maroon #78290F
 *  - Bold borders, shadow-neo, Space Grotesk headings, Inter body
 *  - Slide animations, brutal geometry
 *
 * Features:
 *  - Live waveform indicator (orange=user, teal=AI)
 *  - Real-time transcript feed (both sides)
 *  - Call timer
 *  - End call button with pulse animation
 *  - Status indicator (Listening / Processing / AI Speaking)
 */
import { useEffect, useRef } from 'react';
import { Phone, PhoneOff, Mic, MicOff, Volume2, Loader2, X, TrendingUp, Zap } from 'lucide-react';
import useVoiceCall from './useVoiceCall';
import './VoiceCall.css';

function formatDuration(seconds) {
    const m = Math.floor(seconds / 60).toString().padStart(2, '0');
    const s = (seconds % 60).toString().padStart(2, '0');
    return `${m}:${s}`;
}

function StatusLabel({ status }) {
    const config = {
        idle: { text: 'READY', color: 'bg-neo-navy/50 text-neo-cream/60' },
        connecting: { text: 'CONNECTING...', color: 'bg-neo-orange text-neo-navy' },
        listening: { text: 'LISTENING', color: 'bg-neo-orange text-neo-navy' },
        processing: { text: 'THINKING...', color: 'bg-neo-teal text-neo-cream' },
        speaking: { text: 'AI SPEAKING', color: 'bg-neo-teal text-neo-cream' },
    };
    const c = config[status] || config.idle;
    return (
        <span className={`status-text inline-flex items-center gap-2 px-4 py-1.5 border-2 border-neo-navy font-heading font-bold text-xs uppercase tracking-widest ${c.color}`}>
            {status === 'listening' && <Mic className="w-3.5 h-3.5" />}
            {status === 'speaking' && <Volume2 className="w-3.5 h-3.5" />}
            {status === 'processing' && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
            {status === 'connecting' && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
            {c.text}
        </span>
    );
}

function WaveformBars({ status }) {
    const isUser = status === 'listening';
    const isAi = status === 'speaking';
    const isActive = isUser || isAi;
    const barClass = isUser ? 'wave-bar-user' : isAi ? 'wave-bar-ai' : 'wave-bar-idle';

    return (
        <div className="flex items-center justify-center gap-1.5 h-10">
            {[...Array(7)].map((_, i) => (
                <div
                    key={i}
                    className={`wave-bar ${isActive ? barClass : 'wave-bar-idle'}`}
                />
            ))}
        </div>
    );
}

function ThinkingDots() {
    return (
        <div className="flex items-center justify-center py-2">
            <span className="thinking-dot" />
            <span className="thinking-dot" />
            <span className="thinking-dot" />
        </div>
    );
}


export default function VoiceCall({ sessionId, config, selectedProduct, onClose, onMessage }) {
    const {
        isCallActive,
        callStatus,
        error,
        callDuration,
        userTranscript,
        aiTranscript,
        callHistory,
        startCall,
        endCall,
        setError,
    } = useVoiceCall({ sessionId });

    const transcriptEndRef = useRef(null);

    // Auto-scroll transcript
    useEffect(() => {
        transcriptEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [callHistory, userTranscript, aiTranscript]);

    // Push completed exchanges to parent chat messages on close
    const handleEndCall = () => {
        // Send transcript history back to Chat.jsx
        if (onMessage && callHistory.length > 0) {
            callHistory.forEach(entry => {
                onMessage({
                    id: Date.now() + Math.random(),
                    text: `🎙️ [Voice] ${entry.text}`,
                    sender: entry.sender === 'user' ? 'user' : 'bot',
                    timestamp: entry.timestamp,
                    meta: {
                        isVoiceCall: true,
                        ...(entry.meta || {}),
                    },
                });
            });
        }
        endCall();
        onClose();
    };

    return (
        <div className="fixed inset-0 z-50 bg-neo-navy voice-call-overlay flex flex-col">
            {/* ───── HEADER ───── */}
            <header className="border-b-4 border-neo-cream/20 p-4">
                <div className="max-w-2xl mx-auto flex items-center justify-between">
                    {/* Left: Branding + product */}
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 bg-neo-orange flex items-center justify-center border-2 border-neo-cream">
                            <Phone className="w-5 h-5 text-neo-navy" />
                        </div>
                        <div>
                            <h2 className="text-lg font-bold font-heading text-neo-cream flex items-center gap-2">
                                Voice Negotiation
                                {isCallActive && (
                                    <span className="inline-flex items-center gap-1.5 px-2 py-0.5 bg-neo-maroon border border-neo-cream/30 text-[10px] font-bold text-neo-cream uppercase tracking-widest">
                                        <span className="live-dot w-2 h-2 rounded-full bg-neo-orange inline-block" />
                                        LIVE
                                    </span>
                                )}
                            </h2>
                            <p className="text-xs text-neo-cream/50">
                                {selectedProduct ? selectedProduct.name : 'Custom Product'}
                                {config && <> · {config.mode === 'MAX_PROFIT' ? 'Max Profit' : 'Min Loss'}</>}
                            </p>
                        </div>
                    </div>

                    {/* Right: Timer + Close */}
                    <div className="flex items-center gap-3">
                        {isCallActive && (
                            <span className="font-heading font-bold text-neo-cream text-lg tabular-nums">
                                {formatDuration(callDuration)}
                            </span>
                        )}
                        <button
                            onClick={handleEndCall}
                            className="w-9 h-9 flex items-center justify-center border-2 border-neo-cream/30 text-neo-cream/60 hover:bg-neo-cream/10 hover:text-neo-cream transition-all"
                        >
                            <X className="w-5 h-5" />
                        </button>
                    </div>
                </div>
            </header>

            {/* ───── ERROR BANNER ───── */}
            {error && (
                <div className="bg-neo-maroon border-b-2 border-neo-navy p-3">
                    <div className="max-w-2xl mx-auto flex items-center gap-2 text-sm text-neo-cream font-bold">
                        <Zap className="w-4 h-4 flex-shrink-0" />
                        <p>{error}</p>
                        <button onClick={() => setError(null)} className="ml-auto underline text-xs hover:text-neo-orange">
                            Dismiss
                        </button>
                    </div>
                </div>
            )}

            {/* ───── TRANSCRIPT FEED ───── */}
            <div className="flex-1 overflow-y-auto p-4 call-transcript-scroll">
                <div className="max-w-2xl mx-auto space-y-3">
                    {/* Empty state */}
                    {!isCallActive && callHistory.length === 0 && (
                        <div className="flex flex-col items-center justify-center py-16 text-center">
                            <div className="w-20 h-20 bg-neo-teal/20 border-3 border-neo-cream/20 flex items-center justify-center mb-6">
                                <Phone className="w-10 h-10 text-neo-teal" />
                            </div>
                            <h3 className="text-xl font-bold font-heading text-neo-cream mb-2">
                                Call & Negotiate
                            </h3>
                            <p className="text-neo-cream/50 text-sm max-w-xs">
                                Start a voice call to negotiate in real-time. Speak naturally — the AI will listen, understand, and respond with voice.
                            </p>
                        </div>
                    )}

                    {/* Transcript messages */}
                    {callHistory.map((entry, i) => (
                        <div
                            key={i}
                            className={`transcript-bubble flex ${entry.sender === 'user' ? 'justify-end' : 'justify-start'}`}
                        >
                            <div
                                className={`max-w-[85%] px-4 py-3 border-2 border-neo-navy ${entry.sender === 'user'
                                        ? 'bg-neo-orange text-neo-navy'
                                        : 'bg-neo-teal text-neo-cream'
                                    }`}
                            >
                                {/* Label */}
                                <div className="flex items-center gap-2 mb-1">
                                    <span className={`text-[10px] font-bold uppercase tracking-widest ${entry.sender === 'user' ? 'text-neo-navy/60' : 'text-neo-cream/60'
                                        }`}>
                                        {entry.sender === 'user' ? '🎤 You said' : '🤖 AI said'}
                                    </span>
                                </div>

                                {/* Text */}
                                <p className="text-sm font-body whitespace-pre-line">{entry.text}</p>

                                {/* Pricing meta */}
                                {entry.meta?.pricing && entry.meta.pricing.decision && (
                                    <div className={`mt-2 pt-2 border-t ${entry.sender === 'user' ? 'border-neo-navy/20' : 'border-neo-cream/20'
                                        }`}>
                                        {entry.meta.pricing.decision === 'counter' && entry.meta.pricing.counter_offer && (
                                            <span className="text-xs font-bold">
                                                💰 Counter: ${entry.meta.pricing.counter_offer}
                                            </span>
                                        )}
                                        {entry.meta.pricing.decision === 'accept' && (
                                            <span className="text-xs font-bold">
                                                ✅ Deal accepted!
                                            </span>
                                        )}
                                        {entry.meta.pricing.decision === 'reject' && (
                                            <span className="text-xs font-bold">
                                                ❌ Offer rejected
                                            </span>
                                        )}
                                    </div>
                                )}

                                {/* Round info */}
                                {entry.meta?.round_number && (
                                    <div className={`text-[10px] mt-1 ${entry.sender === 'user' ? 'text-neo-navy/40' : 'text-neo-cream/40'
                                        }`}>
                                        Round {entry.meta.round_number}
                                        {entry.meta.rounds_remaining != null && ` · ${entry.meta.rounds_remaining} left`}
                                    </div>
                                )}

                                {/* Timestamp */}
                                <div className={`text-[10px] mt-1 ${entry.sender === 'user' ? 'text-neo-navy/40' : 'text-neo-cream/40'
                                    }`}>
                                    {entry.timestamp.toLocaleTimeString()}
                                </div>
                            </div>
                        </div>
                    ))}

                    {/* Live partial user transcript */}
                    {userTranscript && (
                        <div className="flex justify-end">
                            <div className="max-w-[85%] px-4 py-3 border-2 border-neo-navy bg-neo-orange/40 text-neo-cream">
                                <span className="text-[10px] font-bold uppercase tracking-widest text-neo-cream/50 block mb-1">
                                    🎤 Listening...
                                </span>
                                <p className="text-sm italic">{userTranscript}</p>
                            </div>
                        </div>
                    )}

                    {/* Processing indicator */}
                    {callStatus === 'processing' && (
                        <div className="flex justify-start">
                            <div className="px-4 py-3 border-2 border-neo-navy bg-neo-teal/30 text-neo-cream">
                                <span className="text-[10px] font-bold uppercase tracking-widest text-neo-cream/50 block mb-1">
                                    🤖 Thinking
                                </span>
                                <ThinkingDots />
                            </div>
                        </div>
                    )}

                    <div ref={transcriptEndRef} />
                </div>
            </div>

            {/* ───── BOTTOM CONTROLS ───── */}
            <div className="border-t-4 border-neo-cream/20 bg-neo-navy p-6">
                <div className="max-w-2xl mx-auto">
                    {/* Waveform */}
                    {isCallActive && (
                        <div className="flex flex-col items-center mb-4">
                            <WaveformBars status={callStatus} />
                            <StatusLabel status={callStatus} />
                        </div>
                    )}

                    {/* Action buttons */}
                    <div className="flex items-center justify-center gap-4">
                        {!isCallActive ? (
                            /* Start Call Button */
                            <button
                                onClick={startCall}
                                className="flex items-center gap-3 px-8 py-4 bg-neo-orange border-3 border-neo-navy text-neo-navy font-heading font-bold text-lg uppercase tracking-wide shadow-neo hover:shadow-neo-hover hover:translate-x-[2px] hover:translate-y-[2px] active:translate-x-[4px] active:translate-y-[4px] active:shadow-none transition-all"
                            >
                                <Phone className="w-6 h-6" />
                                Start Call
                            </button>
                        ) : (
                            /* End Call Button */
                            <button
                                onClick={handleEndCall}
                                className="end-call-btn flex items-center justify-center w-16 h-16 bg-neo-maroon border-3 border-neo-navy text-neo-cream rounded-full"
                            >
                                <PhoneOff className="w-7 h-7" />
                            </button>
                        )}
                    </div>

                    {/* Hint text */}
                    {isCallActive && (
                        <p className="text-center text-neo-cream/30 text-xs mt-3 font-body">
                            Speak naturally · Interrupt anytime · Your conversation is transcribed live
                        </p>
                    )}
                    {!isCallActive && callHistory.length === 0 && (
                        <p className="text-center text-neo-cream/30 text-xs mt-3 font-body">
                            Requires microphone access · Audio is processed securely
                        </p>
                    )}
                </div>
            </div>
        </div>
    );
}
