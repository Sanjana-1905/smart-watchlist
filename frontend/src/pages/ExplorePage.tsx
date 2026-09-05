import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../services/api';
import type { Stock, BasicWatchlistItem } from '../types/market';
import type { Analytics } from '../types/analytics';
import DataFreshness from '../components/DataFreshness';
import MarketDelta from '../components/MarketDelta';

const sectorName = (sector: string | null) => sector ?? 'General';

type SortOption = 'Alphabetical' | "Today's Move" | 'Attention Score' | 'Volume Anomaly';

// Per-stock analytics state
type AnalyticsState = Analytics | 'loading' | 'error';

export default function ExplorePage() {
  const [stocks, setStocks] = useState<Stock[]>([]);
  const [members, setMembers] = useState<BasicWatchlistItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState('');
  const [sector, setSector] = useState('All sectors');
  const [sortBy, setSortBy] = useState<SortOption>('Alphabetical');
  const [page, setPage] = useState(0);
  const [analyticsMap, setAnalyticsMap] = useState<Record<string, AnalyticsState>>({});
  const [pending, setPending] = useState<string | null>(null);
  const inFlight = useRef(false);
  // Track in-flight fetch AbortControllers keyed by symbol to avoid double-firing
  const fetchingRef = useRef<Set<string>>(new Set());

  useEffect(() => {
    let active = true;
    Promise.all([api.getAllStocks(), api.getWatchlist()])
      .then(([s, m]) => {
        if (active) { setStocks(s); setMembers(m); }
      })
      .catch(e => {
        if (active) setError(e instanceof Error ? e.message : 'Failed to load market directory');
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => { active = false; };
  }, []);

  const sectors = ['All sectors', ...new Set(stocks.map(s => sectorName(s.sector)))].filter(Boolean);

  // Filter stocks
  const filtered = stocks.filter(s =>
    (sector === 'All sectors' || sectorName(s.sector) === sector) &&
    `${s.symbol} ${s.company_name}`.toLowerCase().includes(query.trim().toLowerCase())
  );

  // Page-based slice for visible items
  const PAGE_SIZE = 12;
  const sorted = [...filtered].sort((a, b) => {
    const aData = analyticsMap[a.symbol];
    const bData = analyticsMap[b.symbol];
    if (sortBy === "Today's Move") {
      const aVal = typeof aData === 'object' && aData !== null && 'temporal' in aData ? Math.abs(aData.temporal.session_change_pct ?? 0) : 0;
      const bVal = typeof bData === 'object' && bData !== null && 'temporal' in bData ? Math.abs(bData.temporal.session_change_pct ?? 0) : 0;
      return bVal - aVal;
    }
    if (sortBy === 'Attention Score') {
      const aVal = typeof aData === 'object' && aData !== null && 'final' in aData ? (aData.final?.attention_score ?? 0) : 0;
      const bVal = typeof bData === 'object' && bData !== null && 'final' in bData ? (bData.final?.attention_score ?? 0) : 0;
      return bVal - aVal;
    }
    if (sortBy === 'Volume Anomaly') {
      const aVal = typeof aData === 'object' && aData !== null && 'volume' in aData ? (aData.volume.volume_ratio ?? 0) : 0;
      const bVal = typeof bData === 'object' && bData !== null && 'volume' in bData ? (bData.volume.volume_ratio ?? 0) : 0;
      return bVal - aVal;
    }
    return a.symbol.localeCompare(b.symbol);
  });

  const visible = sorted.slice(page * PAGE_SIZE, page * PAGE_SIZE + PAGE_SIZE);

  // Fetch analytics for visible symbols — deduplicated, with explicit loading/error states
  useEffect(() => {
    if (visible.length === 0) return;
    let active = true;

    for (const stock of visible) {
      const sym = stock.symbol;
      // Skip if already fetched or currently fetching
      if (analyticsMap[sym] !== undefined || fetchingRef.current.has(sym)) continue;

      fetchingRef.current.add(sym);
      // Mark as loading immediately
      setAnalyticsMap(prev => ({ ...prev, [sym]: 'loading' }));

      api.getAnalytics(sym)
        .then(d => {
          if (active) {
            setAnalyticsMap(prev => ({ ...prev, [sym]: d }));
          }
        })
        .catch(() => {
          if (active) {
            setAnalyticsMap(prev => ({ ...prev, [sym]: 'error' }));
          }
        })
        .finally(() => {
          fetchingRef.current.delete(sym);
        });
    }

    return () => { active = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [visible.map(s => s.symbol).join(',')]);

  async function toggle(stock: Stock) {
    if (inFlight.current) return;
    inFlight.current = true;
    setPending(stock.symbol);
    setError(null);
    try {
      if (members.some(m => m.symbol === stock.symbol)) {
        await api.removeWatchlistStock(stock.symbol);
      } else {
        await api.addWatchlistStock(stock.symbol);
      }
      setMembers(await api.getWatchlist());
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not update watchlist');
    } finally {
      inFlight.current = false;
      setPending(null);
    }
  }

  function retryAnalytics(symbol: string) {
    if (fetchingRef.current.has(symbol)) return;
    fetchingRef.current.add(symbol);
    setAnalyticsMap(prev => ({ ...prev, [symbol]: 'loading' }));
    api.getAnalytics(symbol)
      .then(d => setAnalyticsMap(prev => ({ ...prev, [symbol]: d })))
      .catch(() => setAnalyticsMap(prev => ({ ...prev, [symbol]: 'error' })))
      .finally(() => fetchingRef.current.delete(symbol));
  }

  return (
    <main className="explore-page">
      <p className="eyebrow" style={{ color: '#4f46e5' }}>Market Explorer</p>
      <h1>Explore Companies</h1>
      <p className="muted" style={{ marginBottom: '32px' }}>
        Explore companies, compare market behavior, and add the ones you care about to your attention desk.
      </p>

      {/* Filter and Search Bar */}
      <div className="explore-search">
        <label htmlFor="stock-search">
          Search
          <input
            id="stock-search"
            type="search"
            value={query}
            placeholder="Symbol or company name…"
            onChange={e => { setQuery(e.target.value); setPage(0); }}
          />
        </label>

        <label htmlFor="sector-filter">
          Sector
          <select id="sector-filter" value={sector} onChange={e => { setSector(e.target.value); setPage(0); }}>
            {sectors.map(s => <option key={s}>{s}</option>)}
          </select>
        </label>

        <label htmlFor="sort-filter">
          Sort by
          <select id="sort-filter" value={sortBy} onChange={e => setSortBy(e.target.value as SortOption)}>
            <option value="Alphabetical">Alphabetical</option>
            <option value="Today's Move">Today's Move</option>
            <option value="Attention Score">Attention Score</option>
            <option value="Volume Anomaly">Volume Ratio</option>
          </select>
        </label>
      </div>

      {error && <p role="alert" style={{ color: '#dc2626', marginBottom: '16px' }}>{error}</p>}

      {loading ? (
        <p role="status" className="caption" style={{ marginTop: '32px' }}>Loading market directory…</p>
      ) : (
        <>
          <div className="section-heading" style={{ margin: '8px 0 16px' }}>
            <h2>
              {query || sector !== 'All sectors'
                ? `${filtered.length} ${filtered.length === 1 ? 'company' : 'companies'} matched`
                : `${stocks.length} NSE companies available`}
            </h2>
            <span className="caption">{members.length} watched</span>
          </div>

          <div className="explore-list">
            {visible.map(stock => {
              const a = analyticsMap[stock.symbol];
              const watched = members.some(m => m.symbol === stock.symbol);
              const analytics = (a !== 'loading' && a !== 'error' && a !== undefined) ? a as Analytics : null;

              return (
                <article
                  key={stock.symbol}
                  className="explore-entry"
                  style={{ background: watched ? '#f8fafc' : '#ffffff' }}
                >
                  <div>
                    <p className="eyebrow" style={{ color: '#94a3b8', marginBottom: '4px' }}>
                      {sectorName(stock.sector)} · {stock.exchange}
                    </p>
                    <Link className="explore-symbol" to={`/stock/${encodeURIComponent(stock.symbol)}`}>
                      {stock.symbol}
                    </Link>
                    <p className="muted" style={{ fontSize: '13px', marginTop: '2px' }}>{stock.company_name}</p>
                  </div>

                  <div className="explore-observation">
                    {a === 'loading' || a === undefined ? (
                      <p role="status" className="caption" style={{ color: '#94a3b8' }}>
                        <span style={{ display: 'inline-block', width: '80px', height: '12px', background: '#e2e8f0', borderRadius: '4px', animation: 'pulse 1.5s infinite' }} />
                      </p>
                    ) : a === 'error' ? (
                      <div>
                        <p className="caption" style={{ color: '#94a3b8', marginBottom: '4px' }}>Market data temporarily unavailable</p>
                        <button
                          className="text-link"
                          style={{ fontSize: '11px', padding: 0, border: 0, background: 'transparent', cursor: 'pointer', color: '#4f46e5' }}
                          onClick={() => retryAnalytics(stock.symbol)}
                        >
                          Retry
                        </button>
                      </div>
                    ) : analytics?.observation.current_price == null ? (
                      <p className="caption" style={{ color: '#94a3b8' }}>
                        Market data unavailable
                      </p>
                    ) : (
                      <>
                        <strong style={{ fontSize: '18px', display: 'block', color: '#0f172a' }}>
                          ₹{analytics.observation.current_price.toFixed(2)}
                        </strong>
                        {analytics.temporal.session_change_pct != null && (
                          <div style={{ display: 'flex', gap: '12px', alignItems: 'center', marginTop: '4px', flexWrap: 'wrap' }}>
                            <MarketDelta value={analytics.temporal.session_change_pct} />
                            {analytics.volatility && analytics.volatility.unusualness_ratio > 1.2 && (
                              <span style={{ fontSize: '11px', color: '#4f46e5', background: '#eef2ff', padding: '1px 6px', borderRadius: '4px' }}>
                                {analytics.volatility.unusualness_ratio.toFixed(2)}× normal
                              </span>
                            )}
                          </div>
                        )}
                        <DataFreshness freshness={analytics.observation.freshness} compact />
                      </>
                    )}
                  </div>

                  <div style={{ display: 'flex', gap: '8px', alignItems: 'center', flexWrap: 'wrap' }}>
                    <Link
                      to={`/stock/${encodeURIComponent(stock.symbol)}`}
                      className="secondary-action"
                      style={{ textDecoration: 'none', color: '#4f46e5' }}
                    >
                      View Lens
                    </Link>
                    <button
                      className="secondary-action"
                      disabled={pending !== null}
                      onClick={() => toggle(stock)}
                      style={{
                        background: watched ? '#e2e8f0' : '#ffffff',
                        fontWeight: watched ? 600 : 400,
                      }}
                      aria-label={`${watched ? 'Remove' : 'Add'} ${stock.symbol} ${watched ? 'from' : 'to'} watchlist`}
                      aria-pressed={watched}
                    >
                      {pending === stock.symbol ? 'Saving…' : watched ? '✓ Watching' : '+ Watch'}
                    </button>
                  </div>
                </article>
              );
            })}
          </div>

          {!visible.length && (
            <p className="caption" style={{ marginTop: '32px', color: '#64748b' }}>
              No companies match your search. <button className="text-link" style={{ padding: 0, border: 0, background: 'transparent', cursor: 'pointer' }} onClick={() => { setQuery(''); setSector('All sectors'); }}>Clear filters</button>
            </p>
          )}

          <nav className="explore-pagination" aria-label="Market directory pages">
            <button disabled={page === 0} onClick={() => setPage(p => p - 1)}>← Previous</button>
            <span className="caption">
              Page {page + 1} of {Math.max(1, Math.ceil(filtered.length / PAGE_SIZE))}
              {' '}· Showing {visible.length} of {filtered.length}
            </span>
            <button disabled={(page + 1) * PAGE_SIZE >= filtered.length} onClick={() => setPage(p => p + 1)}>Next →</button>
          </nav>
        </>
      )}
    </main>
  );
}
