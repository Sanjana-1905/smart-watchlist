import { useState } from 'react';
import { Link } from 'react-router-dom';
import type { WatchlistResponse, BasicWatchlistItem } from '../types/market';
import AttentionLandscape from '../components/AttentionLandscape';
import TemporalLens, { type Lens } from '../components/TemporalLens';
import FocusedStockPreview from '../components/FocusedStockPreview';
import MarketDelta from '../components/MarketDelta';
import AddStockPanel from '../components/AddStockPanel';
import DataFreshness from '../components/DataFreshness';

interface DashboardProps {
  data: WatchlistResponse | null; loading: boolean; error: string | null; onRefetch: () => void;
  membership?: BasicWatchlistItem[];
}
export default function Dashboard({ data, loading, error, onRefetch, membership }: DashboardProps) {
  const [lens, setLens] = useState<Lens>('since');
  const [selected, setSelected] = useState<string | null>(null);
  const [showAdd, setShowAdd] = useState(false);
  if (loading) return <main className="state-message">Loading your attention landscape…</main>;
  if (error) return <main className="state-message" role="alert">{error}</main>;
  if (!data) return <main className="state-message">No data available.</main>;
  const meaningful = data.items.filter(i => i.attention_level !== 'LOW');
  const focused = data.items.find(i => i.symbol === selected) ?? meaningful[0];
  const members = membership ?? data.items.map(i => ({ ...i, added_at: '' }));
  const quiet = data.items.filter(i => i.attention_level === 'LOW').length;
  const pulse: [string, number][] = [
    ['Meaningful', meaningful.length], ['High', data.items.filter(i => i.attention_level === 'HIGH').length],
    ['Medium', data.items.filter(i => i.attention_level === 'MEDIUM').length], ['Quiet', quiet],
    ['Volume signals', data.items.filter(i => i.reasons.some(r => r.type === 'VOLUME')).length],
    ['New highs', data.items.filter(i => i.reasons.some(r => r.type === 'NEW_HIGH')).length],
  ];
  return <main className="attention-page">
    <div className="landscape-intro"><div><p className="eyebrow">The market is global. Attention is personal.</p><h1>Your attention<span className="intelligence-dot">.</span></h1><p className="muted">What changed enough to deserve a closer look.</p></div><TemporalLens value={lens} onChange={setLens} /></div>
    <div className="market-line"><span>Market {data.market_status}</span><span>{members.length} stocks watched · {data.items.length} with analysis</span></div>
    {data.items.length > 0 && <AttentionLandscape items={data.items} selected={focused?.symbol ?? null} onSelect={setSelected} lens={lens} />}
    <dl className="market-pulse">{pulse.map(([label, count]) => <div key={label}><dt>{label}</dt><dd>{count}</dd></div>)}</dl>
    {members.length === 0 ? <section className="caught-up"><p className="eyebrow">Start with what matters to you</p><h2>Your attention starts here.</h2><p>Add stocks to remember what changes between your visits.</p><button className="analysis-link" onClick={() => setShowAdd(true)}>Add a stock ↗</button></section> : data.items.length === 0 ? <section className="caught-up"><p className="eyebrow">Awaiting market observations</p><h2>Analytics unavailable.</h2><p>Your watched companies are listed below. There is not enough market history to assess attention yet.</p></section> : meaningful.length === 0 && <section className="caught-up"><span className="quiet-orbit" aria-hidden="true">○</span><p className="eyebrow">You're caught up</p><h2>A little less to look at.</h2><p>No analyzed watchlist stocks have medium or high attention right now.</p><p className="caption">Stocks without sufficient data are listed separately below. Smart Watchlist will stay quiet until something deserves it.</p></section>}
    {focused && <FocusedStockPreview item={focused} lens={lens} />}
    <section id="watchlist" className="secondary-watchlist"><div className="section-heading"><div><p className="eyebrow">Your collection</p><h2>Watchlist</h2></div><button className="text-action" onClick={() => setShowAdd(!showAdd)}>{showAdd ? 'Close stock picker' : '+ Add stock'}</button></div>
      {showAdd && <div className="stock-picker"><AddStockPanel watchlistedSymbols={members.map(i => i.symbol)} onAdded={onRefetch} /></div>}
      <div className="table-scroll" tabIndex={0} role="region" aria-label="Watchlist, scroll for all columns"><table><thead><tr><th>Stock</th><th>Price</th><th>Today</th><th>Since I looked</th><th>Unusualness</th><th>Attention</th></tr></thead><tbody>{members.map(member => {
        const item = data.items.find(i => i.symbol === member.symbol);
        const unusual = item?.reasons.find(r => r.type === 'UNUSUAL_RETURN');
        return <tr key={member.symbol}><td><Link to={`/stock/${member.symbol}`}>{member.symbol}</Link><small>{member.company_name}</small>{item && <DataFreshness freshness={item.freshness} />}</td>{item ? <><td>₹{item.current_price.toFixed(2)}</td><td><MarketDelta value={item.session_change_pct} /></td><td><MarketDelta value={item.since_last_view_pct} /></td><td>{unusual ? `${unusual.value}× normal` : 'No emitted signal'}</td><td>{item.attention_score.toFixed(1)} <small>{item.attention_level}</small></td></> : <td colSpan={5}>Analytics unavailable · watchlist membership saved</td>}</tr>;
      })}</tbody></table></div>
    </section>
  </main>;
}
