const API_BASE = 'http://127.0.0.1:8001/api/v1/negotiate';
const CHAT_DB_BASE = 'http://127.0.0.1:8001/api/v1/chat-sessions';

function _token() {
    return localStorage.getItem('trademind_token');
}

function _authHeaders() {
    const h = { 'Content-Type': 'application/json' };
    const t = _token();
    if (t) h['Authorization'] = `Bearer ${t}`;
    return h;
}

// ── Chat DB persistence helpers ──────────────────────────────────

/** Create a chat session in MySQL (returns { id, status }) */
export async function dbStartSession({ product_name, mode, base_price, cost_price, min_price, max_rounds }) {
    if (!_token()) return null;
    try {
        const res = await fetch(CHAT_DB_BASE, {
            method: 'POST',
            headers: _authHeaders(),
            body: JSON.stringify({ product_name, mode, base_price, cost_price, min_price, max_rounds }),
        });
        if (!res.ok) return null;
        return await res.json();
    } catch { return null; }
}

/** Save a chat round to MySQL */
export async function dbSaveMessage(dbSessionId, { round_number, user_message, bot_reply, offered_price, counter_price, decision }) {
    if (!_token() || !dbSessionId) return null;
    try {
        const res = await fetch(`${CHAT_DB_BASE}/${dbSessionId}/messages`, {
            method: 'POST',
            headers: _authHeaders(),
            body: JSON.stringify({ round_number, user_message, bot_reply, offered_price, counter_price, decision }),
        });
        if (!res.ok) return null;
        return await res.json();
    } catch { return null; }
}

/** Close a chat session in MySQL with final outcome */
export async function dbCloseSession(dbSessionId, { status, final_price, final_decision, deal_closed, buyer_last_offer, seller_last_offer, rounds_used }) {
    if (!_token() || !dbSessionId) return null;
    try {
        const res = await fetch(`${CHAT_DB_BASE}/${dbSessionId}/close`, {
            method: 'PUT',
            headers: _authHeaders(),
            body: JSON.stringify({ status, final_price, final_decision, deal_closed, buyer_last_offer, seller_last_offer, rounds_used }),
        });
        if (!res.ok) return null;
        return await res.json();
    } catch { return null; }
}

/** Save a callback request (phone number for scheduling a call) */
export async function dbSaveCallbackRequest({ session_id, phone_number, product_name, negotiation_status, final_price }) {
    if (!_token()) return null;
    try {
        const res = await fetch(`${CHAT_DB_BASE}/callback-request`, {
            method: 'POST',
            headers: _authHeaders(),
            body: JSON.stringify({ session_id, phone_number, product_name, negotiation_status, final_price }),
        });
        if (!res.ok) return null;
        return await res.json();
    } catch { return null; }
}

/** Get all chat sessions for current user */
export async function dbGetSessions() {
    if (!_token()) return [];
    try {
        const res = await fetch(CHAT_DB_BASE, { headers: _authHeaders() });
        if (!res.ok) return [];
        return await res.json();
    } catch { return []; }
}

/** Get a single session with messages */
export async function dbGetSession(dbSessionId) {
    if (!_token() || !dbSessionId) return null;
    try {
        const res = await fetch(`${CHAT_DB_BASE}/${dbSessionId}`, { headers: _authHeaders() });
        if (!res.ok) return null;
        return await res.json();
    } catch { return null; }
}

// Default product config for demo/testing
const DEFAULT_SESSION_CONFIG = {
    product: {
        product_id: "DEMO-001",
        product_name: "Premium Widget",
        base_price: 100.00,
        cost_price: 40.00,
        min_acceptable_price: 50.00,
        max_loss_percentage: 0
    },
    inventory: {
        available_quantity: 100,
        requested_quantity: 10,
        inventory_pressure: "medium",
        sales_frequency: "medium"
    },
    strategy: {
        mode: "MAX_PROFIT",
        urgency: "medium",
        relationship_priority: "medium",
        max_rounds: 10
    }
};

// Create a new negotiation session
export async function createSession(config = null) {
    try {
        const body = config || DEFAULT_SESSION_CONFIG;
        const response = await fetch(`${API_BASE}/sessions`, {
            method: 'POST',
            headers: _authHeaders(),
            body: JSON.stringify(body)
        });

        if (!response.ok) {
            const errorData = await response.text();
            throw new Error(`HTTP ${response.status}: ${errorData}`);
        }

        return await response.json();
    } catch (error) {
        console.error('Failed to create session:', error);
        throw error;
    }
}

// Submit a buyer offer (negotiation turn)
export async function submitOffer(sessionId, offeredPrice, message = null, offeredQuantity = null) {
    try {
        const body = {
            offered_price: offeredPrice,
        };
        if (message) body.message = message;
        if (offeredQuantity) body.offered_quantity = offeredQuantity;

        const response = await fetch(`${API_BASE}/sessions/${sessionId}/turns`, {
            method: 'POST',
            headers: _authHeaders(),
            body: JSON.stringify(body)
        });

        if (!response.ok) {
            const errorData = await response.text();
            throw new Error(`HTTP ${response.status}: ${errorData}`);
        }

        return await response.json();
    } catch (error) {
        console.error('Failed to submit offer:', error);
        throw error;
    }
}

// Send a free-text chat message (AI understands intent)
export async function sendChat(sessionId, message) {
    try {
        const body = { message };

        const response = await fetch(`${API_BASE}/sessions/${sessionId}/chat`, {
            method: 'POST',
            headers: _authHeaders(),
            body: JSON.stringify(body)
        });

        if (!response.ok) {
            const errorData = await response.text();
            throw new Error(`HTTP ${response.status}: ${errorData}`);
        }

        return await response.json();
    } catch (error) {
        console.error('Failed to send chat:', error);
        throw error;
    }
}

// Get session summary
export async function getSession(sessionId) {
    try {
        const response = await fetch(`${API_BASE}/sessions/${sessionId}`, {
            method: 'GET',
            headers: _authHeaders()
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        return await response.json();
    } catch (error) {
        console.error('Failed to get session:', error);
        throw error;
    }
}

// Get session analytics
export async function getAnalytics(sessionId) {
    try {
        const response = await fetch(`${API_BASE}/sessions/${sessionId}/analytics`, {
            method: 'GET',
            headers: _authHeaders()
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        return await response.json();
    } catch (error) {
        console.error('Failed to get analytics:', error);
        throw error;
    }
}

// Health check
export async function healthCheck() {
    try {
        const response = await fetch(`${API_BASE}/health`, {
            method: 'GET'
        });
        return response.ok;
    } catch (error) {
        console.error('Health check failed:', error);
        return false;
    }
}

// Helper: extract a numeric price from user text
export function extractPrice(text) {
    const match = text.match(/\$?\s?(\d+(?:\.\d{1,2})?)/);
    return match ? parseFloat(match[1]) : null;
}
