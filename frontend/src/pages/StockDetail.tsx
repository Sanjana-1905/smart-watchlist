import { useEffect, useRef, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import type { Stock, PriceSnapshot, WatchlistItem } from '../types/market';
import { api } from '../services/api';
import AttentionScore from '../components/AttentionScore';
import DataFreshness from '../components/DataFreshness';
import PriceChart from '../components/PriceChart';

export default function StockDetail() {
  const { symbol } = useParams<{ symbol: string }>();
  return <StockDetailContent key={symbol} symbol={symbol} />;
}

function StockDetailContent({ symbol }: { symbol: string | undefined }) {
  const [stock, setStock] = useState<Stock | null>(null);
  const [history, setHistory] = useState<PriceSnapshot[]>([]);
  const [attention, setAttention] = useState<WatchlistItem | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [marking, setMarking] = useState(false);
  const [justViewed, setJustViewed] = useState(false);

  const [markError, setMarkError] = useState<string | null>(null);
  const markInFlight = useRef(false);

  useEffect(() => {
    let active = true;
    if (!symbol) { setError('Stock not found'); setLoading(false); return; }
    // Loading a detail page is read-only. Baselines change only on the button action.
    Promise.all([api.getStock(symbol), api.getStockHistory(symbol), api.getWatchlistChanges()])
      .then(([stockRes, historyRes, changesRes]) => {
        if (!active) return;
        setStock(stockRes);
        setHistory(historyRes);
        setAttention(changesRes.items.find(i => i.symbol === symbol.toUpperCase()) ?? null);
      })
      .catch(err => { if (active) setError(err instanceof Error ? err.message : 'Failed to load stock'); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [symbol]);

  const handleMarkViewed = async () => {
    if (!symbol || markInFlight.current || justViewed) return;
    markInFlight.current = true;
    setMarking(true);
    setMarkError(null);
    try {
      await api.markViewed(symbol);
      setJustViewed(true);
      try {
        const changes = await api.getWatchlistChanges();
        setAttention(changes.items.find(i => i.symbol === symbol.toUpperCase()) ?? null);
      } catch (err) {
        setMarkError(`Caught-up state saved, but refresh failed: ${err instanceof Error ? err.message : 'Please reload the page.'}`);
      }
    } catch (err) {
      setMarkError(err instanceof Error ? err.message : 'Failed to mark as caught up');
    } finally {
      markInFlight.current = false;
      setMarking(false);
    }
  };

  if (loading) {
    return <div className="min-h-screen flex items-center justify-center text-gray-600">Loading...</div>;
  }

  if (error || !stock) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center gap-4 text-gray-600">
        <p>{error || 'Stock not found'}</p>
        <Link to="/" className="text-gray-900 font-medium underline">Back to watchlist</Link>
      </div>
    );
  }

  const latest = history[history.length - 1];
  const currentPrice = attention?.current_price ?? (latest ? Number(latest.close) : 0);
  const level = attention?.attention_level ?? 'LOW';

  const levelPill =
    level === 'HIGH' ? 'bg-gray-900 text-white' :
    level === 'MEDIUM' ? 'border border-gray-400 text-gray-700' :
    'text-gray-400';

  return (
    <div className="min-h-screen bg-slate-50 font-sans pb-20">
      <header className="bg-white border-b border-slate-200 px-4 sm:px-8 py-4 sticky top-0 z-10 shadow-sm">
        <div className="max-w-3xl mx-auto flex flex-wrap gap-3 items-center justify-between">
          <Link to="/" className="flex items-center gap-2 text-sm font-medium text-slate-500 hover:text-slate-900 transition-colors">
            <ArrowLeft size={16} />
            Back to watchlist
          </Link>
          {attention && (
            <span className={`px-2.5 py-1 rounded text-[11px] font-bold tracking-wider ${levelPill}`}>
              {level}
            </span>
          )}
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-4 sm:px-8 py-10 space-y-12">
        {/* FACT SECTION */}
        <section className="bg-white rounded-xl border border-slate-200 p-4 sm:p-8 shadow-sm">
          <div className="mb-6">
            <h1 className="text-3xl font-bold text-slate-900 leading-tight">{stock.symbol}</h1>
            <p className="text-sm text-slate-500 mt-1">{stock.company_name}</p>
          </div>

          <div className="flex flex-col md:flex-row md:items-end justify-between gap-8 mb-8">
            <div>
              <p className="text-3xl sm:text-4xl break-words font-bold text-slate-900 leading-none">₹{currentPrice.toFixed(2)}</p>
              {attention && (
                <div className="flex flex-wrap items-center gap-2 mt-3">
                  <span className={`text-lg font-semibold ${attention.session_change_pct >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                    {attention.session_change_pct >= 0 ? '+' : ''}{attention.session_change_pct.toFixed(2)}%
                  </span>
                  <span className="text-sm text-slate-500">Today · vs previous close</span>
                </div>
              )}
            </div>

            <div className="bg-slate-50 border border-slate-200 rounded-lg p-4 sm:p-5 min-w-0">
              <p className="text-xs font-bold text-slate-500 uppercase tracking-widest mb-1">Since you checked</p>
              {attention?.since_last_view_pct != null ? (
                <>
                  <p className={`text-2xl font-bold ${attention.since_last_view_pct >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                    {attention.since_last_view_pct >= 0 ? '+' : ''}{attention.since_last_view_pct.toFixed(2)}%
                  </p>
                  <p className="text-xs text-slate-400 mt-1">vs your last view</p>
                </>
              ) : (
                <p className="text-lg font-medium text-slate-400 mt-1">No baseline yet</p>
              )}
            </div>
          </div>

          {history.length >= 2 && (
            <div className="mt-4">
              <PriceChart data={history} />
            </div>
          )}
        </section>

        {/* INTERPRETATION SECTION */}
        {attention && attention.reasons.length > 0 && (
          <section className="bg-white rounded-xl border border-slate-200 p-4 sm:p-8 shadow-sm">
            <h2 className="text-sm font-bold text-slate-900 uppercase tracking-widest mb-6">Why this matters</h2>
            <ul className="space-y-4">
              {attention.reasons.map((reason, idx) => (
                <li key={idx} className="flex gap-4 items-start">
                  <span className="text-slate-400 mt-0.5">•</span>
                  <p className="text-slate-700 leading-relaxed text-base">{reason.message}</p>
                </li>
              ))}
            </ul>
          </section>
        )}

        {/* PERSONALIZATION SECTION */}
        {attention && (
          <section className="bg-white rounded-xl border border-slate-200 p-4 sm:p-8 shadow-sm">
            <h2 className="text-sm font-bold text-slate-900 uppercase tracking-widest mb-6">Attention Score</h2>

            <AttentionScore objective={attention.objective_score} preference={attention.preference_fit} final={attention.attention_score} level={attention.attention_level} />

            <p className="text-sm text-slate-500 italic mt-6 bg-slate-50 p-4 rounded-lg border border-slate-100">
              Personal relevance reflects movement since your last view and your preferences. Market facts remain the same for everyone.
            </p>
          </section>
        )}

        {/* DATA SOURCE & ACTIONS */}
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4 pt-4">
          <div className="text-xs font-medium text-slate-400">
            {attention ? (
              <DataFreshness freshness={attention.freshness} />
            ) : (
              <span>Not on your watchlist</span>
            )}
          </div>
          <button
            onClick={handleMarkViewed}
            disabled={marking || justViewed}
            className="w-full sm:w-auto px-6 py-3 bg-slate-900 text-white text-sm font-semibold rounded-lg hover:bg-slate-800 disabled:opacity-50 transition-colors shadow-sm"
          >
            {marking ? 'Marking...' : justViewed ? '✓ Caught up' : 'Mark as caught up'}
          </button>
        </div>
        {markError && <p role="alert" className="text-sm text-red-700">{markError}</p>}
      </main>
    </div>
  );
}
