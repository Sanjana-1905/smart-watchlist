import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import type { Stock, PriceSnapshot, WatchlistItem } from '../types/market';
import { api } from '../services/api';
import PriceChart from '../components/PriceChart';

export default function StockDetail() {
  const { symbol } = useParams<{ symbol: string }>();
  const [stock, setStock] = useState<Stock | null>(null);
  const [history, setHistory] = useState<PriceSnapshot[]>([]);
  const [attention, setAttention] = useState<WatchlistItem | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [marking, setMarking] = useState(false);
  const [justViewed, setJustViewed] = useState(false);

  useEffect(() => {
    if (symbol) load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [symbol]);

  const load = async () => {
    if (!symbol) return;
    setLoading(true);
    setError(null);
    try {
      const [stockRes, historyRes, changesRes] = await Promise.all([
        api.getStock(symbol),
        api.getStockHistory(symbol),
        api.getWatchlistChanges(),
      ]);
      setStock(stockRes);
      setHistory(historyRes);
      const match = changesRes.items.find((i) => i.symbol === symbol.toUpperCase());
      setAttention(match ?? null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load stock');
    } finally {
      setLoading(false);
    }
  };

  const handleMarkViewed = async () => {
    if (!symbol) return;
    setMarking(true);
    try {
      await api.markViewed(symbol);
      setJustViewed(true);
      await load();
    } catch {
      // non-fatal for MVP
    } finally {
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
    <div className="min-h-screen bg-white">
      <header className="border-b border-gray-200 px-8 py-6">
        <div className="max-w-4xl mx-auto flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2 text-sm text-gray-600 hover:text-gray-900">
            <ArrowLeft size={16} />
            Back to watchlist
          </Link>
          {attention && (
            <span className={`px-3 py-1 rounded-full text-xs font-semibold ${levelPill}`}>
              {level}
            </span>
          )}
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-8 py-12 space-y-10">
        <div>
          <p className="text-sm text-gray-600">{stock.company_name}</p>
          <h1 className="text-3xl font-bold text-gray-900">{stock.symbol}</h1>
          <p className="text-xs text-gray-500 mt-1">
            {stock.exchange}{stock.sector ? ` · ${stock.sector}` : ''}
          </p>
        </div>

        <div className="space-y-3">
          <p className="text-4xl font-bold text-gray-900">₹{currentPrice.toFixed(2)}</p>
          <div className="flex gap-8 text-sm">
            {attention && (
              <div>
                <p className="text-gray-600">Today</p>
                <p className={`text-lg font-semibold ${attention.session_change_pct >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                  {attention.session_change_pct >= 0 ? '+' : ''}{attention.session_change_pct.toFixed(2)}%
                </p>
              </div>
            )}
            <div>
              <p className="text-gray-600">Since you checked</p>
              {attention?.since_last_view_pct != null ? (
                <p className={`text-lg font-semibold ${attention.since_last_view_pct >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                  {attention.since_last_view_pct >= 0 ? '+' : ''}{attention.since_last_view_pct.toFixed(2)}%
                </p>
              ) : (
                <p className="text-lg font-semibold text-gray-400">No baseline yet</p>
              )}
            </div>
          </div>
        </div>

        {history.length >= 2 && (
          <div>
            <PriceChart data={history} />
          </div>
        )}

        {attention && attention.reasons.length > 0 && (
          <div className="pt-6 border-t">
            <p className="text-xs font-semibold text-gray-900 uppercase tracking-wide mb-4">Why this matters</p>
            <div className="space-y-3">
              {attention.reasons.map((reason, idx) => (
                <div key={idx} className="flex gap-3 text-sm">
                  <span className="text-gray-400 font-semibold">{String(idx + 1).padStart(2, '0')}</span>
                  <p className="text-gray-700">{reason.message}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {attention && (
          <div className="pt-6 border-t space-y-3">
            <div className="flex justify-between items-baseline">
              <span className="text-sm text-gray-600">Attention score</span>
              <span className="text-2xl font-bold text-gray-900">{attention.attention_score.toFixed(0)}</span>
            </div>
            <div className="w-full bg-gray-200 h-1 rounded-full overflow-hidden">
              <div className="bg-gray-900 h-full" style={{ width: `${Math.min(attention.attention_score, 100)}%` }} />
            </div>
            <div className="text-xs text-gray-500 space-y-1 pt-1">
              <div className="flex justify-between">
                <span>Objective</span>
                <span>{attention.objective_score.toFixed(0)}</span>
              </div>
              <div className="flex justify-between">
                <span>Your preferences</span>
                <span>+{attention.preference_fit.toFixed(0)}</span>
              </div>
            </div>
            <p className="text-xs text-gray-500 pt-2 italic">
              This ranks attention. It's not a buy/sell recommendation.
            </p>
          </div>
        )}

        <div className="pt-6 border-t flex items-center justify-between">
          <div className="text-xs text-gray-500">
            {attention ? (
              <span>
                {attention.freshness.status} ·{' '}
                {attention.freshness.age_minutes != null ? `${attention.freshness.age_minutes} min ago` : 'just now'} ·{' '}
                {attention.freshness.source}
              </span>
            ) : (
              <span>Not on your watchlist</span>
            )}
          </div>
          <button
            onClick={handleMarkViewed}
            disabled={marking}
            className="px-4 py-2 bg-gray-900 text-white text-sm font-medium rounded-lg hover:bg-gray-800 disabled:opacity-50"
          >
            {marking ? 'Marking...' : justViewed ? 'Viewed ✓' : 'Mark as viewed'}
          </button>
        </div>
      </main>
    </div>
  );
}
