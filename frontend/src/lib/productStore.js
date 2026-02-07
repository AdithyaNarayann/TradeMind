/**
 * Product Catalog Store
 * 
 * DB-backed via REST API. Each user's products are stored in MySQL.
 * Falls back to localStorage for offline / unauthenticated usage.
 * 
 * Each product:
 *   { id, name, basePrice, costPrice, minAcceptablePrice, maxLossPercent,
 *     mode, maxRounds, category, status, createdAt, updatedAt,
 *     stats: { totalSessions, acceptedDeals, avgMargin, revenue } }
 */

const AUTH_API_URL = import.meta.env.VITE_AUTH_API_URL || 'http://localhost:8000';
const STORAGE_KEY = 'trademind_products';

// ── Auth helper ──────────────────────────────────────────────────────────

function _token() {
    return localStorage.getItem('trademind_token');
}

function _headers() {
    const h = { 'Content-Type': 'application/json' };
    const t = _token();
    if (t) h['Authorization'] = `Bearer ${t}`;
    return h;
}

/** If a 401 comes back the stored token is stale – clear it. */
function _handleUnauthorized() {
    localStorage.removeItem('trademind_token');
    localStorage.removeItem('trademind_user');
}

// ── LocalStorage fallback (when not logged in) ──────────────────────────

function _readLocal() {
    try { return JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]'); } catch { return []; }
}
function _writeLocal(products) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(products));
}
function _generateId() {
    return 'PROD-' + Date.now().toString(36).toUpperCase() + '-' + Math.random().toString(36).slice(2, 6).toUpperCase();
}

// ── API-to-frontend shape converter ─────────────────────────────────────

function _apiToLocal(p) {
    return {
        id: p.id,
        name: p.name,
        basePrice: p.base_price,
        costPrice: p.cost_price,
        minAcceptablePrice: p.min_acceptable_price,
        maxLossPercent: p.max_loss_percent,
        mode: p.mode,
        maxRounds: p.max_rounds,
        category: p.category,
        status: p.status,
        createdAt: p.created_at,
        updatedAt: p.updated_at,
        stats: p.stats || { totalSessions: 0, acceptedDeals: 0, avgMargin: 0, revenue: 0 },
    };
}

// ── CRUD ─────────────────────────────────────────────────────────────────

/** Get all products */
export async function getProducts() {
    if (!_token()) return _readLocal();
    try {
        const res = await fetch(`${AUTH_API_URL}/api/v1/products`, { headers: _headers() });
        if (res.status === 401) { _handleUnauthorized(); return _readLocal(); }
        if (!res.ok) return _readLocal();
        const data = await res.json();
        return data.map(_apiToLocal);
    } catch {
        return _readLocal();
    }
}

/** Get a single product by ID */
export async function getProduct(id) {
    const products = await getProducts();
    return products.find(p => p.id === id) || null;
}

/** Create a new product. Returns the created product. */
export async function createProduct({ name, basePrice, costPrice, minAcceptablePrice, maxLossPercent = 0, mode = 'MAX_PROFIT', maxRounds = 10, category = 'General' }) {
    if (!_token()) throw new Error('Please log in to add products');

    const res = await fetch(`${AUTH_API_URL}/api/v1/products`, {
        method: 'POST',
        headers: _headers(),
        body: JSON.stringify({
            name, base_price: Number(basePrice), cost_price: Number(costPrice),
            min_acceptable_price: Number(minAcceptablePrice || costPrice),
            max_loss_percent: Number(maxLossPercent), mode,
            max_rounds: Number(maxRounds), category,
        }),
    });
    if (res.status === 401) {
        _handleUnauthorized();
        throw new Error('Session expired — please log in again');
    }
    if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'Failed to create product');
    }
    return _apiToLocal(await res.json());
}

/** Update a product. Returns the updated product or null. */
export async function updateProduct(id, updates) {
    if (!_token()) throw new Error('Please log in to update products');

    const body = {};
    if (updates.name !== undefined) body.name = updates.name;
    if (updates.basePrice !== undefined) body.base_price = Number(updates.basePrice);
    if (updates.costPrice !== undefined) body.cost_price = Number(updates.costPrice);
    if (updates.minAcceptablePrice !== undefined) body.min_acceptable_price = Number(updates.minAcceptablePrice);
    if (updates.maxLossPercent !== undefined) body.max_loss_percent = Number(updates.maxLossPercent);
    if (updates.mode !== undefined) body.mode = updates.mode;
    if (updates.maxRounds !== undefined) body.max_rounds = Number(updates.maxRounds);
    if (updates.category !== undefined) body.category = updates.category;
    if (updates.status !== undefined) body.status = updates.status;

    const res = await fetch(`${AUTH_API_URL}/api/v1/products/${id}`, {
        method: 'PUT',
        headers: _headers(),
        body: JSON.stringify(body),
    });
    if (res.status === 401) {
        _handleUnauthorized();
        throw new Error('Session expired — please log in again');
    }
    if (!res.ok) return null;
    return _apiToLocal(await res.json());
}

/** Delete a product. Returns true if deleted. */
export async function deleteProduct(id) {
    if (!_token()) throw new Error('Please log in to delete products');

    const res = await fetch(`${AUTH_API_URL}/api/v1/products/${id}`, {
        method: 'DELETE',
        headers: _headers(),
    });
    if (res.status === 401) {
        _handleUnauthorized();
        throw new Error('Session expired — please log in again');
    }
    return res.ok || res.status === 204;
}

/** Record a completed negotiation against a product */
export async function recordNegotiation(productId, { accepted, margin, revenue }) {
    // For now keep stats in localStorage — backend can be extended later
    const products = _readLocal();
    const idx = products.findIndex(p => p.id === productId);
    if (idx === -1) return;
    const s = products[idx].stats;
    s.totalSessions += 1;
    if (accepted) {
        s.acceptedDeals += 1;
        s.revenue += Number(revenue) || 0;
    }
    // Running average margin
    if (s.totalSessions > 0) {
        s.avgMargin = ((s.avgMargin * (s.totalSessions - 1)) + (Number(margin) || 0)) / s.totalSessions;
    }
    products[idx].stats = s;
    _writeLocal(products);
}

// ── Bulk CSV Import ──────────────────────────────────────────────────────

/**
 * Parse a CSV string and create products.
 * Expected columns: name, basePrice, costPrice, category (optional)
 * Returns { created: number, errors: string[] }
 */
export async function importFromCSV(csvText) {
    if (!_token()) return { created: 0, errors: ['Please log in to import products'] };

    try {
        const res = await fetch(`${AUTH_API_URL}/api/v1/products/import`, {
            method: 'POST',
            headers: _headers(),
            body: JSON.stringify({ csv_text: csvText }),
        });
        if (res.status === 401) {
            _handleUnauthorized();
            return { created: 0, errors: ['Session expired — please log in again'] };
        }
        if (!res.ok) throw new Error('Import failed');
        return await res.json();
    } catch (e) {
        return { created: 0, errors: [e.message] };
    }
}

// ── Aggregate Analytics ──────────────────────────────────────────────────

/** Get summary analytics across all products */
export async function getAggregateAnalytics() {
    const products = await getProducts();
    const totalProducts = products.length;
    const activeProducts = products.filter(p => p.status === 'active').length;
    let totalSessions = 0;
    let totalAccepted = 0;
    let totalRevenue = 0;
    let marginSum = 0;
    let marginCount = 0;

    for (const p of products) {
        totalSessions += p.stats.totalSessions;
        totalAccepted += p.stats.acceptedDeals;
        totalRevenue += p.stats.revenue;
        if (p.stats.totalSessions > 0) {
            marginSum += p.stats.avgMargin;
            marginCount++;
        }
    }

    return {
        totalProducts,
        activeProducts,
        totalSessions,
        totalAccepted,
        acceptRate: totalSessions > 0 ? Math.round((totalAccepted / totalSessions) * 100) : 0,
        totalRevenue: totalRevenue.toFixed(2),
        avgMargin: marginCount > 0 ? (marginSum / marginCount).toFixed(1) : '0.0',
        products, // for per-product breakdowns
    };
}

/** Fetch live stats for a specific product from chat_sessions data */
export async function getProductStats(productId) {
    if (!_token()) return null;
    try {
        const res = await fetch(`${AUTH_API_URL}/api/v1/products/${productId}/stats`, {
            headers: _headers(),
        });
        if (res.status === 401) { _handleUnauthorized(); return null; }
        if (!res.ok) return null;
        return await res.json();
    } catch {
        return null;
    }
}
