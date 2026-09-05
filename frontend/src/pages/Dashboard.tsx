import { useState } from 'react';
import { Link } from 'react-router-dom';
import type { WatchlistResponse, BasicWatchlistItem } from '../types/market';
import AttentionPulse from '../components/AttentionPulse';
import TemporalLens, { type Lens } from '../components/TemporalLens';
import FocusedStockPreview from '../components/FocusedStockPreview';
import MarketDelta from '../components/MarketDelta';
import AddStockPanel from '../components/AddStockPanel';
import DataFreshness from '../components/DataFreshness';
import StarterMarketView from '../components/StarterMarketView';
import { useAuth } from '../context/AuthContext';

interface DashboardProps {
  data: WatchlistResponse | null;
  loading: boolean;
  error: string | null;
  onRefetch: () => void;
  membership?: BasicWatchlistItem[];
}

export default function Dashboard({ data, loading, error, onRefetch, membership }: DashboardProps) {
  const { user } = useAuth();
  const [lens, setLens] = useState<Lens>('since');
  const [selected, _setSelected] = useState<string | null>(null);
  const [showAdd, setShowAdd] = useState(false);
  const [showAllQuiet, setShowAllQuiet] = useState(false);

  if (loading) return (
    <main className="attention-page" role="status">
      <p className="caption" style={{ marginTop: '80px' }}>Loading your attention desk…</p>
    </main>
  );
  if (error) return (
    <main className="attention-page">
      <div role="alert" style={{ borderLeft: '2px solid #dc2626', paddingLeft: '16px', margin: '48px 0' }}>
        <p style={{ color: '#dc2626', fontWeight: 600 }}>{error}</p>
        <button
          className="text-action"
          style={{ marginTop: '12px' }}
          onClick={onRefetch}
        >
          Retry →
        </button>
      </div>
    </main>
  );
  if (!data) return (
    <main className="attention-page">
      <p className="caption" style={{ marginTop: '80px' }}>No market data available.</p>
    </main>
  );

  const members = membership ?? data.items.map(i => ({ ...i, added_at: '' }));
  const highItems = data.items.filter(i => i.attention_level === 'HIGH');
  const mediumItems = data.items.filter(i => i.attention_level === 'MEDIUM');
  const lowItems = data.items.filter(i => i.attention_level === 'LOW');
  const needsAttentionItems = [...highItems, ...mediumItems];

  const focused = data.items.find(i => i.symbol === selected) ?? needsAttentionItems[0] ?? data.items[0];

  // Empty watchlist → show market discovery
  if (members.length === 0) {
    return (
      <main className="attention-page">
        <div className="landscape-intro" style={{ marginBottom: '8px' }}>
          <div>
            <p className="eyebrow" style={{ color: '#4f46e5' }}>
              Attention Desk · {user?.display_name || user?.email}
            </p>
            <h1>Your Attention Desk<span className="intelligence-dot">.</span></h1>
            <p className="muted">No companies tracked yet. Add your first stock to begin.</p>
          </div>
        </div>
        <div className="market-line">
          <span>Market Status: <strong>{data.market_status}</strong></span>
        </div>
        <StarterMarketView onStockAdded={onRefetch} />
      </main>
    );
  }

  return (
    <main className="attention-page">
      {/* Header: Desk Identity & Status */}
      <div className="landscape-intro">
        <div>
          <p className="eyebrow" style={{ color: '#4f46e5' }}>
            Attention Desk · {user?.display_name || user?.email}
          </p>
          <h1>Market Attention<span className="intelligence-dot">.</span></h1>
          <p className="muted">
            What moved enough to deserve your closer inspection.
          </p>
        </div>
        <TemporalLens value={lens} onChange={setLens} />
      </div>

      <div className="market-line">
        <span>Market Status: <strong>{data.market_status}</strong></span>
        <span>{members.length} watched · {data.items.length} evaluated</span>
      </div>

      {/* Compact Attention Pulse (replaces giant spectrum visualization) */}
      {data.items.length > 0 && <AttentionPulse items={data.items} />}

      {/* No data yet for watched stocks */}
      {data.items.length === 0 && members.length > 0 && (
        <section className="caught-up" style={{ padding: '32px 0' }}>
          <p className="eyebrow">Awaiting Market Data</p>
          <h2>No snapshots available.</h2>
          <p>Your watched stocks are saved, but market history has not been ingested yet.</p>
        </section>
      )}

      {data.items.length > 0 && (
        <>
          {/* Focused Stock Spotlight */}
          {focused && <FocusedStockPreview item={focused} lens={lens} />}

          {/* Needs Your Attention */}
          <section style={{ marginTop: '40px' }}>
            <div className="section-heading">
              <div>
                <p className="eyebrow" style={{ color: '#4f46e5' }}>Ranked by Attention Score</p>
                <h2>
                  {needsAttentionItems.length === 0
                    ? 'Quiet Right Now'
                    : `Needs Your Attention (${needsAttentionItems.length})`}
                </h2>
              </div>
              <button className="text-action" onClick={() => setShowAdd(!showAdd)}>
                {showAdd ? 'Close' : '+ Add stock'}
              </button>
            </div>

            {showAdd && (
              <div className="stock-picker">
                <AddStockPanel watchlistedSymbols={members.map(i => i.symbol)} onAdded={onRefetch} />
              </div>
            )}

            {needsAttentionItems.length === 0 ? (
              <section className="caught-up" style={{ padding: '28px 0' }}>
                <span className="quiet-orbit" aria-hidden="true" style={{ color: '#16a34a', fontSize: '40px' }}>✓</span>
                <p className="eyebrow" style={{ color: '#16a34a', marginTop: '8px' }}>All Caught Up</p>
                <h3 style={{ fontSize: '22px', margin: '6px 0 12px' }}>No unusual movement right now.</h3>
                <p className="muted">
                  None of your tracked stocks are showing significant market movement.
                </p>
              </section>
            ) : (
              <div className="table-scroll" tabIndex={0} role="region" aria-label="Stocks needing attention">
                <table>
                  <thead>
                    <tr>
                      <th>Company</th>
                      <th>Price</th>
                      <th>Today</th>
                      <th>Since You Checked</th>
                      <th>Market Significance</th>
                      <th>Your Relevance</th>
                      <th>Attention</th>
                      <th>Why Now</th>
                    </tr>
                  </thead>
                  <tbody>
                    {needsAttentionItems.map(item => {
                      const unusual = item.reasons.find(r => r.type === 'UNUSUAL_RETURN');
                      const primaryReason = item.reasons[0]?.message ?? 'Within normal range';
                      const sinceCheckedLabel = item.since_last_view_pct == null
                        ? <span className="caption" style={{ color: '#94a3b8' }}>— First view</span>
                        : <MarketDelta value={item.since_last_view_pct} />;
                      return (
                        <tr key={item.symbol} style={{ background: selected === item.symbol ? '#eef2ff' : undefined }}>
                          <td>
                            <Link to={`/stock/${item.symbol}`} style={{ color: '#4f46e5', fontWeight: 700 }}>
                              {item.symbol}
                            </Link>
                            <small>{item.company_name}</small>
                            <DataFreshness freshness={item.freshness} compact />
                          </td>
                          <td style={{ fontWeight: 600 }}>₹{item.current_price.toFixed(2)}</td>
                          <td><MarketDelta value={item.session_change_pct} /></td>
                          <td>
                            {sinceCheckedLabel}
                          </td>
                          <td>
                            <strong style={{ fontSize: '14px' }}>{item.objective_score.toFixed(1)}</strong>
                            <small style={{ display: 'block', color: '#64748b' }}>/ 80</small>
                          </td>
                          <td>
                            <strong style={{ fontSize: '14px', color: '#4f46e5' }}>+{item.preference_fit.toFixed(1)}</strong>
                            <small style={{ display: 'block', color: '#64748b' }}>/ 35</small>
                          </td>
                          <td>
                            <span
                              style={{
                                display: 'inline-block',
                                padding: '3px 8px',
                                borderRadius: '4px',
                                background: item.attention_level === 'HIGH' ? '#bef264' : '#e2e8f0',
                                color: '#0f172a',
                                fontWeight: 700,
                                fontSize: '13px',
                              }}
                            >
                              {item.attention_score.toFixed(1)}
                            </span>
                            <small style={{ display: 'block', color: '#64748b' }}>{item.attention_level}</small>
                          </td>
                          <td style={{ fontSize: '12px', color: '#334155' }}>
                            {unusual
                              ? `${unusual.value}× normal move`
                              : primaryReason === 'No emitted signal' || primaryReason.includes('emitted')
                                ? 'Within normal range'
                                : primaryReason}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </section>

          {/* Quiet Right Now — compact, collapsible if large */}
          {lowItems.length > 0 && (
            <section style={{ marginTop: '48px', borderTop: '1px solid #e2e8f0', paddingTop: '28px' }}>
              <div className="section-heading" style={{ marginBottom: '16px' }}>
                <div>
                  <p className="eyebrow" style={{ color: '#94a3b8' }}>Within normal range</p>
                  <h3 style={{ fontSize: '16px', color: '#64748b', margin: '4px 0 0' }}>
                    Quiet Right Now ({lowItems.length})
                  </h3>
                </div>
              </div>
              <div className="table-scroll" tabIndex={0} role="region" aria-label="Quiet stocks">
                <table>
                  <thead>
                    <tr>
                      <th>Stock</th>
                      <th>Price</th>
                      <th>Today</th>
                      <th>Since You Checked</th>
                      <th>Attention</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(showAllQuiet ? lowItems : lowItems.slice(0, 5)).map(item => {
                      const sinceCheckedLabel = item.since_last_view_pct == null
                        ? <span className="caption" style={{ color: '#94a3b8' }}>— First view</span>
                        : <MarketDelta value={item.since_last_view_pct} />;
                      return (
                        <tr key={item.symbol} style={{ opacity: 0.75 }}>
                          <td>
                            <Link to={`/stock/${item.symbol}`} style={{ color: '#475569', fontWeight: 600 }}>
                              {item.symbol}
                            </Link>
                            <small>{item.company_name}</small>
                          </td>
                          <td>₹{item.current_price.toFixed(2)}</td>
                          <td><MarketDelta value={item.session_change_pct} /></td>
                          <td>{sinceCheckedLabel}</td>
                          <td style={{ color: '#64748b' }}>{item.attention_score.toFixed(1)}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
              {lowItems.length > 5 && (
                <button
                  className="text-action"
                  style={{ marginTop: '12px' }}
                  onClick={() => setShowAllQuiet(v => !v)}
                >
                  {showAllQuiet ? 'Show less ↑' : `Show all ${lowItems.length} quiet stocks ↓`}
                </button>
              )}
            </section>
          )}
        </>
      )}
    </main>
  );
}
