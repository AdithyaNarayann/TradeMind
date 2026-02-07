import { useState, useEffect, useRef } from 'react';
import {
    Package, Plus, Pencil, Trash2, Upload, X, Search,
    DollarSign, TrendingUp, TrendingDown, Settings, AlertCircle, Check,
    BarChart3, Loader2, ArrowRight, ChevronDown, ChevronUp,
    IndianRupee, Target, Zap, ShoppingCart, Percent, Activity,
    PieChart, Award
} from 'lucide-react';
import Layout from '../components/Layout';
import NeoCard from '../components/NeoCard';
import NeoButton from '../components/NeoButton';
import {
    getProducts, createProduct, updateProduct, deleteProduct, importFromCSV
} from '../lib/productStore';

export default function ProductCatalog() {
    const fileInputRef = useRef(null);

    const [products, setProducts] = useState([]);
    const [searchQuery, setSearchQuery] = useState('');
    const [showForm, setShowForm] = useState(false);
    const [editingProduct, setEditingProduct] = useState(null);
    const [importResult, setImportResult] = useState(null);
    const [deleteConfirm, setDeleteConfirm] = useState(null);
    const [analyticsOpen, setAnalyticsOpen] = useState(null); // product id or null

    // Form state
    const [form, setForm] = useState({
        name: '', basePrice: '', costPrice: '', minAcceptablePrice: '',
        maxLossPercent: '0', mode: 'MAX_PROFIT', maxRounds: '10', category: 'General',
    });
    const [formError, setFormError] = useState('');

    useEffect(() => { reload(); }, []);

    async function reload() {
        setProducts(await getProducts());
    }

    // ── Form helpers ───────────────────────────────────────────────────────

    function openCreate() {
        setEditingProduct(null);
        setForm({ name: '', basePrice: '', costPrice: '', minAcceptablePrice: '', maxLossPercent: '0', mode: 'MAX_PROFIT', maxRounds: '10', category: 'General' });
        setFormError('');
        setShowForm(true);
    }

    function openEdit(product) {
        setEditingProduct(product);
        setForm({
            name: product.name,
            basePrice: String(product.basePrice),
            costPrice: String(product.costPrice),
            minAcceptablePrice: String(product.minAcceptablePrice),
            maxLossPercent: String(product.maxLossPercent),
            mode: product.mode,
            maxRounds: String(product.maxRounds),
            category: product.category,
        });
        setFormError('');
        setShowForm(true);
    }

    async function handleSubmit(e) {
        e.preventDefault();
        const base = parseFloat(form.basePrice);
        const cost = parseFloat(form.costPrice);
        const min = parseFloat(form.minAcceptablePrice || form.costPrice);

        if (!form.name.trim()) { setFormError('Product name is required'); return; }
        if (isNaN(base) || base <= 0) { setFormError('Invalid base price'); return; }
        if (isNaN(cost) || cost <= 0) { setFormError('Invalid cost price'); return; }
        if (cost >= base) { setFormError('Cost price must be less than base price'); return; }

        try {
            if (editingProduct) {
                await updateProduct(editingProduct.id, {
                    name: form.name.trim(), basePrice: base, costPrice: cost,
                    minAcceptablePrice: min, maxLossPercent: Number(form.maxLossPercent),
                    mode: form.mode, maxRounds: Number(form.maxRounds), category: form.category,
                });
            } else {
                await createProduct({
                    name: form.name.trim(), basePrice: base, costPrice: cost,
                    minAcceptablePrice: min, maxLossPercent: Number(form.maxLossPercent),
                    mode: form.mode, maxRounds: Number(form.maxRounds), category: form.category,
                });
            }
            setShowForm(false);
            reload();
        } catch (err) {
            setFormError(err.message || 'Failed to save product');
        }
    }

    async function handleDelete(id) {
        try {
            await deleteProduct(id);
            setDeleteConfirm(null);
            reload();
        } catch (err) {
            console.error('Delete failed:', err);
            setDeleteConfirm(null);
            reload();
        }
    }

    // ── CSV Import ─────────────────────────────────────────────────────────

    function handleCSVUpload(e) {
        const file = e.target.files?.[0];
        if (!file) return;
        const reader = new FileReader();
        reader.onload = async (ev) => {
            const result = await importFromCSV(ev.target.result);
            setImportResult(result);
            reload();
            setTimeout(() => setImportResult(null), 6000);
        };
        reader.readAsText(file);
        e.target.value = '';
    }

    // ── Filter ─────────────────────────────────────────────────────────────

    const filteredProducts = products.filter(p =>
        p.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        p.category.toLowerCase().includes(searchQuery.toLowerCase()) ||
        String(p.id).toLowerCase().includes(searchQuery.toLowerCase())
    );

    // ── Render ─────────────────────────────────────────────────────────────

    return (
        <Layout>
            {/* Hero Header — same pattern as JuryDashboard */}
            <section className="bg-neo-navy py-6 sm:py-12 border-b-[4px] border-neo-navy">
                <div className="container mx-auto px-4">
                    <div className="max-w-4xl mx-auto">
                        <div className="flex flex-col gap-4">
                            <div>
                                <div className="neo-badge-orange mb-2 sm:mb-4 text-xs sm:text-sm">
                                    <Package className="w-3 h-3 sm:w-4 sm:h-4" />
                                    PRODUCT CATALOG
                                </div>
                                <h1 className="text-2xl sm:text-4xl md:text-5xl font-heading font-bold text-neo-cream mb-1 sm:mb-2">
                                    Your Products
                                </h1>
                                <p className="text-sm sm:text-base text-neo-cream/60">
                                    Manage products, pricing rules, and start negotiations directly.
                                </p>
                            </div>
                        </div>
                    </div>
                </div>
            </section>

            {/* Stats Bar */}
            <section className="bg-neo-teal border-b-[4px] border-neo-navy">
                <div className="container mx-auto px-4">
                    <div className="max-w-4xl mx-auto grid grid-cols-2 md:grid-cols-4">
                        <div className="py-3 sm:py-6 text-center border-r-[2px] border-b-[2px] md:border-b-0 border-neo-navy">
                            <p className="text-2xl sm:text-4xl font-heading font-bold text-neo-cream">{products.length}</p>
                            <p className="text-xs sm:text-sm text-neo-cream/70">Products</p>
                        </div>
                        <div className="py-3 sm:py-6 text-center border-b-[2px] md:border-b-0 md:border-r-[2px] border-neo-navy">
                            <p className="text-2xl sm:text-4xl font-heading font-bold text-neo-orange">
                                {products.filter(p => p.status === 'active').length}
                            </p>
                            <p className="text-xs sm:text-sm text-neo-cream/70">Active</p>
                        </div>
                        <div className="py-3 sm:py-6 text-center border-r-[2px] border-neo-navy">
                            <p className="text-2xl sm:text-4xl font-heading font-bold text-neo-cream">
                                {products.reduce((sum, p) => sum + p.stats.totalSessions, 0)}
                            </p>
                            <p className="text-xs sm:text-sm text-neo-cream/70">Negotiations</p>
                        </div>
                        <div className="py-3 sm:py-6 text-center">
                            <p className="text-2xl sm:text-4xl font-heading font-bold text-neo-orange">
                                {products.reduce((sum, p) => sum + p.stats.acceptedDeals, 0)}
                            </p>
                            <p className="text-xs sm:text-sm text-neo-cream/70">Deals Closed</p>
                        </div>
                    </div>
                </div>
            </section>

            {/* Import Result Banner */}
            {importResult && (
                <section className="bg-neo-cream border-b-[4px] border-neo-navy">
                    <div className="container mx-auto px-4">
                        <div className="max-w-4xl mx-auto py-3 flex items-center gap-3">
                            <Check className="w-5 h-5 text-neo-teal flex-shrink-0" />
                            <p className="text-sm font-bold text-neo-navy">
                                Imported {importResult.created} product{importResult.created !== 1 ? 's' : ''}.
                                {importResult.errors.length > 0 && (
                                    <span className="text-neo-maroon ml-2">{importResult.errors.length} error(s): {importResult.errors[0]}</span>
                                )}
                            </p>
                            <button onClick={() => setImportResult(null)} className="ml-auto">
                                <X className="w-4 h-4 text-neo-navy/60" />
                            </button>
                        </div>
                    </div>
                </section>
            )}

            {/* Main Content */}
            <section className="py-8 sm:py-12 bg-neo-cream">
                <div className="container mx-auto px-4">
                    <div className="max-w-4xl mx-auto">

                        {/* Actions Row */}
                        <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3 mb-6">
                            <div className="flex-1 relative w-full sm:w-auto">
                                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-neo-navy/40" />
                                <input
                                    type="text"
                                    placeholder="Search products..."
                                    value={searchQuery}
                                    onChange={(e) => setSearchQuery(e.target.value)}
                                    className="neo-input pl-10 text-sm"
                                />
                            </div>
                            <div className="flex gap-2">
                                <NeoButton variant="orange" size="sm" onClick={openCreate}>
                                    <Plus className="w-4 h-4 mr-1" /> Add Product
                                </NeoButton>
                                <NeoButton variant="default" size="sm" onClick={() => fileInputRef.current?.click()}>
                                    <Upload className="w-4 h-4 mr-1" /> CSV Import
                                </NeoButton>
                                <input ref={fileInputRef} type="file" accept=".csv" className="hidden" onChange={handleCSVUpload} />
                            </div>
                        </div>

                        {/* ──── Add / Edit Form Modal ──── */}
                        {showForm && (
                            <NeoCard className="mb-6 overflow-hidden">
                                <div className="p-4 bg-neo-navy flex items-center justify-between">
                                    <div className="flex items-center gap-3">
                                        <div className="w-10 h-10 bg-neo-orange flex items-center justify-center">
                                            {editingProduct ? <Pencil className="w-5 h-5 text-neo-navy" /> : <Plus className="w-5 h-5 text-neo-navy" />}
                                        </div>
                                        <p className="font-heading font-bold text-neo-cream">
                                            {editingProduct ? 'Edit Product' : 'New Product'}
                                        </p>
                                    </div>
                                    <button onClick={() => setShowForm(false)} className="text-neo-cream/70 hover:text-neo-cream">
                                        <X className="w-5 h-5" />
                                    </button>
                                </div>

                                <form onSubmit={handleSubmit} className="p-4 space-y-4">
                                    {/* Row 1: Name + Category */}
                                    <div className="grid sm:grid-cols-2 gap-4">
                                        <div>
                                            <label className="text-xs font-bold text-neo-navy/60 mb-1 block uppercase tracking-widest">Product Name</label>
                                            <input type="text" value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} className="neo-input text-sm" placeholder="e.g. Premium Widget" />
                                        </div>
                                        <div>
                                            <label className="text-xs font-bold text-neo-navy/60 mb-1 block uppercase tracking-widest">Category</label>
                                            <input type="text" value={form.category} onChange={e => setForm({ ...form, category: e.target.value })} className="neo-input text-sm" placeholder="e.g. Electronics" />
                                        </div>
                                    </div>

                                    {/* Row 2: Prices */}
                                    <div className="grid sm:grid-cols-3 gap-4">
                                        <div>
                                            <label className="text-xs font-bold text-neo-navy/60 mb-1 block uppercase tracking-widest">Base Price ($)</label>
                                            <input type="number" step="0.01" min="0" value={form.basePrice} onChange={e => setForm({ ...form, basePrice: e.target.value })} className="neo-input text-sm" placeholder="100" />
                                        </div>
                                        <div>
                                            <label className="text-xs font-bold text-neo-navy/60 mb-1 block uppercase tracking-widest">Cost Price ($)</label>
                                            <input type="number" step="0.01" min="0" value={form.costPrice} onChange={e => setForm({ ...form, costPrice: e.target.value })} className="neo-input text-sm" placeholder="40" />
                                        </div>
                                        <div>
                                            <label className="text-xs font-bold text-neo-navy/60 mb-1 block uppercase tracking-widest">Min Accept ($)</label>
                                            <input type="number" step="0.01" min="0" value={form.minAcceptablePrice} onChange={e => setForm({ ...form, minAcceptablePrice: e.target.value })} className="neo-input text-sm" placeholder="Auto = cost" />
                                        </div>
                                    </div>

                                    {/* Row 3: Strategy */}
                                    <div className="grid sm:grid-cols-2 gap-4">
                                        <div>
                                            <label className="text-xs font-bold text-neo-navy/60 mb-1 block uppercase tracking-widest">Strategy Mode</label>
                                            <div className="grid grid-cols-2 gap-2">
                                                <button type="button" onClick={() => setForm({ ...form, mode: 'MAX_PROFIT' })}
                                                    className={`px-3 py-2 border-[3px] border-neo-navy font-bold text-xs transition-all ${form.mode === 'MAX_PROFIT' ? 'bg-neo-teal text-neo-cream shadow-neo' : 'bg-white text-neo-navy'}`}>
                                                    MAX PROFIT
                                                </button>
                                                <button type="button" onClick={() => setForm({ ...form, mode: 'MIN_LOSS' })}
                                                    className={`px-3 py-2 border-[3px] border-neo-navy font-bold text-xs transition-all ${form.mode === 'MIN_LOSS' ? 'bg-neo-teal text-neo-cream shadow-neo' : 'bg-white text-neo-navy'}`}>
                                                    MIN LOSS
                                                </button>
                                            </div>
                                        </div>
                                        <div>
                                            <label className="text-xs font-bold text-neo-navy/60 mb-1 block uppercase tracking-widest">Max Rounds</label>
                                            <input type="number" min="1" max="50" value={form.maxRounds} onChange={e => setForm({ ...form, maxRounds: e.target.value })} className="neo-input text-sm" />
                                        </div>
                                    </div>

                                    {formError && (
                                        <p className="text-neo-maroon text-sm font-bold flex items-center gap-1">
                                            <AlertCircle className="w-4 h-4" /> {formError}
                                        </p>
                                    )}

                                    <div className="flex gap-3 pt-2">
                                        <NeoButton variant="orange" size="sm" type="submit">
                                            <Check className="w-4 h-4 mr-1" /> {editingProduct ? 'Save Changes' : 'Create Product'}
                                        </NeoButton>
                                        <NeoButton variant="default" size="sm" type="button" onClick={() => setShowForm(false)}>
                                            Cancel
                                        </NeoButton>
                                    </div>
                                </form>
                            </NeoCard>
                        )}

                        {/* ──── Empty State ──── */}
                        {filteredProducts.length === 0 && !showForm && (
                            <NeoCard className="p-8 text-center">
                                <Package className="w-12 h-12 mx-auto text-neo-navy/40 mb-4" />
                                <h3 className="font-heading font-bold text-xl text-neo-navy mb-2">
                                    {products.length === 0 ? 'No Products Yet' : 'No Matching Products'}
                                </h3>
                                <p className="text-neo-navy/60 mb-4">
                                    {products.length === 0
                                        ? 'Add your first product to start using AI-powered negotiations.'
                                        : 'Try a different search term.'}
                                </p>
                                {products.length === 0 && (
                                    <NeoButton variant="orange" size="sm" onClick={openCreate}>
                                        <Plus className="w-4 h-4 mr-1" /> Add First Product
                                    </NeoButton>
                                )}
                            </NeoCard>
                        )}

                        {/* ──── Product Cards ──── */}
                        <div className="space-y-4">
                            {filteredProducts.map((product) => (
                                <NeoCard key={product.id} className="overflow-hidden">
                                    {/* Card Header */}
                                    <div className="p-4 border-b-[3px] border-neo-navy bg-neo-navy flex items-center justify-between">
                                        <div className="flex items-center gap-3">
                                            <div className="w-10 h-10 bg-neo-orange flex items-center justify-center">
                                                <Package className="w-5 h-5 text-neo-navy" />
                                            </div>
                                            <div>
                                                <p className="font-heading font-bold text-neo-cream">{product.name}</p>
                                                <p className="text-xs text-neo-cream/60">{product.id}</p>
                                            </div>
                                        </div>
                                        <div className="flex items-center gap-2">
                                            <span className="neo-badge bg-neo-orange text-neo-navy border-neo-cream text-xs">
                                                {product.category}
                                            </span>
                                            <span className={`neo-badge border-neo-cream text-xs ${product.mode === 'MAX_PROFIT' ? 'bg-neo-teal text-neo-cream' : 'bg-neo-maroon text-neo-cream'}`}>
                                                {product.mode === 'MAX_PROFIT' ? 'MAX PROFIT' : 'MIN LOSS'}
                                            </span>
                                        </div>
                                    </div>

                                    {/* Card Body */}
                                    <div className="p-4 grid sm:grid-cols-2 gap-4">
                                        {/* Pricing Info */}
                                        <div className="space-y-3">
                                            <p className="text-xs uppercase font-bold text-neo-navy/60">Pricing Rules</p>
                                            <div className="grid grid-cols-3 gap-2">
                                                <div className="text-center p-2 border-[2px] border-neo-navy">
                                                    <p className="text-lg font-heading font-bold text-neo-navy">${product.basePrice}</p>
                                                    <p className="text-[10px] uppercase text-neo-navy/60 font-bold">Base</p>
                                                </div>
                                                <div className="text-center p-2 border-[2px] border-neo-navy">
                                                    <p className="text-lg font-heading font-bold text-neo-teal">${product.costPrice}</p>
                                                    <p className="text-[10px] uppercase text-neo-navy/60 font-bold">Cost</p>
                                                </div>
                                                <div className="text-center p-2 border-[2px] border-neo-navy">
                                                    <p className="text-lg font-heading font-bold text-neo-orange">${product.minAcceptablePrice}</p>
                                                    <p className="text-[10px] uppercase text-neo-navy/60 font-bold">Min</p>
                                                </div>
                                            </div>
                                            <div className="flex items-center gap-2 text-sm text-neo-navy/60">
                                                <Settings className="w-3 h-3" />
                                                Max {product.maxRounds} rounds
                                            </div>
                                        </div>

                                        {/* Stats */}
                                        <div className="space-y-3">
                                            <p className="text-xs uppercase font-bold text-neo-navy/60">Performance</p>
                                            <div className="grid grid-cols-2 gap-2">
                                                <NeoCard variant="teal" className="p-2 text-center">
                                                    <p className="text-lg font-heading font-bold text-neo-cream">{product.stats.totalSessions}</p>
                                                    <p className="text-[10px] uppercase text-neo-cream/70 font-bold">Sessions</p>
                                                </NeoCard>
                                                <NeoCard variant="teal" className="p-2 text-center">
                                                    <p className="text-lg font-heading font-bold text-neo-orange">{product.stats.acceptedDeals}</p>
                                                    <p className="text-[10px] uppercase text-neo-cream/70 font-bold">Closed</p>
                                                </NeoCard>
                                            </div>
                                            <div className="flex items-center justify-between text-sm">
                                                <span className="text-neo-navy/60">Avg Margin</span>
                                                <span className="font-bold text-neo-teal">{product.stats.avgMargin.toFixed(1)}%</span>
                                            </div>
                                        </div>
                                    </div>

                                    {/* Card Footer — Actions */}
                                    <div className="p-4 border-t-[3px] border-neo-navy bg-neo-cream flex flex-wrap gap-2">
                                        <NeoButton variant="default" size="sm" onClick={() => openEdit(product)}>
                                            <Pencil className="w-4 h-4 mr-1" /> Edit
                                        </NeoButton>
                                        <NeoButton
                                            variant={analyticsOpen === product.id ? 'teal' : 'orange'}
                                            size="sm"
                                            onClick={() => setAnalyticsOpen(analyticsOpen === product.id ? null : product.id)}
                                        >
                                            <BarChart3 className="w-4 h-4 mr-1" />
                                            {analyticsOpen === product.id ? 'Hide' : 'Show'} Analytics
                                            {analyticsOpen === product.id
                                                ? <ChevronUp className="w-3 h-3 ml-1" />
                                                : <ChevronDown className="w-3 h-3 ml-1" />}
                                        </NeoButton>
                                        {deleteConfirm === product.id ? (
                                            <div className="flex items-center gap-2 ml-auto">
                                                <span className="text-xs text-neo-maroon font-bold">Delete?</span>
                                                <NeoButton variant="maroon" size="sm" onClick={() => handleDelete(product.id)}>Yes</NeoButton>
                                                <NeoButton variant="default" size="sm" onClick={() => setDeleteConfirm(null)}>No</NeoButton>
                                            </div>
                                        ) : (
                                            <button onClick={() => setDeleteConfirm(product.id)} className="ml-auto text-neo-navy/40 hover:text-neo-maroon transition-colors p-2">
                                                <Trash2 className="w-4 h-4" />
                                            </button>
                                        )}
                                    </div>

                                    {/* ──── Inline Analytics Panel ──── */}
                                    {analyticsOpen === product.id && (() => {
                                        const margin = product.basePrice > 0
                                            ? ((product.basePrice - product.costPrice) / product.basePrice * 100)
                                            : 0;
                                        const markup = product.costPrice > 0
                                            ? ((product.basePrice - product.costPrice) / product.costPrice * 100)
                                            : 0;
                                        const profitPerUnit = product.basePrice - product.costPrice;
                                        const acceptRate = product.stats.totalSessions > 0
                                            ? (product.stats.acceptedDeals / product.stats.totalSessions * 100)
                                            : 0;
                                        const priceRange = product.basePrice - product.costPrice;
                                        const minPos = priceRange > 0
                                            ? ((product.minAcceptablePrice - product.costPrice) / priceRange * 100)
                                            : 50;
                                        const maxLossAmt = product.basePrice * (product.maxLossPercent / 100);
                                        const negotiationBuffer = product.basePrice - product.minAcceptablePrice;
                                        const bufferPercent = product.basePrice > 0 ? (negotiationBuffer / product.basePrice * 100) : 0;

                                        return (
                                            <div className="border-t-[3px] border-neo-navy bg-gradient-to-b from-neo-cream to-white">
                                                {/* Analytics Header */}
                                                <div className="px-4 pt-4 pb-2 flex items-center gap-2">
                                                    <div className="w-7 h-7 bg-neo-orange flex items-center justify-center">
                                                        <PieChart className="w-4 h-4 text-neo-navy" />
                                                    </div>
                                                    <p className="font-heading font-bold text-neo-navy text-sm">Product Analytics</p>
                                                    <span className="text-[10px] text-neo-navy/40 ml-auto uppercase font-bold tracking-wider">Live Data</span>
                                                </div>

                                                {/* ── Row 1: Key Metrics ── */}
                                                <div className="px-4 pb-3">
                                                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                                                        <div className="bg-neo-navy p-3 text-center">
                                                            <p className="text-neo-cream/50 text-[8px] uppercase font-bold tracking-wider">Profit / Unit</p>
                                                            <p className={`text-xl font-heading font-bold ${profitPerUnit >= 0 ? 'text-neo-teal' : 'text-neo-maroon'}`}>
                                                                ₹{profitPerUnit.toFixed(0)}
                                                            </p>
                                                        </div>
                                                        <div className="bg-neo-navy p-3 text-center">
                                                            <p className="text-neo-cream/50 text-[8px] uppercase font-bold tracking-wider">Margin</p>
                                                            <p className={`text-xl font-heading font-bold ${margin >= 20 ? 'text-neo-teal' : margin >= 10 ? 'text-neo-orange' : 'text-neo-maroon'}`}>
                                                                {margin.toFixed(1)}%
                                                            </p>
                                                        </div>
                                                        <div className="bg-neo-navy p-3 text-center">
                                                            <p className="text-neo-cream/50 text-[8px] uppercase font-bold tracking-wider">Markup</p>
                                                            <p className="text-xl font-heading font-bold text-neo-orange">
                                                                {markup.toFixed(1)}%
                                                            </p>
                                                        </div>
                                                        <div className="bg-neo-navy p-3 text-center">
                                                            <p className="text-neo-cream/50 text-[8px] uppercase font-bold tracking-wider">Accept Rate</p>
                                                            <p className={`text-xl font-heading font-bold ${acceptRate >= 50 ? 'text-neo-teal' : acceptRate > 0 ? 'text-neo-orange' : 'text-neo-cream/30'}`}>
                                                                {product.stats.totalSessions > 0 ? `${acceptRate.toFixed(0)}%` : '—'}
                                                            </p>
                                                        </div>
                                                    </div>
                                                </div>

                                                {/* ── Row 2: Price Range Visualization ── */}
                                                <div className="px-4 pb-3">
                                                    <p className="text-[10px] uppercase font-bold text-neo-navy/50 mb-2 flex items-center gap-1">
                                                        <Target className="w-3 h-3" /> Price Positioning
                                                    </p>
                                                    <div className="bg-neo-navy/5 border-[2px] border-neo-navy p-3">
                                                        {/* Price bar */}
                                                        <div className="relative h-8 bg-neo-navy/10 border border-neo-navy/20 overflow-hidden">
                                                            {/* Cost zone */}
                                                            <div className="absolute inset-y-0 left-0 bg-neo-maroon/20" style={{ width: `${100 - margin}%` }} />
                                                            {/* Profit zone */}
                                                            <div className="absolute inset-y-0 right-0 bg-neo-teal/30" style={{ width: `${margin}%` }} />
                                                            {/* Min acceptable marker */}
                                                            <div
                                                                className="absolute top-0 bottom-0 w-0.5 bg-neo-orange z-10"
                                                                style={{ left: `${Math.min(Math.max(minPos, 2), 98)}%` }}
                                                            >
                                                                <div className="absolute -top-5 left-1/2 -translate-x-1/2 bg-neo-orange text-neo-navy text-[8px] font-bold px-1.5 py-0.5 whitespace-nowrap">
                                                                    Min ₹{product.minAcceptablePrice}
                                                                </div>
                                                            </div>
                                                        </div>
                                                        {/* Labels */}
                                                        <div className="flex justify-between mt-1.5">
                                                            <span className="text-[10px] font-bold text-neo-maroon flex items-center gap-0.5">
                                                                <TrendingDown className="w-3 h-3" /> Cost ₹{product.costPrice}
                                                            </span>
                                                            <span className="text-[10px] font-bold text-neo-teal flex items-center gap-0.5">
                                                                Base ₹{product.basePrice} <TrendingUp className="w-3 h-3" />
                                                            </span>
                                                        </div>
                                                    </div>
                                                </div>

                                                {/* ── Row 3: Negotiation & Strategy ── */}
                                                <div className="px-4 pb-3 grid grid-cols-1 sm:grid-cols-2 gap-3">
                                                    {/* Negotiation Buffer */}
                                                    <div className="border-[2px] border-neo-navy p-3">
                                                        <p className="text-[10px] uppercase font-bold text-neo-navy/50 mb-2 flex items-center gap-1">
                                                            <Activity className="w-3 h-3" /> Negotiation Room
                                                        </p>
                                                        <div className="space-y-2">
                                                            <div>
                                                                <div className="flex justify-between text-[10px] mb-1">
                                                                    <span className="text-neo-navy/60 font-bold">Buffer</span>
                                                                    <span className="font-bold text-neo-navy">₹{negotiationBuffer.toFixed(0)} ({bufferPercent.toFixed(1)}%)</span>
                                                                </div>
                                                                <div className="h-3 bg-neo-navy/10 border border-neo-navy/20 overflow-hidden">
                                                                    <div
                                                                        className={`h-full transition-all ${bufferPercent > 20 ? 'bg-neo-teal' : bufferPercent > 10 ? 'bg-neo-orange' : 'bg-neo-maroon'}`}
                                                                        style={{ width: `${Math.min(bufferPercent, 100)}%` }}
                                                                    />
                                                                </div>
                                                            </div>
                                                            <div className="flex items-center justify-between text-xs">
                                                                <span className="text-neo-navy/60">Max Loss</span>
                                                                <span className="font-bold text-neo-maroon">{product.maxLossPercent}% (₹{maxLossAmt.toFixed(0)})</span>
                                                            </div>
                                                            <div className="flex items-center justify-between text-xs">
                                                                <span className="text-neo-navy/60">Max Rounds</span>
                                                                <span className="font-bold text-neo-navy">{product.maxRounds}</span>
                                                            </div>
                                                        </div>
                                                    </div>

                                                    {/* Deal Funnel */}
                                                    <div className="border-[2px] border-neo-navy p-3">
                                                        <p className="text-[10px] uppercase font-bold text-neo-navy/50 mb-2 flex items-center gap-1">
                                                            <ShoppingCart className="w-3 h-3" /> Deal Funnel
                                                        </p>
                                                        {product.stats.totalSessions > 0 ? (
                                                            <div className="space-y-1.5">
                                                                {/* Sessions bar */}
                                                                <div>
                                                                    <div className="flex justify-between text-[10px] mb-0.5">
                                                                        <span className="font-bold text-neo-navy">Sessions</span>
                                                                        <span className="font-bold text-neo-navy">{product.stats.totalSessions}</span>
                                                                    </div>
                                                                    <div className="h-5 bg-neo-navy flex items-center justify-end pr-2">
                                                                        <span className="text-[9px] font-bold text-neo-cream/70">100%</span>
                                                                    </div>
                                                                </div>
                                                                {/* Deals bar */}
                                                                <div>
                                                                    <div className="flex justify-between text-[10px] mb-0.5">
                                                                        <span className="font-bold text-neo-teal">Deals Closed</span>
                                                                        <span className="font-bold text-neo-teal">{product.stats.acceptedDeals}</span>
                                                                    </div>
                                                                    <div className="h-5 bg-neo-navy/10 border border-neo-navy/20 overflow-hidden">
                                                                        <div
                                                                            className="h-full bg-neo-teal flex items-center justify-end pr-2 transition-all"
                                                                            style={{ width: `${Math.max(acceptRate, 4)}%` }}
                                                                        >
                                                                            {acceptRate >= 15 && (
                                                                                <span className="text-[9px] font-bold text-neo-cream">{acceptRate.toFixed(0)}%</span>
                                                                            )}
                                                                        </div>
                                                                    </div>
                                                                </div>
                                                                {/* Lost bar */}
                                                                <div>
                                                                    <div className="flex justify-between text-[10px] mb-0.5">
                                                                        <span className="font-bold text-neo-maroon">Lost / Rejected</span>
                                                                        <span className="font-bold text-neo-maroon">{product.stats.totalSessions - product.stats.acceptedDeals}</span>
                                                                    </div>
                                                                    <div className="h-5 bg-neo-navy/10 border border-neo-navy/20 overflow-hidden">
                                                                        <div
                                                                            className="h-full bg-neo-maroon/70 flex items-center justify-end pr-2 transition-all"
                                                                            style={{ width: `${Math.max(100 - acceptRate, 4)}%` }}
                                                                        >
                                                                            {(100 - acceptRate) >= 15 && (
                                                                                <span className="text-[9px] font-bold text-neo-cream">{(100 - acceptRate).toFixed(0)}%</span>
                                                                            )}
                                                                        </div>
                                                                    </div>
                                                                </div>
                                                            </div>
                                                        ) : (
                                                            <div className="h-24 flex items-center justify-center text-neo-navy/30 border-[2px] border-dashed border-neo-navy/20">
                                                                <div className="text-center">
                                                                    <ShoppingCart className="w-5 h-5 mx-auto mb-1 opacity-40" />
                                                                    <p className="text-[10px]">No negotiations yet</p>
                                                                </div>
                                                            </div>
                                                        )}
                                                    </div>
                                                </div>

                                                {/* ── Row 4: Revenue & Summary ── */}
                                                <div className="px-4 pb-4">
                                                    <div className="grid grid-cols-3 gap-2">
                                                        <div className="bg-neo-teal/10 border-[2px] border-neo-teal p-3 text-center">
                                                            <p className="text-[8px] uppercase font-bold text-neo-teal/70 tracking-wider">Revenue</p>
                                                            <p className="text-lg font-heading font-bold text-neo-teal">
                                                                ₹{(product.stats.revenue || 0).toLocaleString()}
                                                            </p>
                                                        </div>
                                                        <div className="bg-neo-orange/10 border-[2px] border-neo-orange p-3 text-center">
                                                            <p className="text-[8px] uppercase font-bold text-neo-orange/70 tracking-wider">Avg Margin</p>
                                                            <p className="text-lg font-heading font-bold text-neo-orange">
                                                                {product.stats.avgMargin > 0 ? `${product.stats.avgMargin.toFixed(1)}%` : '—'}
                                                            </p>
                                                        </div>
                                                        <div className="bg-neo-navy/5 border-[2px] border-neo-navy p-3 text-center">
                                                            <p className="text-[8px] uppercase font-bold text-neo-navy/50 tracking-wider">Strategy</p>
                                                            <p className={`text-sm font-heading font-bold ${product.mode === 'MAX_PROFIT' ? 'text-neo-teal' : 'text-neo-maroon'}`}>
                                                                {product.mode === 'MAX_PROFIT' ? 'MAX PROFIT' : 'MIN LOSS'}
                                                            </p>
                                                            <Award className="w-4 h-4 mx-auto mt-1 text-neo-navy/30" />
                                                        </div>
                                                    </div>
                                                </div>
                                            </div>
                                        );
                                    })()}
                                </NeoCard>
                            ))}
                        </div>

                        {/* CSV Format Tip */}
                        <NeoCard variant="navy" className="p-6 mt-8">
                            <div className="flex items-start gap-4">
                                <div className="w-12 h-12 bg-neo-orange flex items-center justify-center flex-shrink-0">
                                    <Upload className="w-6 h-6 text-neo-navy" />
                                </div>
                                <div>
                                    <h4 className="font-heading font-bold text-neo-cream mb-2">Bulk Import via CSV</h4>
                                    <p className="text-neo-cream/70 text-sm mb-2">
                                        Upload a CSV file with columns: <span className="text-neo-orange font-bold">name, basePrice, costPrice, category</span> (category optional).
                                    </p>
                                    <p className="text-neo-cream/50 text-xs font-mono">
                                        name,basePrice,costPrice,category<br />
                                        Premium Widget,100,40,Electronics<br />
                                        Basic Plan,50,20,Services
                                    </p>
                                </div>
                            </div>
                        </NeoCard>

                    </div>
                </div>
            </section>
        </Layout>
    );
}
