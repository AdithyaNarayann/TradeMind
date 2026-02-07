import { useState, useEffect, useRef } from 'react';
import { Send, Loader2, AlertCircle, TrendingUp, DollarSign, RotateCcw } from 'lucide-react';
import { createSession, sendChat, getSession, healthCheck, extractPrice } from './api';
import './Chat.css';

export default function Chat() {
    const [sessionId, setSessionId] = useState(null);
    const [sessionInfo, setSessionInfo] = useState(null); // initial_offer, max_rounds, mode
    const [messages, setMessages] = useState([]);
    const [inputValue, setInputValue] = useState('');
    const [loading, setLoading] = useState(false);
    const [initializing, setInitializing] = useState(true);
    const [error, setError] = useState(null);
    const [backendHealthy, setBackendHealthy] = useState(false);
    const [negotiationEnded, setNegotiationEnded] = useState(false);
    const messagesEndRef = useRef(null);

    // Scroll to bottom of messages
    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    // Initialize session
    useEffect(() => {
        initSession();
    }, []);

    async function initSession() {
        setInitializing(true);
        setError(null);
        setMessages([]);
        setNegotiationEnded(false);

        try {
            const healthy = await healthCheck();
            setBackendHealthy(healthy);

            if (!healthy) {
                setError('Backend service is not available. Please ensure the backend is running on http://127.0.0.1:8000');
                setInitializing(false);
                return;
            }

            // Create session with default product config
            const sessionData = await createSession();

            if (sessionData && sessionData.session_id) {
                setSessionId(sessionData.session_id);
                setSessionInfo(sessionData);

                // Show the initial offer as a bot message
                const welcomeMsg = {
                    id: Date.now(),
                    text: sessionData.message,
                    sender: 'bot',
                    timestamp: new Date(),
                    meta: {
                        initialOffer: sessionData.initial_offer,
                        mode: sessionData.mode,
                        maxRounds: sessionData.max_rounds,
                    }
                };
                setMessages([welcomeMsg]);
                setError(null);
            } else {
                setError('Failed to create session — unexpected response');
            }
        } catch (err) {
            console.error('Initialization error:', err);
            setError(`Failed to initialize: ${err.message}`);
        } finally {
            setInitializing(false);
        }
    }

    const handleSendMessage = async (e) => {
        e.preventDefault();

        if (!inputValue.trim() || !sessionId || loading || negotiationEnded) return;

        const userText = inputValue.trim();

        // Add user message to chat
        const userMessage = {
            id: Date.now(),
            text: userText,
            sender: 'user',
            timestamp: new Date(),
            meta: {}
        };

        setMessages(prev => [...prev, userMessage]);
        setInputValue('');
        setLoading(true);
        setError(null);

        try {
            // Send as free-text chat — AI will understand intent
            const response = await sendChat(sessionId, userText);

            if (response) {
                let botText = response.message;

                if (response.has_price_offer && response.pricing) {
                    // AI found a price in the message and processed it
                    const decision = response.pricing?.decision;
                    const counterPrice = response.pricing?.counter_offer_price;
                    const acceptedPrice = response.pricing?.accepted_price;

                    if (decision === 'counter' && counterPrice) {
                        botText += `\n\n💰 Counter offer: $${parseFloat(counterPrice).toFixed(2)}`;
                    } else if (decision === 'accept' && acceptedPrice) {
                        botText += `\n\n✅ Deal accepted at $${parseFloat(acceptedPrice).toFixed(2)}!`;
                    } else if (decision === 'reject') {
                        botText += `\n\n❌ Offer rejected.`;
                    }

                    // Update user message with extracted price
                    if (response.extracted_price) {
                        userMessage.meta.offeredPrice = parseFloat(response.extracted_price);
                        setMessages(prev => prev.map(m => m.id === userMessage.id ? { ...m, meta: { ...m.meta, offeredPrice: parseFloat(response.extracted_price) } } : m));
                    }
                }

                const botMessage = {
                    id: Date.now() + 1,
                    text: botText,
                    sender: 'bot',
                    timestamp: new Date(),
                    meta: {
                        decision: response.pricing?.decision,
                        counterPrice: response.pricing?.counter_offer_price,
                        acceptedPrice: response.pricing?.accepted_price,
                        round: response.round_number,
                        roundsRemaining: response.rounds_remaining,
                        status: response.status,
                        margin: response.pricing?.margin_percentage,
                        isChat: !response.has_price_offer,
                    }
                };
                setMessages(prev => [...prev, botMessage]);

                // Check if negotiation ended
                if (response.can_continue === false) {
                    setNegotiationEnded(true);
                }
            } else {
                setError('Empty response from server');
            }
        } catch (err) {
            console.error('Send message error:', err);
            setError(`Failed to send message: ${err.message}`);
        } finally {
            setLoading(false);
        }
    };

    if (initializing) {
        return (
            <div className="min-h-screen bg-neo-cream flex items-center justify-center">
                <div className="neo-card p-8 text-center">
                    <Loader2 className="w-10 h-10 animate-spin text-neo-teal mx-auto mb-4" />
                    <h2 className="text-xl font-bold text-neo-navy mb-2">Initializing Trade Mind Chat</h2>
                    <p className="text-neo-navy/70">Creating negotiation session...</p>
                </div>
            </div>
        );
    }

    if (!backendHealthy) {
        return (
            <div className="min-h-screen bg-neo-cream flex items-center justify-center">
                <div className="neo-card p-8 text-center max-w-md">
                    <AlertCircle className="w-12 h-12 text-neo-maroon mx-auto mb-4" />
                    <h2 className="text-xl font-bold text-neo-navy mb-2">Backend Service Unavailable</h2>
                    <p className="text-neo-navy/70 mb-4">
                        {error || 'The backend service is not running.'}
                    </p>
                    <div className="text-left bg-neo-navy/10 p-4 border-l-4 border-neo-orange mb-4">
                        <p className="text-sm font-mono text-neo-navy">
                            <code className="bg-neo-navy text-neo-cream px-2 py-1">cd backend && python -m uvicorn src.app:app --reload</code>
                        </p>
                    </div>
                    <button
                        onClick={initSession}
                        className="neo-button bg-neo-orange text-neo-navy px-6 py-3 font-bold flex items-center gap-2 mx-auto"
                    >
                        <RotateCcw className="w-4 h-4" /> Retry
                    </button>
                </div>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-neo-cream flex flex-col">
            {/* Header */}
            <header className="bg-neo-navy text-neo-cream border-b-4 border-neo-navy p-4">
                <div className="max-w-4xl mx-auto flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 bg-neo-orange flex items-center justify-center border-2 border-neo-cream">
                            <TrendingUp className="w-6 h-6 text-neo-navy" />
                        </div>
                        <div>
                            <h1 className="text-2xl font-bold font-heading">Trade Mind Chat</h1>
                            <p className="text-sm text-neo-cream/70">AI Negotiation Engine</p>
                        </div>
                    </div>
                    {sessionInfo && (
                        <div className="hidden sm:flex items-center gap-4 text-sm">
                            <span className="bg-neo-teal px-3 py-1 border-2 border-neo-cream font-bold">
                                {sessionInfo.mode === 'max_profit' ? 'MAX PROFIT' : 'MIN LOSS'}
                            </span>
                            <span className="text-neo-cream/70">
                                Max {sessionInfo.max_rounds} rounds
                            </span>
                        </div>
                    )}
                </div>
            </header>

            {/* Error Banner */}
            {error && (
                <div className="bg-neo-maroon text-neo-cream border-b-2 border-neo-navy p-3">
                    <div className="max-w-4xl mx-auto flex items-center gap-2 text-sm">
                        <AlertCircle className="w-4 h-4 flex-shrink-0" />
                        <p>{error}</p>
                        <button onClick={() => setError(null)} className="ml-auto underline text-xs">Dismiss</button>
                    </div>
                </div>
            )}

            {/* Session Bar */}
            <div className="bg-neo-teal text-neo-cream p-2 text-center text-xs sm:text-sm flex items-center justify-center gap-2">
                <DollarSign className="w-4 h-4" />
                Session: <code className="bg-neo-navy px-2 py-0.5 font-mono text-xs">{sessionId ? sessionId.slice(0, 8) + '...' : '—'}</code>
                {sessionInfo && (
                    <span className="ml-2">| Base price: <strong>${parseFloat(sessionInfo.initial_offer).toFixed(2)}</strong></span>
                )}
            </div>

            {/* Messages Container */}
            <div className="flex-1 overflow-y-auto p-4 max-w-4xl mx-auto w-full">
                <div className="space-y-4">
                    {messages.length === 0 ? (
                        <div className="text-center py-12">
                            <TrendingUp className="w-12 h-12 text-neo-teal/30 mx-auto mb-4" />
                            <h3 className="text-lg font-bold text-neo-navy mb-2">Start Negotiating</h3>
                            <p className="text-neo-navy/60">Say hello, ask about the product, or make a price offer!</p>
                        </div>
                    ) : (
                        messages.map((msg) => (
                            <div
                                key={msg.id}
                                className={`flex ${msg.sender === 'user' ? 'justify-end' : 'justify-start'}`}
                            >
                                <div className={`chat-message-${msg.sender} flex flex-col`}>
                                    <p className="text-sm whitespace-pre-line">{msg.text}</p>
                                    <div className="flex items-center justify-between mt-1 gap-3">
                                        <span className="text-xs opacity-70">
                                            {msg.timestamp.toLocaleTimeString()}
                                        </span>
                                        {msg.meta?.round && (
                                            <span className="text-xs opacity-70">
                                                Round {msg.meta.round} • {msg.meta.roundsRemaining} left
                                            </span>
                                        )}
                                        {msg.meta?.offeredPrice && (
                                            <span className="text-xs font-bold opacity-90">
                                                ${msg.meta.offeredPrice.toFixed(2)}
                                            </span>
                                        )}
                                    </div>
                                </div>
                            </div>
                        ))
                    )}
                    {loading && (
                        <div className="flex justify-start">
                            <div className="chat-message-bot">
                                <div className="flex items-center gap-2">
                                    <Loader2 className="w-4 h-4 animate-spin" />
                                    <span>Thinking...</span>
                                </div>
                            </div>
                        </div>
                    )}
                    <div ref={messagesEndRef} />
                </div>
            </div>

            {/* Negotiation Ended Banner */}
            {negotiationEnded && (
                <div className="bg-neo-navy text-neo-cream p-4 border-t-4 border-neo-orange">
                    <div className="max-w-4xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-3">
                        <p className="font-bold font-heading">Negotiation Complete</p>
                        <button
                            onClick={initSession}
                            className="neo-button bg-neo-orange text-neo-navy px-5 py-2 font-bold flex items-center gap-2 text-sm"
                        >
                            <RotateCcw className="w-4 h-4" /> New Negotiation
                        </button>
                    </div>
                </div>
            )}

            {/* Input Form */}
            {!negotiationEnded && (
                <footer className="bg-neo-cream border-t-4 border-neo-navy p-4">
                    <form onSubmit={handleSendMessage} className="max-w-4xl mx-auto">
                        <div className="flex gap-3">
                            <input
                                type="text"
                                value={inputValue}
                                onChange={(e) => setInputValue(e.target.value)}
                                placeholder='Type anything — "hello", "why so expensive?", "I offer $70"...'
                                className="flex-1 px-4 py-3 border-3 border-neo-navy bg-white text-neo-navy placeholder-neo-navy/50 focus:outline-none font-body"
                                disabled={loading || !sessionId}
                            />
                            <button
                                type="submit"
                                disabled={loading || !sessionId || !inputValue.trim()}
                                className={`neo-button px-6 py-3 font-bold flex items-center gap-2 ${loading || !sessionId || !inputValue.trim()
                                    ? 'bg-neo-navy/30 opacity-50 cursor-not-allowed'
                                    : 'bg-neo-orange text-neo-navy hover:bg-neo-orange/90'
                                    }`}
                            >
                                <Send className="w-5 h-5" />
                                Send
                            </button>
                        </div>
                    </form>
                </footer>
            )}
        </div>
    );
}
