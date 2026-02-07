import { useState, useEffect, useRef } from 'react';
import { Send, Loader2, AlertCircle, TrendingUp, RotateCcw, Plus, Minus, Zap, Shield } from 'lucide-react';
import { createSession, sendChat, healthCheck, dbStartSession, dbSaveMessage, dbCloseSession } from './api';
import './Chat.css';

export default function Chat() {
    // Setup config
    const [showSetup, setShowSetup] = useState(true);
    const [config, setConfig] = useState({
        mode: 'MAX_PROFIT',
        maxRounds: 10,
        basePrice: 100,
        costPrice: 40,
    });

    // Session state
    const [sessionId, setSessionId] = useState(null);
    const [sessionInfo, setSessionInfo] = useState(null);
    const [messages, setMessages] = useState([]);
    const [inputValue, setInputValue] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [backendHealthy, setBackendHealthy] = useState(null);
    const [negotiationEnded, setNegotiationEnded] = useState(false);
    const [dbSessionId, setDbSessionId] = useState(null);
    const [lastBuyerOffer, setLastBuyerOffer] = useState(null);
    const [lastSellerOffer, setLastSellerOffer] = useState(null);
    const messagesEndRef = useRef(null);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    // Check backend health on mount
    useEffect(() => {
        healthCheck().then(ok => setBackendHealthy(ok));
    }, []);

    async function startNegotiation() {
        setLoading(true);
        setError(null);

        const sessionConfig = {
            product: {
                product_id: "TRADE-001",
                product_name: "Custom Product",
                base_price: config.basePrice,
                cost_price: config.costPrice,
                min_acceptable_price: config.costPrice,
                max_loss_percentage: 0
            },
            inventory: {
                available_quantity: 100,
                requested_quantity: 10,
                inventory_pressure: "medium",
                sales_frequency: "medium"
            },
            strategy: {
                mode: config.mode,
                urgency: "medium",
                relationship_priority: "medium",
                max_rounds: config.maxRounds
            }
        };

        try {
            const healthy = await healthCheck();
            setBackendHealthy(healthy);
            if (!healthy) {
                setError('Backend not available. Start the server first.');
                setLoading(false);
                return;
            }

            const sessionData = await createSession(sessionConfig);
            if (sessionData?.session_id) {
                setSessionId(sessionData.session_id);
                setSessionInfo(sessionData);
                setShowSetup(false);

                // ── Persist to MySQL ──
                const dbSess = await dbStartSession({
                    product_name: 'Custom Product',
                    mode: config.mode,
                    base_price: config.basePrice,
                    cost_price: config.costPrice,
                    min_price: config.costPrice,
                    max_rounds: config.maxRounds,
                });
                if (dbSess?.id) {
                    setDbSessionId(dbSess.id);
                    // Save the initial bot greeting as round 0
                    await dbSaveMessage(dbSess.id, {
                        round_number: 0,
                        user_message: null,
                        bot_reply: sessionData.message,
                        offered_price: null,
                        counter_price: sessionData.initial_offer ? parseFloat(sessionData.initial_offer) : null,
                        decision: 'chat',
                    });
                    setLastSellerOffer(sessionData.initial_offer ? parseFloat(sessionData.initial_offer) : config.basePrice);
                }
                setMessages([{
                    id: Date.now(),
                    text: sessionData.message,
                    sender: 'bot',
                    timestamp: new Date(),
                    meta: {
                        initialOffer: sessionData.initial_offer,
                        mode: sessionData.mode,
                        maxRounds: sessionData.max_rounds,
                    }
                }]);
            } else {
                setError('Failed to create session');
            }
        } catch (err) {
            setError("Failed to start: " + err.message);
        } finally {
            setLoading(false);
        }
    }

    function resetToSetup() {
        setShowSetup(true);
        setSessionId(null);
        setSessionInfo(null);
        setMessages([]);
        setNegotiationEnded(false);
        setDbSessionId(null);
        setLastBuyerOffer(null);
        setLastSellerOffer(null);
        setError(null);
        setInputValue('');
    }

    const handleSendMessage = async (e) => {
        e.preventDefault();
        if (!inputValue.trim() || !sessionId || loading || negotiationEnded) return;

        const userText = inputValue.trim();
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
            const response = await sendChat(sessionId, userText);
            if (response) {
                let botText = response.message;

                if (response.has_price_offer && response.pricing) {
                    const decision = response.pricing?.decision;
                    const counterPrice = response.pricing?.counter_offer_price;
                    const acceptedPrice = response.pricing?.accepted_price;

                    if (decision === 'counter' && counterPrice) {
                        botText += "\n\n\u{1F4B0} Counter offer: $" + parseFloat(counterPrice).toFixed(2);
                    } else if (decision === 'accept' && acceptedPrice) {
                        botText += "\n\n\u2705 Deal accepted at $" + parseFloat(acceptedPrice).toFixed(2) + "!";
                    } else if (decision === 'reject') {
                        botText += "\n\n\u274C Offer rejected.";
                    }

                    if (response.extracted_price) {
                        setMessages(prev => prev.map(m =>
                            m.id === userMessage.id
                                ? { ...m, meta: { ...m.meta, offeredPrice: parseFloat(response.extracted_price) } }
                                : m
                        ));
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

                // ── Persist round to MySQL ──
                const roundDecision = response.pricing?.decision || (response.has_price_offer ? 'counter' : 'chat');
                const offeredPrice = response.extracted_price ? parseFloat(response.extracted_price) : null;
                const counterPrice = response.pricing?.counter_offer_price ? parseFloat(response.pricing.counter_offer_price) : null;
                const acceptedPrice = response.pricing?.accepted_price ? parseFloat(response.pricing.accepted_price) : null;

                if (offeredPrice) setLastBuyerOffer(offeredPrice);
                if (counterPrice) setLastSellerOffer(counterPrice);
                if (acceptedPrice) setLastSellerOffer(acceptedPrice);

                await dbSaveMessage(dbSessionId, {
                    round_number: response.round_number || 0,
                    user_message: userText,
                    bot_reply: botText,
                    offered_price: offeredPrice,
                    counter_price: counterPrice || acceptedPrice,
                    decision: roundDecision,
                });

                if (response.can_continue === false) {
                    setNegotiationEnded(true);

                    // ── Close session in MySQL ──
                    const finalStatus = response.status || roundDecision;
                    const dealWasMade = roundDecision === 'accept';
                    await dbCloseSession(dbSessionId, {
                        status: finalStatus,
                        final_price: dealWasMade ? (acceptedPrice || offeredPrice) : null,
                        final_decision: finalStatus,
                        deal_closed: dealWasMade,
                        buyer_last_offer: offeredPrice || lastBuyerOffer,
                        seller_last_offer: counterPrice || acceptedPrice || lastSellerOffer,
                        rounds_used: response.round_number || 0,
                    });
                }
            } else {
                setError('Empty response from server');
            }
        } catch (err) {
            console.error('Send message error:', err);
            setError("Failed to send: " + err.message);
        } finally {
            setLoading(false);
        }
    };

    //  SETUP SCREEN 
    if (showSetup) {
        return (
            <div className="min-h-screen bg-neo-cream flex items-center justify-center p-4">
                <div className="w-full max-w-lg">
                    <div className="flex items-center justify-center gap-3 mb-8">
                        <div className="w-12 h-12 bg-neo-orange flex items-center justify-center border-4 border-neo-navy">
                            <TrendingUp className="w-7 h-7 text-neo-navy" />
                        </div>
                        <h1 className="text-3xl font-bold font-heading text-neo-navy">Trade Mind</h1>
                    </div>

                    <div className="neo-card p-6 space-y-6">
                        <h2 className="text-xl font-bold text-neo-navy text-center font-heading">Configure Negotiation</h2>

                        {/* Mode Toggle */}
                        <div>
                            <label className="text-xs font-bold text-neo-navy/60 mb-2 block uppercase tracking-widest">Strategy Mode</label>
                            <div className="grid grid-cols-2 gap-3">
                                <button
                                    onClick={() => setConfig({ ...config, mode: 'MAX_PROFIT' })}
                                    className={"px-4 py-3 border-3 border-neo-navy font-bold text-sm transition-all flex items-center justify-center gap-2 " + (config.mode === 'MAX_PROFIT' ? 'bg-neo-teal text-neo-cream shadow-neo' : 'bg-white text-neo-navy hover:bg-neo-navy/5')}
                                >
                                    <Zap className="w-4 h-4" />
                                    MAX PROFIT
                                </button>
                                <button
                                    onClick={() => setConfig({ ...config, mode: 'MIN_LOSS' })}
                                    className={"px-4 py-3 border-3 border-neo-navy font-bold text-sm transition-all flex items-center justify-center gap-2 " + (config.mode === 'MIN_LOSS' ? 'bg-neo-teal text-neo-cream shadow-neo' : 'bg-white text-neo-navy hover:bg-neo-navy/5')}
                                >
                                    <Shield className="w-4 h-4" />
                                    MIN LOSS
                                </button>
                            </div>
                        </div>

                        {/* Max Rounds */}
                        <div>
                            <label className="text-xs font-bold text-neo-navy/60 mb-2 block uppercase tracking-widest">Max Rounds</label>
                            <div className="flex items-center gap-3">
                                <button
                                    onClick={() => setConfig({ ...config, maxRounds: Math.max(1, config.maxRounds - 1) })}
                                    className="w-11 h-11 border-3 border-neo-navy bg-white flex items-center justify-center hover:bg-neo-navy/5"
                                >
                                    <Minus className="w-4 h-4" />
                                </button>
                                <div className="flex-1 px-4 py-2.5 border-3 border-neo-navy bg-neo-teal text-neo-cream text-center font-bold text-xl shadow-neo">
                                    {config.maxRounds}
                                </div>
                                <button
                                    onClick={() => setConfig({ ...config, maxRounds: Math.min(20, config.maxRounds + 1) })}
                                    className="w-11 h-11 border-3 border-neo-navy bg-white flex items-center justify-center hover:bg-neo-navy/5"
                                >
                                    <Plus className="w-4 h-4" />
                                </button>
                            </div>
                        </div>

                        {/* Base Price */}
                        <div>
                            <label className="text-xs font-bold text-neo-navy/60 mb-2 block uppercase tracking-widest">Base Price (Selling Price)</label>
                            <div className="flex items-center border-3 border-neo-navy overflow-hidden">
                                <span className="px-3 py-2.5 bg-neo-navy text-neo-cream font-bold text-lg">$</span>
                                <input
                                    type="number"
                                    value={config.basePrice}
                                    onChange={(e) => setConfig({ ...config, basePrice: parseFloat(e.target.value) || 0 })}
                                    className="flex-1 px-3 py-2.5 bg-white text-neo-navy font-bold text-lg focus:outline-none config-input"
                                    min="1"
                                    step="1"
                                />
                            </div>
                        </div>

                        {/* Cost Price */}
                        <div>
                            <label className="text-xs font-bold text-neo-navy/60 mb-2 block uppercase tracking-widest">Actual Cost Price</label>
                            <div className="flex items-center border-3 border-neo-navy overflow-hidden">
                                <span className="px-3 py-2.5 bg-neo-navy text-neo-cream font-bold text-lg">$</span>
                                <input
                                    type="number"
                                    value={config.costPrice}
                                    onChange={(e) => setConfig({ ...config, costPrice: parseFloat(e.target.value) || 0 })}
                                    className="flex-1 px-3 py-2.5 bg-white text-neo-navy font-bold text-lg focus:outline-none config-input"
                                    min="1"
                                    step="1"
                                />
                            </div>
                        </div>

                        {config.costPrice >= config.basePrice && (
                            <p className="text-neo-maroon text-sm font-bold flex items-center gap-1">
                                <AlertCircle className="w-4 h-4" /> Cost price must be less than base price
                            </p>
                        )}

                        {backendHealthy === false && (
                            <div className="bg-neo-maroon/10 border-2 border-neo-maroon p-3 text-sm text-neo-maroon font-bold flex items-center gap-2">
                                <AlertCircle className="w-4 h-4 flex-shrink-0" />
                                Backend not available. Start the server first.
                            </div>
                        )}
                        {backendHealthy === null && (
                            <div className="flex items-center gap-2 text-neo-navy/50 text-sm">
                                <Loader2 className="w-4 h-4 animate-spin" /> Checking backend...
                            </div>
                        )}

                        <button
                            onClick={startNegotiation}
                            disabled={loading || backendHealthy !== true || config.costPrice >= config.basePrice || config.basePrice <= 0 || config.costPrice <= 0}
                            className={"w-full py-4 border-3 border-neo-navy font-bold text-lg flex items-center justify-center gap-2 transition-all " + (loading || backendHealthy !== true || config.costPrice >= config.basePrice ? 'bg-neo-navy/20 text-neo-navy/40 cursor-not-allowed' : 'bg-neo-orange text-neo-navy shadow-neo hover:shadow-none hover:translate-x-[3px] hover:translate-y-[3px]')}
                        >
                            {loading ? (
                                <><Loader2 className="w-5 h-5 animate-spin" /> Creating Session...</>
                            ) : (
                                <><TrendingUp className="w-5 h-5" /> Start Negotiation</>
                            )}
                        </button>

                        {error && <p className="text-neo-maroon text-sm text-center font-bold">{error}</p>}
                    </div>
                </div>
            </div>
        );
    }

    //  CHAT SCREEN 
    return (
        <div className="min-h-screen bg-neo-cream flex flex-col">
            <header className="bg-neo-navy text-neo-cream border-b-4 border-neo-navy p-4">
                <div className="max-w-4xl mx-auto flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 bg-neo-orange flex items-center justify-center border-2 border-neo-cream">
                            <TrendingUp className="w-6 h-6 text-neo-navy" />
                        </div>
                        <div>
                            <h1 className="text-2xl font-bold font-heading">Trade Mind</h1>
                            <p className="text-sm text-neo-cream/70">AI Negotiation Engine</p>
                        </div>
                    </div>
                    <div className="hidden sm:flex flex-wrap items-center gap-2">
                        <span className="bg-neo-teal px-3 py-1 border-2 border-neo-cream font-bold text-xs">
                            {config.mode === 'MAX_PROFIT' ? 'MAX PROFIT' : 'MIN LOSS'}
                        </span>
                        <span className="bg-neo-teal px-3 py-1 border-2 border-neo-cream font-bold text-xs">
                            {config.maxRounds} Rounds
                        </span>
                        <span className="bg-neo-teal px-3 py-1 border-2 border-neo-cream font-bold text-xs">
                            Base ${config.basePrice}
                        </span>
                        <span className="bg-neo-teal px-3 py-1 border-2 border-neo-cream font-bold text-xs">
                            Cost ${config.costPrice}
                        </span>
                    </div>
                </div>
            </header>

            {error && (
                <div className="bg-neo-maroon text-neo-cream border-b-2 border-neo-navy p-3">
                    <div className="max-w-4xl mx-auto flex items-center gap-2 text-sm">
                        <AlertCircle className="w-4 h-4 flex-shrink-0" />
                        <p>{error}</p>
                        <button onClick={() => setError(null)} className="ml-auto underline text-xs">Dismiss</button>
                    </div>
                </div>
            )}

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
                                className={"flex " + (msg.sender === 'user' ? 'justify-end' : 'justify-start')}
                            >
                                <div className={"chat-message-" + msg.sender + " flex flex-col"}>
                                    <p className="text-sm whitespace-pre-line">{msg.text}</p>
                                    <div className="flex items-center justify-between mt-1 gap-3">
                                        <span className="text-xs opacity-70">
                                            {msg.timestamp.toLocaleTimeString()}
                                        </span>
                                        {msg.meta?.round && (
                                            <span className="text-xs opacity-70">
                                                Round {msg.meta.round} \u2022 {msg.meta.roundsRemaining} left
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

            {negotiationEnded && (
                <div className="bg-neo-navy text-neo-cream p-4 border-t-4 border-neo-orange">
                    <div className="max-w-4xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-3">
                        <p className="font-bold font-heading">Negotiation Complete</p>
                        <button
                            onClick={resetToSetup}
                            className="neo-button bg-neo-orange text-neo-navy px-5 py-2 font-bold flex items-center gap-2 text-sm"
                        >
                            <RotateCcw className="w-4 h-4" /> New Negotiation
                        </button>
                    </div>
                </div>
            )}

            {!negotiationEnded && (
                <footer className="bg-neo-cream border-t-4 border-neo-navy p-4">
                    <form onSubmit={handleSendMessage} className="max-w-4xl mx-auto">
                        <div className="flex gap-3">
                            <input
                                type="text"
                                value={inputValue}
                                onChange={(e) => setInputValue(e.target.value)}
                                placeholder='Type anything \u2014 "hello", "why so expensive?", "I offer $70"...'
                                className="flex-1 px-4 py-3 border-3 border-neo-navy bg-white text-neo-navy placeholder-neo-navy/50 focus:outline-none font-body"
                                disabled={loading || !sessionId}
                            />
                            <button
                                type="submit"
                                disabled={loading || !sessionId || !inputValue.trim()}
                                className={"neo-button px-6 py-3 font-bold flex items-center gap-2 " + (loading || !sessionId || !inputValue.trim() ? 'bg-neo-navy/30 opacity-50 cursor-not-allowed' : 'bg-neo-orange text-neo-navy hover:bg-neo-orange/90')}
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
