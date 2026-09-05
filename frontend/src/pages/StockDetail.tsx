import { useEffect, useRef, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import type { Analytics } from '../types/analytics';
import { api, type BasicWatchlistItem } from '../services/api';
import DataFreshness from '../components/DataFreshness';
import ReasonsList from '../components/ReasonsList';
import MarketDelta from '../components/MarketDelta';
import RelatedContext from '../components/RelatedContext';
import ShowMath from '../components/ShowMath';
import PriceChart from '../components/PriceChart';

export default function StockDetail() {
  const { symbol } = useParams<{ symbol: string }>();
  return <StockDetailContent key={symbol} symbol={symbol} />;
}

function StockDetailContent({ symbol }: { symbol: string | undefined }) {
  const [data, setData] = useState<Analytics | null>(null);
  const [watchlistItems, setWatchlistItems] = useState<BasicWatchlistItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [marking, setMarking] = useState(false);
  const [justViewed, setJustViewed] = useState(false);
  const [markError, setMarkError] = useState<string | null>(null);
  const [togglingWatch, setTogglingWatch] = useState(false);
  const markInFlight = useRef(false);

  useEffect(() => {
    let active = true;
    if (!symbol) { setError('Stock symbol not specified'); return; }

    Promise.all([api.getAnalytics(symbol), api.getWatchlist()])
      .then(([result, members]) => {
        if (active) {
          setData(result);
          setWatchlistItems(members);
        }
      })
      .catch(err => {
        if (active) setError(err instanceof Error ? err.message : 'Failed to load stock analytics');
      });

    return () => { active = false; };
  }, [symbol]);

  const isWatched = watchlistItems.some(m => m.symbol.toUpperCase() === symbol?.toUpperCase());

  async function handleToggleWatch() {
    if (!symbol || togglingWatch) return;
    setTogglingWatch(true);
    try {
      if (isWatched) {
        await api.removeWatchlistStock(symbol);
      } else {
        await api.addWatchlistStock(symbol);
      }
      const updated = await api.getWatchlist();
      setWatchlistItems(updated);
    } catch (err) {
      setMarkError(err instanceof Error ? err.message : 'Failed to update watchlist');
    } finally {
      setTogglingWatch(false);
    }
  }

  async function markViewed() {
    if (!symbol || markInFlight.current || justViewed) return;
    markInFlight.current = true;
    setMarking(true);
    setMarkError(null);
    try {
      await api.markViewed(symbol);
      setJustViewed(true);
      try {
        setData(await api.getAnalytics(symbol));
      } catch (err) {
        setMarkError(`Caught-up state saved, but refresh failed: ${err instanceof Error ? err.message : 'Please reload.'}`);
      }
    } catch (err) {
      setMarkError(err instanceof Error ? err.message : 'Failed to mark as caught up');
    } finally {
      markInFlight.current = false;
      setMarking(false);
    }
  }

  if (error) {
    return (
      <main className="analysis-page">
        <Link to="/" className="text-link">← Attention Desk</Link>
        <div role="alert" style={{ borderLeft: '2px solid #dc2626', paddingLeft: '16px', margin: '48px 0' }}>
          <p style={{ color: '#dc2626', fontWeight: 600 }}>{error}</p>
          <Link to="/explore" className="text-link" style={{ display: 'block', marginTop: '12px' }}>
            Browse all companies →
          </Link>
        </div>
      </main>
    );
  }

  if (!data) return (
    <main className="analysis-page" role="status">
      <Link to="/" className="text-link">← Attention Desk</Link>
      <p className="caption" style={{ marginTop: '48px' }}>Loading stock analysis…</p>
    </main>
  );

  const { identity, observation, temporal, volatility, volume, technical, attention, personal, final } = data;

  const hasBaseline = temporal.last_viewed_price != null;
  const sinceCheckedLabel = !hasBaseline
    ? null
    : temporal.since_last_view_pct;

  // Sanitize primary reason text
  function sanitizeReason(msg: string): string {
    if (!msg) return 'Within normal range';
    if (msg.toLowerCase().includes('no emitted signal') || msg.toLowerCase().includes('emitted')) {
      return 'Within normal range';
    }
    return msg;
  }

  return (
    <main className="analysis-page">
      <Link className="text-link" to="/">← Attention Desk</Link>

      {/* Header: Identity & Watch Action */}
      <header className="analysis-heading" style={{ margin: '24px 0 20px' }}>
        <div>
          <p className="eyebrow" style={{ color: '#4f46e5' }}>
            {identity.exchange} · {identity.sector ?? 'General'}
          </p>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: '16px', flexWrap: 'wrap' }}>
            <h1 style={{ margin: 0 }}>{identity.symbol}</h1>
            <button
              type="button"
              className="secondary-action"
              onClick={handleToggleWatch}
              disabled={togglingWatch}
              style={{ padding: '8px 16px', fontSize: '13px', fontWeight: 600 }}
            >
              {togglingWatch ? 'Saving…' : isWatched ? '− In Watchlist' : '+ Add to Watchlist'}
            </button>
          </div>
          <p className="muted" style={{ fontSize: '16px', marginTop: '4px' }}>{identity.company_name}</p>
        </div>

        {/* Attention Score Badge */}
        {final ? (
          <div className="attention-total">
            <span className="eyebrow">Attention</span>
            <strong style={{ background: final.attention_level === 'HIGH' ? '#bef264' : '#e2e8f0' }}>
              {final.attention_score}
            </strong>
            <span style={{ fontWeight: 600, color: '#475569' }}>{final.attention_level}</span>
          </div>
        ) : (
          <p className="caption">Analytics unavailable</p>
        )}
      </header>

      {/* Provenance — compact */}
      <div style={{ marginBottom: '24px' }}>
        <DataFreshness freshness={observation.freshness} />
      </div>

      {/* Prominent Price & Dual Return Comparison */}
      <section style={{ borderTop: '2px solid #e2e8f0', paddingTop: '28px', marginBottom: '32px' }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '32px' }}>
          <div>
            <p className="eyebrow" style={{ color: '#64748b', marginBottom: '8px' }}>Latest Price</p>
            <strong style={{ display: 'block', fontSize: 'clamp(32px,5vw,50px)', fontWeight: 500, letterSpacing: '-.03em', color: '#0f172a' }}>
              {observation.current_price === null ? '—' : `₹${observation.current_price.toFixed(2)}`}
            </strong>
          </div>

          <div>
            <p className="eyebrow" style={{ color: '#64748b', marginBottom: '8px' }}>TODAY</p>
            {temporal.session_change_pct != null
              ? <MarketDelta value={temporal.session_change_pct} large />
              : <span className="caption" style={{ color: '#94a3b8' }}>—</span>}
            {temporal.previous_session_close != null && (
              <p className="caption" style={{ marginTop: '4px' }}>
                vs prev close ₹{temporal.previous_session_close.toFixed(2)}
              </p>
            )}
          </div>

          <div>
            <p className="eyebrow" style={{ color: '#4f46e5', marginBottom: '8px' }}>SINCE YOU CHECKED</p>
            {!hasBaseline ? (
              <div>
                <p style={{ fontSize: '15px', color: '#94a3b8', fontWeight: 500 }}>Not established yet</p>
                <p className="caption" style={{ marginTop: '4px', maxWidth: '220px' }}>
                  Your personal comparison begins after you mark this stock as caught up.
                </p>
                <button
                  className="secondary-action"
                  disabled={marking || observation.current_price === null}
                  onClick={markViewed}
                  style={{ marginTop: '10px', padding: '8px 14px', fontSize: '12px' }}
                >
                  {marking ? 'Marking…' : 'Mark as caught up'}
                </button>
              </div>
            ) : (
              <>
                <MarketDelta value={sinceCheckedLabel} large />
                {temporal.last_viewed_price != null && (
                  <p className="caption" style={{ marginTop: '4px' }}>
                    vs your saved ₹{temporal.last_viewed_price.toFixed(2)}
                  </p>
                )}
              </>
            )}
          </div>
        </div>
      </section>

      {/* Real Price History Chart */}
      <PriceChart
        history={data.history}
        lastViewedPrice={temporal.last_viewed_price}
        lastViewedAt={temporal.last_viewed_at?.toString()}
        companyName={identity.company_name}
        symbol={identity.symbol}
      />

      {/* Market Pattern (Factual Metrics Grid) */}
      <section style={{ margin: '40px 0', borderTop: '1px solid #e2e8f0', paddingTop: '28px' }}>
        <p className="eyebrow" style={{ color: '#4f46e5' }}>Market Pattern</p>
        <h2 style={{ fontSize: '18px', fontWeight: 600, margin: '6px 0 20px' }}>Statistical Context</h2>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: '16px' }}>
          <div style={{ padding: '14px 16px', border: '1px solid #e2e8f0', borderRadius: '6px' }}>
            <p className="eyebrow" style={{ marginBottom: '6px' }}>Today</p>
            <strong style={{ fontSize: '18px' }}>
              {temporal.session_change_pct != null
                ? `${temporal.session_change_pct >= 0 ? '+' : ''}${temporal.session_change_pct.toFixed(2)}%`
                : '—'}
            </strong>
          </div>

          <div style={{ padding: '14px 16px', border: '1px solid #e2e8f0', borderRadius: '6px' }}>
            <p className="eyebrow" style={{ marginBottom: '6px' }}>5-Session</p>
            <strong style={{ fontSize: '18px' }}>
              {temporal.five_session_return_pct != null
                ? `${temporal.five_session_return_pct >= 0 ? '+' : ''}${temporal.five_session_return_pct.toFixed(2)}%`
                : '—'}
            </strong>
          </div>

          <div style={{ padding: '14px 16px', border: '1px solid #e2e8f0', borderRadius: '6px' }}>
            <p className="eyebrow" style={{ marginBottom: '6px' }}>20-Session</p>
            <strong style={{ fontSize: '18px' }}>
              {temporal.twenty_session_return_pct != null
                ? `${temporal.twenty_session_return_pct >= 0 ? '+' : ''}${temporal.twenty_session_return_pct.toFixed(2)}%`
                : '—'}
            </strong>
          </div>

          <div style={{ padding: '14px 16px', border: '1px solid #e2e8f0', borderRadius: '6px' }}>
            <p className="eyebrow" style={{ marginBottom: '6px' }}>20d Volatility</p>
            <strong style={{ fontSize: '18px' }}>
              {volatility ? `±${(volatility.canonical_value * 100).toFixed(2)}%` : '—'}
            </strong>
            {volatility?.floor_applied && (
              <p className="caption" style={{ marginTop: '2px' }}>Floor applied</p>
            )}
          </div>

          <div style={{ padding: '14px 16px', border: '1px solid #e2e8f0', borderRadius: '6px' }}>
            <p className="eyebrow" style={{ marginBottom: '6px' }}>Relative Volume</p>
            <strong style={{ fontSize: '18px' }}>
              {volume.volume_ratio != null ? `${volume.volume_ratio.toFixed(2)}×` : '—'}
            </strong>
            <p className="caption" style={{ marginTop: '2px' }}>vs 20-session avg</p>
          </div>

          <div style={{ padding: '14px 16px', border: '1px solid #e2e8f0', borderRadius: '6px' }}>
            <p className="eyebrow" style={{ marginBottom: '6px' }}>20-Day Range</p>
            <strong style={{ fontSize: '15px' }}>
              {technical?.low_20d && technical?.high_20d
                ? `₹${technical.low_20d.toFixed(0)} – ₹${technical.high_20d.toFixed(0)}`
                : '—'}
            </strong>
          </div>

          <div style={{ padding: '14px 16px', border: '1px solid #e2e8f0', borderRadius: '6px' }}>
            <p className="eyebrow" style={{ marginBottom: '6px' }}>Dist. from 20d High</p>
            <strong style={{ fontSize: '18px' }}>
              {technical?.distance_from_20d_high_pct != null
                ? `${technical.distance_from_20d_high_pct.toFixed(2)}%`
                : '—'}
            </strong>
            {technical?.is_new_high && (
              <p className="caption" style={{ marginTop: '2px', color: '#16a34a' }}>New 20-day high</p>
            )}
          </div>

          <div style={{ padding: '14px 16px', border: '1px solid #e2e8f0', borderRadius: '6px' }}>
            <p className="eyebrow" style={{ marginBottom: '6px' }}>History</p>
            <strong style={{ fontSize: '18px' }}>
              {data.availability.available_history_count ?? data.history.length} obs
            </strong>
            <p className="caption" style={{ marginTop: '2px' }}>yfinance rows</p>
          </div>
        </div>
      </section>

      {/* Score Decomposition */}
      <section style={{ margin: '40px 0', borderTop: '1px solid #e2e8f0', paddingTop: '28px' }}>
        <p className="eyebrow" style={{ color: '#4f46e5' }}>Why This Attention Score?</p>
        <h2 style={{ fontSize: '18px', fontWeight: 600, margin: '6px 0 24px' }}>Score Breakdown</h2>

        <div className="analysis-explanation">
          <div>
            <h3 style={{ fontSize: '14px', fontWeight: 700, color: '#4f46e5', marginBottom: '16px', textTransform: 'uppercase', letterSpacing: '.08em' }}>
              Market Significance
            </h3>
            <strong style={{ display: 'block', fontSize: '40px', fontWeight: 700, letterSpacing: '-.04em', color: '#0f172a' }}>
              {attention?.objective_score.toFixed(1) ?? '—'}
            </strong>
            <p className="caption" style={{ margin: '6px 0 16px' }}>out of 80 · objective market facts</p>
            <p className="caption" style={{ lineHeight: '1.6' }}>
              Derived purely from real market data: price returns, volume anomaly, and technical position. Identical for every user.
            </p>
            {data.reasons.length > 0 && (
              <ReasonsList
                reasons={data.reasons.map(r => ({ ...r, message: sanitizeReason(r.message) }))}
                maxReasons={data.reasons.length}
              />
            )}
          </div>

          <div>
            <h3 style={{ fontSize: '14px', fontWeight: 700, color: '#0f172a', marginBottom: '16px', textTransform: 'uppercase', letterSpacing: '.08em' }}>
              Your Relevance
            </h3>
            <strong style={{ display: 'block', fontSize: '40px', fontWeight: 700, letterSpacing: '-.04em', color: '#4f46e5' }}>
              +{personal?.preference_fit.toFixed(1) ?? '—'}
            </strong>
            <p className="caption" style={{ margin: '6px 0 16px' }}>out of 35 · personal lens</p>
            <p className="caption" style={{ lineHeight: '1.6' }}>
              Based on your since-checked baseline and profile preferences (risk, style, horizon). Changes when you update your profile or mark as caught up.
            </p>
            <div style={{ marginTop: '20px', padding: '16px', background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: '6px' }}>
              <p className="eyebrow" style={{ marginBottom: '8px' }}>Final Attention Score</p>
              <strong style={{ fontSize: '32px', display: 'block', letterSpacing: '-.04em' }}>
                {final?.attention_score.toFixed(1) ?? '—'}
              </strong>
              <p className="caption" style={{ marginTop: '6px' }}>
                min({attention?.objective_score.toFixed(1)} + {personal?.preference_fit.toFixed(1)}, 100) = {final?.attention_score.toFixed(1)}
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Show the Math — collapsible, default closed */}
      <ShowMath data={data} />

      {/* Context */}
      <RelatedContext symbol={identity.symbol} />

      {/* Explicit Mark Caught-Up Action */}
      <footer className="analysis-actions">
        <div>
          <p className="muted" style={{ margin: 0 }}>
            Your last-checked baseline changes <em>only</em> when you explicitly click below.
          </p>
          <p className="caption" style={{ margin: '4px 0 0' }}>
            Opening this page is read-only. Your since-checked comparison is not altered.
          </p>
        </div>
        <button
          className="primary-action"
          disabled={marking || justViewed || observation.current_price === null}
          onClick={markViewed}
          style={{ padding: '14px 28px', fontSize: '14px', fontWeight: 600 }}
        >
          {marking ? 'Marking…' : justViewed ? 'Caught Up ✓' : 'Mark as caught up'}
        </button>
      </footer>
      {markError && <p role="alert" style={{ color: '#dc2626', marginTop: '12px' }}>{markError}</p>}
    </main>
  );
}
