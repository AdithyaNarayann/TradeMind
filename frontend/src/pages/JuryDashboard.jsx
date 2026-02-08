import { useState, useEffect, useCallback } from 'react';
import {
  CheckCircle, XCircle, Clock,
  DollarSign, RefreshCw, Download, Eye, X, MessageSquare, ArrowUpRight,
  ArrowDownRight, Activity, Loader2, ChevronDown, ChevronUp,
  Search
} from 'lucide-react';
import Layout from '../components/Layout';
import NeoCard from '../components/NeoCard';
import { getDashboardSummary, exportSession } from '../lib/api';

const STATUS_CONFIG = {
  accepted:    { label: 'Accepted',    color: 'bg-neo-teal',    text: 'text-neo-cream', icon: CheckCircle  },
  rejected:    { label: 'Rejected',    color: 'bg-neo-maroon',  text: 'text-neo-cream', icon: XCircle      },
  active:      { label: 'Active',      color: 'bg-neo-orange',  text: 'text-neo-navy',  icon: Activity     },
  expired:     { label: 'Expired',     color: 'bg-neo-navy/20', text: 'text-neo-navy',  icon: Clock        },
  walked_away: { label: 'Walked Away', color: 'bg-neo-navy/30', text: 'text-neo-navy',  icon: ArrowUpRight },
};

export default function JuryDashboard() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastRefresh, setLastRefresh] = useState(null);
  const [refreshing, setRefreshing] = useState(false);

  const [statusFilter, setStatusFilter] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [sortField, setSortField] = useState('closed_at');
  const [sortDir, setSortDir] = useState('desc');

  const [chatModal, setChatModal] = useState(null);
  const [chatLoading, setChatLoading] = useState(false);
  const [exporting, setExporting] = useState({});

  const fetchDashboard = useCallback(async (showRefreshing = false) => {
    if (showRefreshing) setRefreshing(true);
    else setLoading(true);
    try {
      const result = await getDashboardSummary();
      setData(result);
      setLastRefresh(new Date());
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => { fetchDashboard(); }, [fetchDashboard]);
  useEffect(() => {
    const timer = setInterval(() => fetchDashboard(true), 30000);
    return () => clearInterval(timer);
  }, [fetchDashboard]);

  const handleViewChat = async (sessionId) => {
    setChatLoading(true);
    try {
      const session = await exportSession(sessionId);
      setChatModal(session);
    } catch { /* ignore */ }
    setChatLoading(false);
  };

  const handleExport = async (sessionId, format = 'json') => {
    const key = format === 'csv' ? `csv-${sessionId}` : sessionId;
    setExporting(p => ({ ...p, [key]: true }));
    try {
      const session = await exportSession(sessionId);
      let blob, filename;
      if (format === 'csv') {
        const msgs = session.messages || [];
        const header = 'Round,Buyer Message,Bot Reply,Offered Price,Counter Price,Decision,Time\n';
        const rows = msgs.map(m =>
          `${m.round_number},"${(m.user_message || '').replace(/"/g, '""')}","${(m.bot_reply || '').replace(/"/g, '""')}",${m.offered_price || ''},${m.counter_price || ''},${m.decision || ''},${m.created_at || ''}`
        ).join('\n');
        blob = new Blob([header + rows], { type: 'text/csv' });
        filename = `session-${sessionId}.csv`;
      } else {
        blob = new Blob([JSON.stringify(session, null, 2)], { type: 'application/json' });
        filename = `session-${sessionId}.json`;
      }
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      a.click();
      URL.revokeObjectURL(url);
    } catch { /* ignore */ }
    setExporting(p => ({ ...p, [key]: false }));
  };

  const getFilteredSessions = () => {
    if (!data) return [];
    let list = [...data.closed_sessions];
    if (statusFilter !== 'all') list = list.filter(s => s.status === statusFilter);
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      list = list.filter(s => s.product_name?.toLowerCase().includes(q));
    }
    list.sort((a, b) => {
      let va = a[sortField] ?? '', vb = b[sortField] ?? '';
      if (typeof va === 'string') return sortDir === 'asc' ? va.localeCompare(vb) : vb.localeCompare(va);
      return sortDir === 'asc' ? va - vb : vb - va;
    });
    return list;
  };

  const toggleSort = (field) => {
    if (sortField === field) setSortDir(d => d === 'asc' ? 'desc' : 'asc');
    else { setSortField(field); setSortDir('desc'); }
  };

  const SortIcon = ({ field }) => {
    if (sortField !== field) return <ChevronDown className="w-3 h-3 opacity-20" />;
    return sortDir === 'asc' ? <ChevronUp className="w-3 h-3 text-neo-orange" /> : <ChevronDown className="w-3 h-3 text-neo-orange" />;
  };

  if (loading && !data) {
    return (
      <Layout>
        <div className="flex items-center justify-center min-h-[60vh]">
          <Loader2 className="w-8 h-8 animate-spin text-neo-navy" />
          <span className="ml-3 font-bold text-neo-navy">Loading dashboard...</span>
        </div>
      </Layout>
    );
  }

  const s = data?.summary || {};
  const acceptRate = s.total > 0 ? ((s.accepted / s.total) * 100).toFixed(1) : 0;
  const filteredSessions = getFilteredSessions();

  return (
    <Layout>
      {/* ── Header ─────────────────────────────────────────── */}
      <div className="bg-neo-navy border-b-[3px] border-neo-navy">
        <div className="container mx-auto px-4">
          <div className="max-w-6xl mx-auto flex items-center justify-between py-4">
            <h1 className="text-xl sm:text-2xl font-heading font-bold text-neo-cream">
              Dashboard
            </h1>
            <div className="flex items-center gap-3">
              {lastRefresh && (
                <span className="text-[10px] text-neo-cream/40 font-mono hidden sm:block">
                  {lastRefresh.toLocaleTimeString()}
                </span>
              )}
              <button
                onClick={() => fetchDashboard(true)}
                disabled={refreshing}
                className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-bold uppercase bg-neo-navy text-neo-cream border-[2px] border-neo-navy hover:bg-neo-orange hover:border-neo-orange transition-colors"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${refreshing ? 'animate-spin' : ''}`} />
                Refresh
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* ── Main Content ──────────────────────────────────── */}
      <section className="py-6 bg-neo-cream min-h-[70vh]">
        <div className="container mx-auto px-4">
          <div className="max-w-6xl mx-auto">

            {error && (
              <div className="bg-neo-maroon text-neo-cream border-[3px] border-neo-navy p-3 mb-5 flex items-center justify-between text-sm font-bold">
                <span>{error}</span>
                <button onClick={() => fetchDashboard()} className="px-3 py-1 bg-neo-orange text-neo-navy text-xs font-bold border-[2px] border-neo-navy">Retry</button>
              </div>
            )}

            {/* ── Stats Cards ──────────────────────────────── */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
              {[
                { val: s.total || 0,       label: 'Total',    accent: 'border-neo-navy'  },
                { val: s.accepted || 0,     label: 'Accepted', accent: 'border-neo-teal'  },
                { val: s.rejected || 0,     label: 'Rejected', accent: 'border-neo-maroon'},
                { val: `${acceptRate}%`,    label: 'Accept Rate', accent: 'border-neo-orange' },
              ].map((item, i) => (
                <div key={i} className={`bg-white border-[3px] ${item.accent} p-4`}>
                  <p className="text-2xl sm:text-3xl font-heading font-bold text-neo-navy">{item.val}</p>
                  <p className="text-[11px] text-neo-navy/50 uppercase font-bold tracking-wide mt-1">{item.label}</p>
                </div>
              ))}
            </div>

            {/* ── Revenue + Avg Deal + Rounds row ──────────── */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-6">
              <div className="bg-neo-navy border-[3px] border-neo-navy p-4 flex items-center gap-3">
                <DollarSign className="w-6 h-6 text-neo-orange flex-shrink-0" />
                <div>
                  <p className="text-lg sm:text-xl font-heading font-bold text-neo-cream">
                    ₹{(s.total_revenue || 0).toLocaleString('en-IN', { maximumFractionDigits: 0 })}
                  </p>
                  <p className="text-[10px] text-neo-cream/40 uppercase font-bold">Total Revenue</p>
                </div>
              </div>
              <div className="bg-white border-[3px] border-neo-navy p-4 flex items-center gap-3">
                <ArrowUpRight className="w-6 h-6 text-neo-teal flex-shrink-0" />
                <div>
                  <p className="text-lg sm:text-xl font-heading font-bold text-neo-navy">
                    ₹{(s.best_deal || 0).toLocaleString('en-IN', { maximumFractionDigits: 0 })}
                  </p>
                  <p className="text-[10px] text-neo-navy/40 uppercase font-bold">Best Deal</p>
                </div>
              </div>
              <div className="bg-white border-[3px] border-neo-navy p-4 flex items-center gap-3">
                <MessageSquare className="w-6 h-6 text-neo-navy/40 flex-shrink-0" />
                <div>
                  <p className="text-lg sm:text-xl font-heading font-bold text-neo-navy">
                    {(s.avg_rounds || 0).toFixed(1)} <span className="text-xs font-normal text-neo-navy/40">rounds avg</span>
                  </p>
                  <p className="text-[10px] text-neo-navy/40 uppercase font-bold">Avg Negotiation</p>
                </div>
              </div>
            </div>

            {/* ── Negotiation History ──────────────────────── */}
            <div>
              <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 mb-3">
                <h2 className="font-heading font-bold text-neo-navy text-sm uppercase tracking-wider">
                  History
                </h2>
                <div className="flex items-center gap-2 flex-wrap">
                  <div className="relative">
                    <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-neo-navy/30" />
                    <input
                      type="text"
                      value={searchQuery}
                      onChange={e => setSearchQuery(e.target.value)}
                      placeholder="Search..."
                      className="pl-8 pr-3 py-1.5 text-xs border-[2px] border-neo-navy/15 bg-white focus:border-neo-orange outline-none w-36 font-mono"
                    />
                  </div>
                  <div className="flex gap-1">
                    {['all', 'accepted', 'rejected', 'expired', 'walked_away'].map(f => (
                      <button
                        key={f}
                        onClick={() => setStatusFilter(f)}
                        className={`px-2 py-1 text-[10px] font-bold uppercase border-[2px] transition-all ${
                          statusFilter === f
                            ? 'bg-neo-navy text-neo-cream border-neo-navy'
                            : 'bg-white text-neo-navy/40 border-neo-navy/10 hover:border-neo-navy/30'
                        }`}
                      >
                        {f === 'all' ? 'All' : f.replace('_', ' ')}
                      </button>
                    ))}
                  </div>
                </div>
              </div>

              <div className="bg-white border-[3px] border-neo-navy overflow-hidden">
                {/* Table header */}
                <div className="bg-neo-navy grid grid-cols-[2fr_0.8fr_1fr_1fr_0.6fr_0.8fr] text-[10px] font-bold uppercase tracking-wider text-neo-cream/50">
                  {[
                    { field: 'product_name', label: 'Product' },
                    { field: 'status',       label: 'Status'  },
                    { field: 'base_price',   label: 'Base'    },
                    { field: 'final_price',  label: 'Final'   },
                    { field: 'rounds_used',  label: 'Rounds'  },
                    { field: null,           label: 'Actions' },
                  ].map((col, i) => (
                    <button
                      key={i}
                      onClick={() => col.field && toggleSort(col.field)}
                      className={`px-3 py-2.5 text-left flex items-center gap-1 ${col.field ? 'hover:text-neo-cream cursor-pointer' : 'cursor-default'} transition-colors`}
                    >
                      {col.label}
                      {col.field && <SortIcon field={col.field} />}
                    </button>
                  ))}
                </div>

                {/* Rows */}
                {filteredSessions.length === 0 ? (
                  <div className="p-10 text-center text-neo-navy/30">
                    <p className="text-sm font-bold">No sessions found</p>
                  </div>
                ) : (
                  filteredSessions.map((session, idx) => {
                    const sc = STATUS_CONFIG[session.status] || STATUS_CONFIG.expired;
                    const StatusIcon = sc.icon;
                    const discount = session.base_price && session.final_price
                      ? (((session.base_price - session.final_price) / session.base_price) * 100).toFixed(1)
                      : null;

                    return (
                      <div
                        key={session.id}
                        className={`grid grid-cols-[2fr_0.8fr_1fr_1fr_0.6fr_0.8fr] items-center text-xs border-b last:border-b-0 border-neo-navy/5 ${
                          idx % 2 === 0 ? 'bg-white' : 'bg-neo-cream/30'
                        } hover:bg-neo-orange/5 transition-colors`}
                      >
                        {/* Product */}
                        <div className="px-3 py-3 font-bold text-neo-navy truncate">
                          {session.product_name}
                        </div>
                        {/* Status */}
                        <div className="px-3 py-3">
                          <span className={`inline-flex items-center gap-1 px-2 py-0.5 text-[9px] font-bold uppercase ${sc.color} ${sc.text}`}>
                            <StatusIcon className="w-3 h-3" />
                            {sc.label}
                          </span>
                        </div>
                        {/* Base */}
                        <div className="px-3 py-3 font-mono text-neo-navy/50">
                          ₹{(session.base_price || 0).toLocaleString('en-IN')}
                        </div>
                        {/* Final */}
                        <div className="px-3 py-3">
                          {session.final_price ? (
                            <span className="font-mono font-bold text-neo-navy">
                              ₹{session.final_price.toLocaleString('en-IN')}
                              {discount && parseFloat(discount) > 0 && (
                                <span className="ml-1 text-[9px] font-bold text-neo-maroon">
                                  <ArrowDownRight className="w-2.5 h-2.5 inline" />{discount}%
                                </span>
                              )}
                              {discount && parseFloat(discount) < 0 && (
                                <span className="ml-1 text-[9px] font-bold text-neo-teal">
                                  <ArrowUpRight className="w-2.5 h-2.5 inline" />{Math.abs(parseFloat(discount))}%
                                </span>
                              )}
                            </span>
                          ) : (
                            <span className="text-neo-navy/20">—</span>
                          )}
                        </div>
                        {/* Rounds */}
                        <div className="px-3 py-3 font-mono text-neo-navy/50 text-center">
                          {session.rounds_used || 0}
                        </div>
                        {/* Actions */}
                        <div className="px-3 py-3 flex items-center gap-1.5">
                          <button onClick={() => handleViewChat(session.id)} className="p-1.5 border-[2px] border-neo-navy/10 hover:border-neo-teal hover:bg-neo-teal/10 transition-colors group" title="View Chat">
                            <Eye className="w-3.5 h-3.5 text-neo-navy/30 group-hover:text-neo-teal" />
                          </button>
                          <button onClick={() => handleExport(session.id)} disabled={exporting[session.id]} className="p-1.5 border-[2px] border-neo-navy/10 hover:border-neo-orange hover:bg-neo-orange/10 transition-colors group" title="Export JSON">
                            {exporting[session.id] ? <Loader2 className="w-3.5 h-3.5 animate-spin text-neo-navy/30" /> : <Download className="w-3.5 h-3.5 text-neo-navy/30 group-hover:text-neo-orange" />}
                          </button>
                          <button onClick={() => handleExport(session.id, 'csv')} disabled={exporting[`csv-${session.id}`]} className="p-1.5 border-[2px] border-neo-navy/10 hover:border-neo-navy hover:bg-neo-navy/10 transition-colors text-[8px] font-bold text-neo-navy/30 hover:text-neo-navy" title="Export CSV">
                            CSV
                          </button>
                        </div>
                      </div>
                    );
                  })
                )}
              </div>

              <p className="text-[10px] text-neo-navy/30 mt-2 text-right">
                {filteredSessions.length} of {data?.closed_sessions?.length || 0} sessions
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* ── Chat Modal ─────────────────────────────────────── */}
      {(chatModal || chatLoading) && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4" onClick={() => !chatLoading && setChatModal(null)}>
          <div className="absolute inset-0 bg-neo-navy/60 backdrop-blur-sm" />
          <div className="relative bg-neo-cream border-[4px] border-neo-navy w-full max-w-2xl max-h-[85vh] flex flex-col" onClick={e => e.stopPropagation()}>
            {chatLoading ? (
              <div className="flex items-center justify-center py-16">
                <Loader2 className="w-8 h-8 animate-spin text-neo-navy" />
              </div>
            ) : chatModal && (
              <>
                {/* Header */}
                <div className="bg-neo-navy p-4 flex items-center justify-between flex-shrink-0">
                  <div>
                    <h3 className="font-heading font-bold text-neo-cream text-sm">{chatModal.product_name}</h3>
                    <div className="flex items-center gap-2 mt-1">
                      <span className={`inline-flex items-center gap-1 px-2 py-0.5 text-[9px] font-bold uppercase ${STATUS_CONFIG[chatModal.status]?.color || 'bg-neo-navy/20'} ${STATUS_CONFIG[chatModal.status]?.text || 'text-neo-navy'}`}>
                        {chatModal.status}
                      </span>
                      <span className="text-[10px] text-neo-cream/40 font-mono">Session {chatModal.id} · {chatModal.rounds_used || 0} rounds</span>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <button onClick={() => handleExport(chatModal.id)} className="p-2 bg-neo-cream/10 hover:bg-neo-cream/20 text-neo-cream transition-colors">
                      <Download className="w-4 h-4" />
                    </button>
                    <button onClick={() => setChatModal(null)} className="p-2 bg-neo-cream/10 hover:bg-neo-maroon text-neo-cream transition-colors">
                      <X className="w-4 h-4" />
                    </button>
                  </div>
                </div>

                {/* Price info */}
                <div className="bg-neo-teal/10 border-b-[2px] border-neo-navy/10 px-4 py-2 grid grid-cols-3 gap-3 text-[10px] flex-shrink-0">
                  <div>
                    <span className="text-neo-navy/40 uppercase font-bold">Base</span>
                    <p className="font-mono font-bold text-neo-navy">₹{(chatModal.base_price || 0).toLocaleString('en-IN')}</p>
                  </div>
                  <div>
                    <span className="text-neo-navy/40 uppercase font-bold">Final</span>
                    <p className="font-mono font-bold text-neo-teal">₹{(chatModal.final_price || 0).toLocaleString('en-IN')}</p>
                  </div>
                  <div>
                    <span className="text-neo-navy/40 uppercase font-bold">Min Price</span>
                    <p className="font-mono font-bold text-neo-maroon">₹{(chatModal.min_price || 0).toLocaleString('en-IN')}</p>
                  </div>
                </div>

                {/* Messages */}
                <div className="flex-1 overflow-y-auto p-4 space-y-3">
                  {(!chatModal.messages || chatModal.messages.length === 0) ? (
                    <div className="text-center text-neo-navy/30 py-8">
                      <MessageSquare className="w-8 h-8 mx-auto mb-2 opacity-30" />
                      <p className="text-sm font-bold">No messages recorded</p>
                    </div>
                  ) : (
                    chatModal.messages.map((msg, i) => (
                      <div key={i} className="space-y-2">
                        {(i === 0 || msg.round_number !== chatModal.messages[i - 1]?.round_number) && (
                          <div className="flex items-center gap-2 my-2">
                            <div className="flex-1 h-[1px] bg-neo-navy/10" />
                            <span className="text-[9px] font-bold uppercase text-neo-navy/30 px-2">Round {msg.round_number}</span>
                            <div className="flex-1 h-[1px] bg-neo-navy/10" />
                          </div>
                        )}
                        {msg.user_message && (
                          <div className="flex justify-start">
                            <div className="max-w-[75%] bg-white border-[2px] border-neo-navy/10 p-3">
                              <p className="text-[10px] font-bold text-neo-navy/40 mb-1">Buyer</p>
                              <p className="text-xs text-neo-navy">{msg.user_message}</p>
                              {msg.offered_price && (
                                <p className="text-[10px] font-mono font-bold text-neo-teal mt-1">Offered: ₹{msg.offered_price.toLocaleString('en-IN')}</p>
                              )}
                            </div>
                          </div>
                        )}
                        {msg.bot_reply && (
                          <div className="flex justify-end">
                            <div className="max-w-[75%] bg-neo-navy text-neo-cream border-[2px] border-neo-navy p-3">
                              <p className="text-[10px] font-bold text-neo-cream/50 mb-1">Bot</p>
                              <p className="text-xs">{msg.bot_reply}</p>
                              {msg.counter_price && (
                                <p className="text-[10px] font-mono font-bold text-neo-orange mt-1">Counter: ₹{msg.counter_price.toLocaleString('en-IN')}</p>
                              )}
                              {msg.decision && (
                                <span className={`inline-block mt-1 px-2 py-0.5 text-[9px] font-bold uppercase ${
                                  msg.decision === 'accept' ? 'bg-neo-teal/30 text-neo-teal' :
                                  msg.decision === 'reject' ? 'bg-neo-maroon/30 text-neo-maroon' :
                                  'bg-neo-cream/10 text-neo-cream/60'
                                }`}>
                                  {msg.decision}
                                </span>
                              )}
                            </div>
                          </div>
                        )}
                      </div>
                    ))
                  )}
                </div>

                {/* Footer */}
                <div className="bg-neo-navy/5 border-t-[2px] border-neo-navy/10 px-4 py-2 flex items-center justify-between flex-shrink-0">
                  <span className="text-[10px] text-neo-navy/30 font-mono">
                    {chatModal.messages?.length || 0} msgs
                  </span>
                  <div className="flex gap-2">
                    <button onClick={() => handleExport(chatModal.id, 'csv')} className="text-[10px] font-bold uppercase text-neo-navy/40 hover:text-neo-navy px-3 py-1 border-[2px] border-neo-navy/10 hover:border-neo-navy/30 transition-colors">CSV</button>
                    <button onClick={() => handleExport(chatModal.id)} className="text-[10px] font-bold uppercase text-neo-navy/40 hover:text-neo-navy px-3 py-1 border-[2px] border-neo-navy/10 hover:border-neo-navy/30 transition-colors">JSON</button>
                  </div>
                </div>
              </>
            )}
          </div>
        </div>
      )}
    </Layout>
  );
}
