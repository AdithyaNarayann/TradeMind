const API_BASE = 'http://127.0.0.1:8000/api/v1/negotiate';

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
            headers: {
                'Content-Type': 'application/json',
            },
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
            headers: {
                'Content-Type': 'application/json',
            },
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
            headers: {
                'Content-Type': 'application/json',
            },
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
            headers: {
                'Content-Type': 'application/json',
            }
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
