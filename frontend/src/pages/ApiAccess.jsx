import { useState, useEffect } from 'react';
import {
    Key, Plus, Copy, Check, Trash2, Code2, AlertCircle, Loader2,
    Shield, Zap, RefreshCw, Eye, EyeOff
} from 'lucide-react';
import Layout from '../components/Layout';
import NeoCard from '../components/NeoCard';
import NeoButton from '../components/NeoButton';
import { getAuthToken } from '../lib/api';

const AUTH_API = import.meta.env.VITE_AUTH_API_URL || 'http://localhost:8000';

// ── API helpers ────────────────────────────────────────────────────
async function fetchKeys() {
    const res = await fetch(`${AUTH_API}/api/v1/api-keys`, {
        headers: { Authorization: `Bearer ${getAuthToken()}` },
    });
    if (!res.ok) throw new Error('Failed to load keys');
    return (await res.json()).keys;
}

async function generateKey(label) {
    const res = await fetch(`${AUTH_API}/api/v1/api-keys`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${getAuthToken()}`,
        },
        body: JSON.stringify({ label }),
    });
    if (!res.ok) throw new Error('Failed to generate key');
    return res.json();
}

async function revokeKey(id) {
    const res = await fetch(`${AUTH_API}/api/v1/api-keys/${id}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${getAuthToken()}` },
    });
    if (!res.ok) throw new Error('Failed to revoke key');
}

// ── Code snippets ──────────────────────────────────────────────────
const LANGS = ['Python', 'JavaScript', 'TypeScript'];

function getSnippet(lang, apiKey) {
    const key = apiKey || 'tm_YOUR_API_KEY_HERE';
    const base = 'http://localhost:8000';

    if (lang === 'Python') {
        return `import requests

API_KEY = "${key}"
BASE_URL = "${base}"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

# ── Start a negotiation session ────────────────────────
payload = {
    "product_name": "Premium Widget",
    "base_price": 100.0,
    "cost_price": 40.0,
    "min_acceptable_price": 60.0,
    "max_rounds": 10,
    "strategy_mode": "MAX_PROFIT"
}

response = requests.post(
    f"{BASE_URL}/api/v1/chat-sessions",
    json=payload,
    headers=headers
)
session = response.json()
print("Session ID:", session["id"])

# ── Send a buyer offer ─────────────────────────────────
offer_payload = {
    "user_message": "I'd like to buy this for $65",
    "bot_reply": "",          # filled by negotiation engine
    "buyer_offer": 65.0,
    "seller_counter": None,
    "round_number": 1
}

msg_response = requests.post(
    f"{BASE_URL}/api/v1/chat-sessions/{session['id']}/messages",
    json=offer_payload,
    headers=headers
)
print("Bot reply:", msg_response.json())`;
    }

    if (lang === 'JavaScript') {
        return `const API_KEY = "${key}";
const BASE_URL = "${base}";

const headers = {
  "Authorization": \`Bearer \${API_KEY}\`,
  "Content-Type": "application/json"
};

// ── Start a negotiation session ────────────────────────
async function startSession() {
  const res = await fetch(\`\${BASE_URL}/api/v1/chat-sessions\`, {
    method: "POST",
    headers,
    body: JSON.stringify({
      product_name: "Premium Widget",
      base_price: 100.0,
      cost_price: 40.0,
      min_acceptable_price: 60.0,
      max_rounds: 10,
      strategy_mode: "MAX_PROFIT"
    })
  });
  const session = await res.json();
  console.log("Session ID:", session.id);
  return session;
}

// ── Send a buyer offer ─────────────────────────────────
async function sendOffer(sessionId, offer) {
  const res = await fetch(
    \`\${BASE_URL}/api/v1/chat-sessions/\${sessionId}/messages\`,
    {
      method: "POST",
      headers,
      body: JSON.stringify({
        user_message: \`I'd like to buy this for $\${offer}\`,
        bot_reply: "",
        buyer_offer: offer,
        seller_counter: null,
        round_number: 1
      })
    }
  );
  return res.json();
}

startSession().then(s => sendOffer(s.id, 65));`;
    }

    // TypeScript
    return `const API_KEY: string = "${key}";
const BASE_URL: string = "${base}";

interface SessionPayload {
  product_name: string;
  base_price: number;
  cost_price: number;
  min_acceptable_price: number;
  max_rounds: number;
  strategy_mode: "MAX_PROFIT" | "MIN_LOSS";
}

interface MessagePayload {
  user_message: string;
  bot_reply: string;
  buyer_offer: number;
  seller_counter: number | null;
  round_number: number;
}

const headers: Record<string, string> = {
  "Authorization": \`Bearer \${API_KEY}\`,
  "Content-Type": "application/json"
};

// ── Start a negotiation session ────────────────────────
async function startSession(): Promise<any> {
  const payload: SessionPayload = {
    product_name: "Premium Widget",
    base_price: 100.0,
    cost_price: 40.0,
    min_acceptable_price: 60.0,
    max_rounds: 10,
    strategy_mode: "MAX_PROFIT"
  };

  const res = await fetch(\`\${BASE_URL}/api/v1/chat-sessions\`, {
    method: "POST",
    headers,
    body: JSON.stringify(payload)
  });
  return res.json();
}

// ── Send a buyer offer ─────────────────────────────────
async function sendOffer(
  sessionId: number,
  offer: number
): Promise<any> {
  const payload: MessagePayload = {
    user_message: \`I'd like to buy this for $\${offer}\`,
    bot_reply: "",
    buyer_offer: offer,
    seller_counter: null,
    round_number: 1
  };

  const res = await fetch(
    \`\${BASE_URL}/api/v1/chat-sessions/\${sessionId}/messages\`,
    {
      method: "POST",
      headers,
      body: JSON.stringify(payload)
    }
  );
  return res.json();
}

(async () => {
  const session = await startSession();
  console.log("Session:", session);
  const reply = await sendOffer(session.id, 65);
  console.log("Reply:", reply);
})();`;
}

// ── Component ──────────────────────────────────────────────────────
export default function ApiAccess() {
    const [keys, setKeys] = useState([]);
    const [loading, setLoading] = useState(true);
    const [generating, setGenerating] = useState(false);
    const [label, setLabel] = useState('');
    const [error, setError] = useState('');
    const [copied, setCopied] = useState(null);       // key id that was copied
    const [selectedLang, setSelectedLang] = useState('Python');
    const [activeKey, setActiveKey] = useState(null);  // key to show in snippets
    const [revealedKeys, setRevealedKeys] = useState(new Set());
    const [deleteConfirm, setDeleteConfirm] = useState(null);

    useEffect(() => {
        loadKeys();
    }, []);

    async function loadKeys() {
        setLoading(true);
        try {
            const data = await fetchKeys();
            setKeys(data);
            if (data.length > 0 && !activeKey) setActiveKey(data[0].api_key_full);
        } catch {
            setError('Failed to load API keys. Are you logged in?');
        }
        setLoading(false);
    }

    async function handleGenerate() {
        setGenerating(true);
        setError('');
        try {
            const newKey = await generateKey(label || 'Default');
            setKeys(prev => [{ ...newKey, api_key_masked: newKey.api_key.slice(0, 3) + '•'.repeat(newKey.api_key.length - 11) + newKey.api_key.slice(-8), api_key_full: newKey.api_key, is_active: 1, created_at: new Date().toISOString() }, ...prev]);
            setActiveKey(newKey.api_key);
            setLabel('');
            // auto-reveal just-created key
            setRevealedKeys(prev => new Set(prev).add(newKey.id));
        } catch {
            setError('Failed to generate API key');
        }
        setGenerating(false);
    }

    async function handleRevoke(id) {
        try {
            await revokeKey(id);
            setKeys(prev => prev.filter(k => k.id !== id));
            setDeleteConfirm(null);
        } catch {
            setError('Failed to revoke key');
        }
    }

    function copyToClipboard(text, id) {
        navigator.clipboard.writeText(text);
        setCopied(id);
        setTimeout(() => setCopied(null), 2000);
    }

    function copySnippet() {
        navigator.clipboard.writeText(getSnippet(selectedLang, activeKey));
        setCopied('snippet');
        setTimeout(() => setCopied(null), 2000);
    }

    function toggleReveal(id) {
        setRevealedKeys(prev => {
            const next = new Set(prev);
            next.has(id) ? next.delete(id) : next.add(id);
            return next;
        });
    }

    return (
        <Layout>
            <section className="min-h-screen bg-neo-cream py-10 px-4">
                <div className="container mx-auto max-w-5xl">

                    {/* ── Header ─────────────────────────────────────── */}
                    <div className="mb-8">
                        <div className="flex items-center gap-3 mb-2">
                            <div className="w-12 h-12 bg-neo-navy flex items-center justify-center">
                                <Key className="w-6 h-6 text-neo-orange" />
                            </div>
                            <div>
                                <h1 className="font-heading text-3xl font-bold text-neo-navy tracking-tight">
                                    API <span className="text-neo-orange">ACCESS</span>
                                </h1>
                                <p className="text-neo-navy/50 text-sm font-bold uppercase tracking-wider">
                                    Generate keys · Integrate your negotiation engine
                                </p>
                            </div>
                        </div>
                    </div>

                    {error && (
                        <div className="mb-4 p-3 bg-neo-maroon/10 border-[2px] border-neo-maroon flex items-center gap-2 text-neo-maroon text-sm font-bold">
                            <AlertCircle className="w-4 h-4" /> {error}
                        </div>
                    )}

                    <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">

                        {/* ── Left: Key Management (3 cols) ──────────── */}
                        <div className="lg:col-span-3 space-y-4">

                            {/* Generate Card */}
                            <NeoCard className="p-5">
                                <p className="text-[10px] uppercase font-bold text-neo-navy/50 mb-3 flex items-center gap-1">
                                    <Zap className="w-3 h-3" /> Generate New Key
                                </p>
                                <div className="flex gap-2">
                                    <input
                                        type="text"
                                        placeholder="Label (e.g. Production, Testing…)"
                                        value={label}
                                        onChange={e => setLabel(e.target.value)}
                                        className="flex-1 px-3 py-2.5 border-[2px] border-neo-navy bg-white text-sm font-bold text-neo-navy placeholder:text-neo-navy/30 focus:outline-none focus:border-neo-orange"
                                    />
                                    <NeoButton
                                        variant="orange"
                                        onClick={handleGenerate}
                                        disabled={generating}
                                    >
                                        {generating ? (
                                            <Loader2 className="w-4 h-4 animate-spin" />
                                        ) : (
                                            <><Plus className="w-4 h-4 mr-1" /> Generate</>
                                        )}
                                    </NeoButton>
                                </div>
                            </NeoCard>

                            {/* Keys List */}
                            <NeoCard className="p-5">
                                <div className="flex items-center justify-between mb-3">
                                    <p className="text-[10px] uppercase font-bold text-neo-navy/50 flex items-center gap-1">
                                        <Shield className="w-3 h-3" /> Your API Keys
                                    </p>
                                    <button onClick={loadKeys} className="text-neo-navy/40 hover:text-neo-teal transition-colors">
                                        <RefreshCw className="w-4 h-4" />
                                    </button>
                                </div>

                                {loading ? (
                                    <div className="h-32 flex items-center justify-center">
                                        <Loader2 className="w-6 h-6 text-neo-teal animate-spin" />
                                    </div>
                                ) : keys.length === 0 ? (
                                    <div className="h-32 flex items-center justify-center border-[2px] border-dashed border-neo-navy/20">
                                        <div className="text-center text-neo-navy/30">
                                            <Key className="w-6 h-6 mx-auto mb-2 opacity-40" />
                                            <p className="text-xs font-bold">No API keys yet</p>
                                            <p className="text-[10px]">Generate one above to get started</p>
                                        </div>
                                    </div>
                                ) : (
                                    <div className="space-y-2">
                                        {keys.map(k => (
                                            <div
                                                key={k.id}
                                                className={`border-[2px] p-3 transition-all cursor-pointer ${
                                                    activeKey === k.api_key_full
                                                        ? 'border-neo-orange bg-neo-orange/5'
                                                        : 'border-neo-navy/20 hover:border-neo-navy/40'
                                                }`}
                                                onClick={() => setActiveKey(k.api_key_full)}
                                            >
                                                <div className="flex items-center justify-between gap-2">
                                                    <div className="flex-1 min-w-0">
                                                        <div className="flex items-center gap-2 mb-1">
                                                            <span className="font-heading font-bold text-sm text-neo-navy">{k.label}</span>
                                                            {k.is_active ? (
                                                                <span className="text-[8px] px-1.5 py-0.5 bg-neo-teal/20 text-neo-teal font-bold uppercase">Active</span>
                                                            ) : (
                                                                <span className="text-[8px] px-1.5 py-0.5 bg-neo-maroon/20 text-neo-maroon font-bold uppercase">Revoked</span>
                                                            )}
                                                        </div>
                                                        <div className="flex items-center gap-1.5">
                                                            <code className="text-xs text-neo-navy/60 font-mono truncate">
                                                                {revealedKeys.has(k.id) ? k.api_key_full : k.api_key_masked}
                                                            </code>
                                                            <button
                                                                onClick={e => { e.stopPropagation(); toggleReveal(k.id); }}
                                                                className="text-neo-navy/30 hover:text-neo-navy transition-colors"
                                                            >
                                                                {revealedKeys.has(k.id) ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                                                            </button>
                                                        </div>
                                                        <p className="text-[10px] text-neo-navy/40 mt-1">
                                                            Created {k.created_at ? new Date(k.created_at).toLocaleDateString() : '—'}
                                                        </p>
                                                    </div>
                                                    <div className="flex items-center gap-1.5">
                                                        <button
                                                            onClick={e => { e.stopPropagation(); copyToClipboard(k.api_key_full, k.id); }}
                                                            className="w-8 h-8 flex items-center justify-center border-[2px] border-neo-navy/20 hover:border-neo-teal hover:text-neo-teal transition-colors"
                                                        >
                                                            {copied === k.id ? <Check className="w-3.5 h-3.5 text-neo-teal" /> : <Copy className="w-3.5 h-3.5" />}
                                                        </button>
                                                        {deleteConfirm === k.id ? (
                                                            <div className="flex items-center gap-1">
                                                                <button
                                                                    onClick={e => { e.stopPropagation(); handleRevoke(k.id); }}
                                                                    className="text-[10px] font-bold text-neo-cream bg-neo-maroon px-2 py-1 border-[2px] border-neo-maroon hover:bg-neo-maroon/80 transition-colors"
                                                                >
                                                                    Yes
                                                                </button>
                                                                <button
                                                                    onClick={e => { e.stopPropagation(); setDeleteConfirm(null); }}
                                                                    className="text-[10px] font-bold px-2 py-1 border-[2px] border-neo-navy/20"
                                                                >
                                                                    No
                                                                </button>
                                                            </div>
                                                        ) : (
                                                            <button
                                                                onClick={e => { e.stopPropagation(); setDeleteConfirm(k.id); }}
                                                                className="w-8 h-8 flex items-center justify-center border-[2px] border-neo-navy/20 text-neo-navy/30 hover:border-neo-maroon hover:text-neo-maroon transition-colors"
                                                            >
                                                                <Trash2 className="w-3.5 h-3.5" />
                                                            </button>
                                                        )}
                                                    </div>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </NeoCard>
                        </div>

                        {/* ── Right: Code Snippets (2 cols) ─────────── */}
                        <div className="lg:col-span-2">
                            <NeoCard className="p-0 overflow-hidden sticky top-4">
                                {/* Tab bar */}
                                <div className="bg-neo-navy flex items-center">
                                    <div className="flex items-center gap-1 px-3 py-2">
                                        <Code2 className="w-4 h-4 text-neo-orange" />
                                        <span className="text-[10px] text-neo-cream/50 uppercase font-bold tracking-wider">Quick Start</span>
                                    </div>
                                    <div className="flex-1" />
                                    {LANGS.map(lang => (
                                        <button
                                            key={lang}
                                            onClick={() => setSelectedLang(lang)}
                                            className={`px-3 py-2.5 text-xs font-bold uppercase tracking-wide transition-colors ${
                                                selectedLang === lang
                                                    ? 'bg-neo-orange text-neo-navy'
                                                    : 'text-neo-cream/50 hover:text-neo-cream'
                                            }`}
                                        >
                                            {lang}
                                        </button>
                                    ))}
                                </div>

                                {/* Code block */}
                                <div className="relative">
                                    <button
                                        onClick={copySnippet}
                                        className="absolute top-2 right-2 z-10 px-2 py-1 bg-neo-navy/80 hover:bg-neo-navy text-neo-cream text-[10px] font-bold uppercase flex items-center gap-1 transition-colors"
                                    >
                                        {copied === 'snippet' ? <><Check className="w-3 h-3" /> Copied</> : <><Copy className="w-3 h-3" /> Copy</>}
                                    </button>
                                    <pre className="p-4 bg-[#0a1628] text-neo-cream/80 text-[11px] leading-relaxed overflow-x-auto max-h-[65vh] font-mono">
                                        <code>{getSnippet(selectedLang, activeKey)}</code>
                                    </pre>
                                </div>

                                {/* Endpoint reference */}
                                <div className="p-3 bg-neo-navy/5 border-t-[2px] border-neo-navy/10">
                                    <p className="text-[10px] uppercase font-bold text-neo-navy/50 mb-2">Available Endpoints</p>
                                    <div className="space-y-1.5">
                                        {[
                                            { method: 'POST', path: '/api/v1/chat-sessions', desc: 'Create session' },
                                            { method: 'GET', path: '/api/v1/chat-sessions', desc: 'List sessions' },
                                            { method: 'GET', path: '/api/v1/chat-sessions/:id', desc: 'Get session + messages' },
                                            { method: 'POST', path: '/api/v1/chat-sessions/:id/messages', desc: 'Send offer' },
                                            { method: 'PUT', path: '/api/v1/chat-sessions/:id/close', desc: 'Close session' },
                                            { method: 'GET', path: '/api/v1/products', desc: 'List products' },
                                            { method: 'GET', path: '/api/v1/products/:id/stats', desc: 'Product stats' },
                                        ].map((ep, i) => (
                                            <div key={i} className="flex items-center gap-2 text-[11px]">
                                                <span className={`font-mono font-bold px-1.5 py-0.5 text-[9px] ${
                                                    ep.method === 'GET' ? 'bg-neo-teal/20 text-neo-teal' :
                                                    ep.method === 'POST' ? 'bg-neo-orange/20 text-neo-orange' :
                                                    'bg-neo-navy/10 text-neo-navy'
                                                }`}>{ep.method}</span>
                                                <code className="text-neo-navy/70 font-mono text-[10px]">{ep.path}</code>
                                                <span className="text-neo-navy/40 text-[10px] ml-auto">{ep.desc}</span>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            </NeoCard>
                        </div>

                    </div>
                </div>
            </section>
        </Layout>
    );
}
