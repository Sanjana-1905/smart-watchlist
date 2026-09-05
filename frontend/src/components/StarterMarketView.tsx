import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../services/api';
import type { Stock } from '../types/market';
import type { Analytics } from '../types/analytics';
import MarketDelta from './MarketDelta';

interface StarterMarketViewProps {
  onStockAdded: () => void;
}

export default function StarterMarketView({ onStockAdded }: StarterMarketViewProps) {
  const [stocks, setStocks] = useState<Stock[]>([]);
  const [analyticsMap, setAnalyticsMap] = useState<Record<string, Analytics>>({});
  const [loading, setLoading] = useState(true);
  const [pending, setPending] = useState<string | null>(null);
  const [search, setSearch] = useState('');

  useEffect(() => {
    let active = true;
    api.getAllStocks()
      .then(async catalog => {
        if (!active) return;
        setStocks(catalog);

        const topSymbols = catalog.slice(0, 6).map(s => s.symbol);
        const results = await Promise.allSettled(topSymbols.map(sym => api.getAnalytics(sym)));
        if (!active) return;

        const map: Record<string, Analytics> = {};
        results.forEach((res, i) => {
          if (res.status === 'fulfilled') {
            map[topSymbols[i]] = res.value;
          }
        });
        setAnalyticsMap(map);
      })
      .catch(() => {})
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => { active = false; };
  }, []);

  async function handleAdd(symbol: string) {
    setPending(symbol);
    try {
      await api.addWatchlistStock(symbol);
      onStockAdded();
    } catch {
      setPending(null);
    }
  }

  const filtered = stocks.filter(s =>
    `${s.symbol} ${s.company_name}`.toLowerCase().includes(search.trim().toLowerCase())
  );

  return (
    <section className="starter-market" style={{ marginTop: '32px' }}>
      <div style={{ background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: '8px', padding: '32px' }}>
        <p className="eyebrow" style={{ color: '#4f46e5' }}>Welcome / Build Your Attention Desk</p>
        <h2 style={{ fontSize: '28px', fontWeight: 650, letterSpacing: '-.03em', margin: '8px 0 12px', color: '#0f172a' }}>
          Track companies you care about.
        </h2>
        <p className="caption" style={{ maxWidth: '640px', fontSize: '14px', marginBottom: '24px', lineHeight: '1.6' }}>
          Smart Watchlist calculates unusual market movement and separates objective market significance from your personal relevance. Search the catalog below to add your first stock.
        </p>

        <div style={{ marginBottom: '24px', maxWidth: '400px' }}>
          <input
            type="search"
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Search company or symbol (e.g. RELIANCE, BEL)..."
            style={{ width: '100%', padding: '12px 16px', border: '1px solid #cbd5e1', borderRadius: '6px', fontSize: '14px' }}
          />
        </div>

        <div className="section-heading" style={{ marginBottom: '16px' }}>
          <h3>Market Right Now</h3>
          <Link to="/explore" className="text-action" style={{ fontWeight: 600 }}>
            Browse all companies →
          </Link>
        </div>

        {loading ? (
          <p className="caption" role="status">Loading market preview…</p>
        ) : (
          <div className="table-scroll" tabIndex={0} role="region" aria-label="Starter market table">
            <table>
              <thead>
                <tr>
                  <th>Stock / Company</th>
                  <th>Price</th>
                  <th>Today</th>
                  <th>Market Significance</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {filtered.slice(0, 8).map(stock => {
                  const a = analyticsMap[stock.symbol];
                  return (
                    <tr key={stock.symbol}>
                      <td>
                        <Link to={`/stock/${stock.symbol}`} style={{ color: '#4f46e5', fontWeight: 700 }}>
                          {stock.symbol}
                        </Link>
                        <small>{stock.company_name}</small>
                      </td>
                      <td style={{ fontWeight: 600 }}>
                        {a?.observation.current_price != null ? `₹${a.observation.current_price.toFixed(2)}` : '—'}
                      </td>
                      <td>
                        {a ? <MarketDelta value={a.temporal.session_change_pct} /> : '—'}
                      </td>
                      <td>
                        {a?.attention ? (
                          <span style={{ fontWeight: 600, color: '#0f172a' }}>
                            {a.attention.objective_score.toFixed(1)} / 80
                          </span>
                        ) : '—'}
                      </td>
                      <td>
                        <button
                          className="secondary-action"
                          disabled={pending === stock.symbol}
                          onClick={() => handleAdd(stock.symbol)}
                          style={{ padding: '6px 14px', fontSize: '12px' }}
                          aria-label={`Add ${stock.symbol} to watchlist`}
                        >
                          {pending === stock.symbol ? 'Adding…' : '+ Watch'}
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </section>
  );
}
