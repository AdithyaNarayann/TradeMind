/**
 * Product Catalog Store
 * 
 * Uses localStorage for now. Designed so that swapping to a DB-backed API
 * requires only changing the implementation of these functions — the
 * component interface stays the same.
 * 
 * Each product:
 *   { id, name, basePrice, costPrice, minAcceptablePrice, maxLossPercent,
 *     mode, maxRounds, category, status, createdAt, updatedAt,
 *     stats: { totalSessions, acceptedDeals, avgMargin, revenue } }
 */

const STORAGE_KEY = 'trademind_products';

// ── Helpers ──────────────────────────────────────────────────────────────

function _read() {
    try {
        const raw = localStorage.getItem(STORAGE_KEY);
        return raw ? JSON.parse(raw) : [];
    } catch {
        return [];
    }
}

function _write(products) {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(products));
}

function _generateId() {
    return 'PROD-' + Date.now().toString(36).toUpperCase() + '-' + Math.random().toString(36).slice(2, 6).toUpperCase();
}

// ── CRUD ─────────────────────────────────────────────────────────────────

/** Get all products */
export function getProducts() {
    return _read();
}

/** Get a single product by ID */
export function getProduct(id) {
    return _read().find(p => p.id === id) || null;
}

/** Create a new product. Returns the created product. */
export function createProduct({ name, basePrice, costPrice, minAcceptablePrice, maxLossPercent = 0, mode = 'MAX_PROFIT', maxRounds = 10, category = 'General' }) {
    const products = _read();
    const now = new Date().toISOString();
    const product = {
        id: _generateId(),
        name,
        basePrice: Number(basePrice),
        costPrice: Number(costPrice),
        minAcceptablePrice: Number(minAcceptablePrice || costPrice),
        maxLossPercent: Number(maxLossPercent),
        mode,
        maxRounds: Number(maxRounds),
        category,
        status: 'active',
        createdAt: now,
        updatedAt: now,
        stats: { totalSessions: 0, acceptedDeals: 0, avgMargin: 0, revenue: 0 },
    };
    products.push(product);
    _write(products);
    return product;
}

/** Update a product. Returns the updated product or null. */
export function updateProduct(id, updates) {
    const products = _read();
    const idx = products.findIndex(p => p.id === id);
    if (idx === -1) return null;
    products[idx] = { ...products[idx], ...updates, updatedAt: new Date().toISOString() };
    _write(products);
    return products[idx];
}

/** Delete a product. Returns true if deleted. */
export function deleteProduct(id) {
    const products = _read();
    const filtered = products.filter(p => p.id !== id);
    if (filtered.length === products.length) return false;
    _write(filtered);
    return true;
}

/** Record a completed negotiation against a product */
export function recordNegotiation(productId, { accepted, margin, revenue }) {
    const products = _read();
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
    _write(products);
}

// ── Bulk CSV Import ──────────────────────────────────────────────────────

/**
 * Parse a CSV string and create products.
 * Expected columns: name, basePrice, costPrice, category (optional)
 * Returns { created: number, errors: string[] }
 */
export function importFromCSV(csvText) {
    const lines = csvText.trim().split('\n');
    if (lines.length < 2) return { created: 0, errors: ['CSV must have a header row and at least one data row.'] };

    const header = lines[0].split(',').map(h => h.trim().toLowerCase());
    const nameIdx = header.indexOf('name');
    const baseIdx = header.findIndex(h => h === 'baseprice' || h === 'base_price' || h === 'base price');
    const costIdx = header.findIndex(h => h === 'costprice' || h === 'cost_price' || h === 'cost price');
    const catIdx = header.findIndex(h => h === 'category');

    if (nameIdx === -1 || baseIdx === -1 || costIdx === -1) {
        return { created: 0, errors: ['CSV must contain columns: name, basePrice, costPrice'] };
    }

    let created = 0;
    const errors = [];

    for (let i = 1; i < lines.length; i++) {
        const cols = lines[i].split(',').map(c => c.trim());
        const name = cols[nameIdx];
        const basePrice = parseFloat(cols[baseIdx]);
        const costPrice = parseFloat(cols[costIdx]);
        const category = catIdx !== -1 ? cols[catIdx] : 'General';

        if (!name) { errors.push(`Row ${i + 1}: missing name`); continue; }
        if (isNaN(basePrice) || basePrice <= 0) { errors.push(`Row ${i + 1}: invalid base price`); continue; }
        if (isNaN(costPrice) || costPrice <= 0) { errors.push(`Row ${i + 1}: invalid cost price`); continue; }
        if (costPrice >= basePrice) { errors.push(`Row ${i + 1}: cost price must be less than base price`); continue; }

        createProduct({ name, basePrice, costPrice, category });
        created++;
    }

    return { created, errors };
}

// ── Aggregate Analytics ──────────────────────────────────────────────────

/** Get summary analytics across all products */
export function getAggregateAnalytics() {
    const products = _read();
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
