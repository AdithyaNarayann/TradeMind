/**
 * VoiceCall — Full-screen voice negotiation overlay.
 *
 * Production call UI:
 *  - Real audio waveform (driven by RMS energy from AudioWorklet/AnalyserNode)
 *  - Mute/unmute toggle
 *  - Volume slider for AI voice
 *  - Connection quality indicator (green/yellow/red)
 *  - Post-call summary modal
 *  - Keyboard shortcuts (Esc=end, M=mute)
 *  - Live transcript feed (secondary — voice is primary)
 *  - Call timer
 */
import { useState, useEffect, useRef, useMemo } from 'react';
import {
    Phone, PhoneOff, Mic, MicOff, Volume2, VolumeX,
    Loader2, X, Zap, Wifi, WifiOff, ChevronDown, ChevronUp,
    TrendingUp, Clock, DollarSign, CheckCircle, XCircle,
} from 'lucide-react';
import useVoiceCall from './useVoiceCall';
import './VoiceCall.css';

// ── Helpers ────────────────────────────────────────────────────────
function formatDuration(seconds) {
    const m = Math.floor(seconds / 60).toString().padStart(2, '0');
    const s = (seconds % 60).toString().padStart(2, '0');
    return `${m}:${s}`;
}

// ── Connection Quality Dot ─────────────────────────────────────────
function QualityDot({ quality }) {
    const colors = { good: 'bg-green-400', fair: 'bg-yellow-400', poor: 'bg-red-500' };
    return (
        <span title={`Connection: ${quality}`} className="flex items-center gap-1">
            <span className={`w-2 h-2 rounded-full ${colors[quality] || colors.good}`} />
        </span>
    );
}

// ── Status Label ───────────────────────────────────────────────────
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

// ── Real Audio Waveform ────────────────────────────────────────────
function RealWaveform({ energy, type }) {
    // Energy is 0–1 RMS, we generate 9 bars with slight randomization
    const barCount = 9;
    const bars = useMemo(() => {
        return Array.from({ length: barCount }, (_, i) => {
            const center = Math.abs(i - Math.floor(barCount / 2));
            const falloff = 1 - (center / (barCount / 2)) * 0.4;
            return falloff;
        });
    }, []);

    const isUser = type === 'user';
    const barColor = isUser ? 'bg-neo-orange' : 'bg-neo-teal';
    const minH = 6;
    const maxH = 48;

    return (
        <div className="flex items-center justify-center gap-1 h-14">
            {bars.map((falloff, i) => {
                const h = Math.max(minH, minH + (maxH - minH) * energy * falloff);
                return (
                    <div
                        key={i}
                        className={`rounded-sm transition-all duration-75 ${barColor}`}
                        style={{
                            width: '5px',
                            height: `${h}px`,
                            border: '1px solid #001524',
                        }}
                    />
                );
            })}
        </div>
    );
}

// ── Thinking Dots ──────────────────────────────────────────────────
function ThinkingDots() {
    return (
        <div className="flex items-center justify-center py-2">
            <span className="thinking-dot" />
            <span className="thinking-dot" />
            <span className="thinking-dot" />
        </div>
    );
}

// ── Post-Call Summary ──────────────────────────────────────────────
function CallSummary({ callHistory, callDuration, onClose }) {
    const rounds = callHistory.filter(e => e.sender === 'bot' && e.meta?.round_number).length;
    const lastBot = [...callHistory].reverse().find(e => e.sender === 'bot');
    const decision = lastBot?.meta?.pricing?.decision;
    const finalPrice = lastBot?.meta?.pricing?.counter_offer || lastBot?.meta?.pricing?.accepted_price;
    const isAccepted = decision === 'accept';
    const isRejected = decision === 'reject';

    return (
        <div className="fixed inset-0 z-[60] bg-neo-navy/90 flex items-center justify-center p-4 voice-call-overlay">
            <div className="bg-neo-navy border-4 border-neo-cream/30 max-w-md w-full p-6 space-y-4 shadow-neo">
                <h3 className="text-xl font-bold font-heading text-neo-cream text-center">
                    Call Summary
                </h3>

                <div className="grid grid-cols-2 gap-3">
                    <div className="bg-neo-cream/10 border-2 border-neo-cream/20 p-3 text-center">
                        <Clock className="w-5 h-5 text-neo-orange mx-auto mb-1" />
                        <p className="text-neo-cream/60 text-[10px] uppercase tracking-widest">Duration</p>
                        <p className="text-neo-cream font-heading font-bold text-lg">{formatDuration(callDuration)}</p>
                    </div>
                    <div className="bg-neo-cream/10 border-2 border-neo-cream/20 p-3 text-center">
                        <TrendingUp className="w-5 h-5 text-neo-teal mx-auto mb-1" />
                        <p className="text-neo-cream/60 text-[10px] uppercase tracking-widest">Rounds</p>
                        <p className="text-neo-cream font-heading font-bold text-lg">{rounds || '—'}</p>
                    </div>
                    <div className="bg-neo-cream/10 border-2 border-neo-cream/20 p-3 text-center">
                        <DollarSign className="w-5 h-5 text-neo-orange mx-auto mb-1" />
                        <p className="text-neo-cream/60 text-[10px] uppercase tracking-widest">Final Price</p>
                        <p className="text-neo-cream font-heading font-bold text-lg">{finalPrice ? `$${finalPrice}` : '—'}</p>
                    </div>
                    <div className="bg-neo-cream/10 border-2 border-neo-cream/20 p-3 text-center">
                        {isAccepted ? <CheckCircle className="w-5 h-5 text-green-400 mx-auto mb-1" /> :
                         isRejected ? <XCircle className="w-5 h-5 text-red-400 mx-auto mb-1" /> :
                         <Phone className="w-5 h-5 text-neo-cream/40 mx-auto mb-1" />}
                        <p className="text-neo-cream/60 text-[10px] uppercase tracking-widest">Outcome</p>
                        <p className="text-neo-cream font-heading font-bold text-lg capitalize">
                            {isAccepted ? 'Deal!' : isRejected ? 'Rejected' : decision || 'Open'}
                        </p>
                    </div>
                </div>

                <div className="max-h-40 overflow-y-auto call-transcript-scroll bg-neo-navy/50 border border-neo-cream/10 p-2 space-y-1">
                    {callHistory.map((entry, i) => (
                        <p key={i} className={`text-xs ${entry.sender === 'user' ? 'text-neo-orange' : 'text-neo-teal'}`}>
                            <span className="font-bold">{entry.sender === 'user' ? 'You' : 'AI'}:</span> {entry.text}
                        </p>
                    ))}
                </div>

                <button
                    onClick={onClose}
                    className="w-full py-3 bg-neo-orange border-3 border-neo-navy text-neo-navy font-heading font-bold uppercase tracking-wide shadow-neo hover:shadow-neo-hover transition-all"
                >
                    Close
                </button>
            </div>
        </div>
    );
}


// ════════════════════════════════════════════════════════════════════
// ██  MAIN COMPONENT
// ════════════════════════════════════════════════════════════════════

export default function VoiceCall({ sessionId, config, selectedProduct, onClose, onMessage }) {
    const {
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
        startCall,
        endCall,
        toggleMute,
        setVolume,
        setError,
    } = useVoiceCall({ sessionId });

    const [showTranscript, setShowTranscript] = useState(false);
    const [showSummary, setShowSummary] = useState(false);
    const [savedHistory, setSavedHistory] = useState([]);
    const [savedDuration, setSavedDuration] = useState(0);
    const transcriptEndRef = useRef(null);

    // Auto-scroll transcript
    useEffect(() => {
        if (showTranscript) {
            transcriptEndRef.current?.scrollIntoView({ behavior: 'smooth' });
        }
    }, [callHistory, userTranscript, aiTranscript, showTranscript]);

    // Handle end call → show summary → push to parent
    const handleEndCall = () => {
        setSavedHistory([...callHistory]);
        setSavedDuration(callDuration);
        endCall();

        if (callHistory.length > 0) {
            setShowSummary(true);
        } else {
            closeFully();
        }
    };

    const closeFully = () => {
        // Push transcripts to parent chat
        if (onMessage && savedHistory.length > 0) {
            savedHistory.forEach(entry => {
                onMessage({
                    id: Date.now() + Math.random(),
                    text: `🎙️ [Voice] ${entry.text}`,
                    sender: entry.sender === 'user' ? 'user' : 'bot',
                    timestamp: entry.timestamp,
                    meta: { isVoiceCall: true, ...(entry.meta || {}) },
                });
            });
        }
        setShowSummary(false);
        onClose();
    };

    // If summary is showing
    if (showSummary) {
        return <CallSummary callHistory={savedHistory} callDuration={savedDuration} onClose={closeFully} />;
    }

    return (
        <div className="fixed inset-0 z-50 bg-neo-navy voice-call-overlay flex flex-col">
            {/* ───── HEADER ───── */}
            <header className="border-b-4 border-neo-cream/20 p-4">
                <div className="max-w-2xl mx-auto flex items-center justify-between">
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

                    <div className="flex items-center gap-3">
                        {isCallActive && <QualityDot quality={connectionQuality} />}
                        {isCallActive && (
                            <span className="font-heading font-bold text-neo-cream text-lg tabular-nums">
                                {formatDuration(callDuration)}
                            </span>
                        )}
                        <button
                            onClick={isCallActive ? handleEndCall : onClose}
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

            {/* ───── MAIN CALL AREA (voice-first) ───── */}
            <div className="flex-1 flex flex-col items-center justify-center p-6 relative">
                {/* Empty state */}
                {!isCallActive && callHistory.length === 0 && !showSummary && (
                    <div className="flex flex-col items-center justify-center text-center">
                        <div className="w-24 h-24 bg-neo-teal/20 border-3 border-neo-cream/20 flex items-center justify-center mb-6 rounded-full">
                            <Phone className="w-12 h-12 text-neo-teal" />
                        </div>
                        <h3 className="text-2xl font-bold font-heading text-neo-cream mb-2">
                            Call & Negotiate
                        </h3>
                        <p className="text-neo-cream/50 text-sm max-w-xs mb-2">
                            Start a voice call to negotiate in real-time. Speak naturally — say a price and the AI responds instantly.
                        </p>
                        <p className="text-neo-cream/30 text-xs">
                            Requires microphone · Press <kbd className="px-1 py-0.5 bg-neo-cream/10 border border-neo-cream/20 text-[10px] rounded">M</kbd> to mute · <kbd className="px-1 py-0.5 bg-neo-cream/10 border border-neo-cream/20 text-[10px] rounded">Esc</kbd> to end
                        </p>
                    </div>
                )}

                {/* Active call: waveform + status */}
                {isCallActive && (
                    <div className="flex flex-col items-center gap-6 w-full max-w-md">
                        {/* AI Waveform (big, centered — this is the primary visual) */}
                        <div className="flex flex-col items-center gap-2">
                            <p className="text-neo-cream/40 text-[10px] uppercase tracking-widest font-bold">AI Voice</p>
                            <RealWaveform energy={callStatus === 'speaking' ? aiEnergy : 0} type="ai" />
                        </div>

                        {/* Status */}
                        <StatusLabel status={callStatus} />

                        {/* Live transcript (small, secondary) */}
                        {(callStatus === 'speaking' || callStatus === 'processing') && aiTranscript && (
                            <div className="bg-neo-teal/20 border border-neo-cream/10 px-4 py-2 max-w-sm text-center">
                                <p className="text-neo-cream text-sm">{aiTranscript}</p>
                            </div>
                        )}
                        {callStatus === 'processing' && <ThinkingDots />}
                        {userTranscript && (
                            <div className="bg-neo-orange/20 border border-neo-cream/10 px-4 py-2 max-w-sm text-center">
                                <p className="text-neo-cream/80 text-sm italic">🎤 {userTranscript}</p>
                            </div>
                        )}

                        {/* User Waveform (smaller) */}
                        <div className="flex flex-col items-center gap-1">
                            <RealWaveform energy={callStatus === 'listening' && !isMuted ? userEnergy : 0} type="user" />
                            <p className="text-neo-cream/40 text-[10px] uppercase tracking-widest font-bold">
                                {isMuted ? 'MUTED' : 'Your Voice'}
                            </p>
                        </div>
                    </div>
                )}

                {/* Transcript toggle (slide-up drawer) */}
                {isCallActive && callHistory.length > 0 && (
                    <button
                        onClick={() => setShowTranscript(prev => !prev)}
                        className="absolute bottom-2 left-1/2 -translate-x-1/2 flex items-center gap-1 text-neo-cream/30 text-xs hover:text-neo-cream/60 transition-colors"
                    >
                        {showTranscript ? <ChevronDown className="w-3 h-3" /> : <ChevronUp className="w-3 h-3" />}
                        {showTranscript ? 'Hide' : 'Show'} Transcript ({callHistory.length})
                    </button>
                )}
            </div>

            {/* ───── TRANSCRIPT DRAWER ───── */}
            {showTranscript && isCallActive && (
                <div className="h-48 border-t-2 border-neo-cream/10 overflow-y-auto p-3 call-transcript-scroll bg-neo-navy/80">
                    <div className="max-w-2xl mx-auto space-y-2">
                        {callHistory.map((entry, i) => (
                            <div key={i} className={`flex ${entry.sender === 'user' ? 'justify-end' : 'justify-start'}`}>
                                <div className={`max-w-[80%] px-3 py-2 border border-neo-navy text-xs ${
                                    entry.sender === 'user'
                                        ? 'bg-neo-orange/80 text-neo-navy'
                                        : 'bg-neo-teal/80 text-neo-cream'
                                }`}>
                                    <span className="font-bold">{entry.sender === 'user' ? 'You' : 'AI'}:</span> {entry.text}
                                    {entry.meta?.pricing?.decision === 'counter' && entry.meta.pricing.counter_offer && (
                                        <span className="block mt-1 font-bold">💰 Counter: ${entry.meta.pricing.counter_offer}</span>
                                    )}
                                    {entry.meta?.pricing?.decision === 'accept' && (
                                        <span className="block mt-1 font-bold">✅ Deal accepted!</span>
                                    )}
                                </div>
                            </div>
                        ))}
                        <div ref={transcriptEndRef} />
                    </div>
                </div>
            )}

            {/* ───── BOTTOM CONTROLS ───── */}
            <div className="border-t-4 border-neo-cream/20 bg-neo-navy p-5">
                <div className="max-w-2xl mx-auto">
                    <div className="flex items-center justify-center gap-4">
                        {!isCallActive ? (
                            <button
                                onClick={startCall}
                                className="flex items-center gap-3 px-8 py-4 bg-neo-orange border-3 border-neo-navy text-neo-navy font-heading font-bold text-lg uppercase tracking-wide shadow-neo hover:shadow-neo-hover hover:translate-x-[2px] hover:translate-y-[2px] active:translate-x-[4px] active:translate-y-[4px] active:shadow-none transition-all"
                            >
                                <Phone className="w-6 h-6" />
                                Start Call
                            </button>
                        ) : (
                            <>
                                {/* Mute Button */}
                                <button
                                    onClick={toggleMute}
                                    title={isMuted ? 'Unmute (M)' : 'Mute (M)'}
                                    className={`w-12 h-12 flex items-center justify-center border-2 rounded-full transition-all ${
                                        isMuted
                                            ? 'bg-neo-maroon border-neo-cream/30 text-neo-cream'
                                            : 'bg-neo-cream/10 border-neo-cream/20 text-neo-cream/70 hover:bg-neo-cream/20'
                                    }`}
                                >
                                    {isMuted ? <MicOff className="w-5 h-5" /> : <Mic className="w-5 h-5" />}
                                </button>

                                {/* End Call */}
                                <button
                                    onClick={handleEndCall}
                                    title="End call (Esc)"
                                    className="end-call-btn flex items-center justify-center w-16 h-16 bg-neo-maroon border-3 border-neo-navy text-neo-cream rounded-full"
                                >
                                    <PhoneOff className="w-7 h-7" />
                                </button>

                                {/* Volume */}
                                <div className="flex items-center gap-2">
                                    <button
                                        onClick={() => setVolume(v => v > 0 ? 0 : 1)}
                                        className="w-12 h-12 flex items-center justify-center border-2 border-neo-cream/20 rounded-full text-neo-cream/70 hover:bg-neo-cream/10 transition-all"
                                        title="Toggle AI volume"
                                    >
                                        {volume === 0 ? <VolumeX className="w-5 h-5" /> : <Volume2 className="w-5 h-5" />}
                                    </button>
                                    <input
                                        type="range"
                                        min="0"
                                        max="1"
                                        step="0.05"
                                        value={volume}
                                        onChange={(e) => setVolume(parseFloat(e.target.value))}
                                        className="w-20 h-1 accent-neo-teal cursor-pointer"
                                        title={`Volume: ${Math.round(volume * 100)}%`}
                                    />
                                </div>
                            </>
                        )}
                    </div>

                    {isCallActive && (
                        <p className="text-center text-neo-cream/25 text-xs mt-3 font-body">
                            Speak naturally · Say a price to negotiate · <kbd className="px-1 bg-neo-cream/5 border border-neo-cream/10 text-[10px] rounded">M</kbd> mute · <kbd className="px-1 bg-neo-cream/5 border border-neo-cream/10 text-[10px] rounded">Esc</kbd> end
                        </p>
                    )}
                </div>
            </div>
        </div>
    );
}
