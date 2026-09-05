import { Link } from 'react-router-dom';
import type { WatchlistItem } from '../types/market';
import type { Lens } from './TemporalLens';
import MarketDelta from './MarketDelta';
import ReasonsList from './ReasonsList';
import AttentionScore from './AttentionScore';
import DataFreshness from './DataFreshness';
export default function FocusedStockPreview({ item, lens }: { item: WatchlistItem; lens: Lens }) {
  const signals = item.reasons.filter(r => ['UNUSUAL_RETURN', 'VOLUME', 'NEW_HIGH'].includes(r.type));
  return <section className="focus-surface" aria-label={`Focused analysis for ${item.symbol}`}>
    <div className="focus-identity"><p className="eyebrow">In focus / {item.attention_level}</p><h2>{item.symbol}</h2><p className="muted">{item.company_name}</p><p className="focus-price">₹{item.current_price.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</p>
      <div className="focus-delta"><MarketDelta value={lens === 'today' ? item.session_change_pct : item.since_last_view_pct} /><span>{lens === 'today' ? 'Today · vs previous close' : 'Since I looked · vs my last view'}</span></div>
      <p className="other-delta">{lens === 'today' ? 'Since I looked' : 'Today'} <MarketDelta value={lens === 'today' ? item.since_last_view_pct : item.session_change_pct} /></p>
      <Link className="analysis-link" to={`/stock/${item.symbol}`}>Analyze {item.symbol} <span aria-hidden="true">↗</span></Link>
    </div>
    <div className="focus-evidence"><div className="signal-strip">{signals.map(r => <div key={r.type}><span className="eyebrow">{r.type === 'UNUSUAL_RETURN' ? 'Move' : r.type === 'NEW_HIGH' ? 'Trend' : 'Volume'}</span><strong>{r.type === 'NEW_HIGH' ? 'New high' : `${r.value}× normal`}</strong></div>)}</div><h3 className="eyebrow">Why now?</h3><ReasonsList reasons={item.reasons} maxReasons={item.reasons.length} /></div>
    <div className="focus-composition"><AttentionScore objective={item.objective_score} preference={item.preference_fit} final={item.attention_score} level={item.attention_level} /><div className="mt-6"><DataFreshness freshness={item.freshness} /></div></div>
  </section>;
}
