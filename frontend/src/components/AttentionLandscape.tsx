import type { WatchlistItem } from '../types/market';
import type { Lens } from './TemporalLens';
import MarketDelta from './MarketDelta';

export default function AttentionLandscape({ items, selected, onSelect, lens }: {
  items: WatchlistItem[]; selected: string | null; onSelect: (symbol: string) => void; lens: Lens;
}) {
  // Exact score positions; vertical lanes resolve collisions without changing scores.
  const lanes: number[] = [];
  const markers = [...items].sort((a, b) => a.attention_score - b.attention_score || a.symbol.localeCompare(b.symbol)).map(item => {
    let lane = lanes.findIndex(score => item.attention_score - score >= 19);
    if (lane < 0) lane = lanes.length;
    lanes[lane] = item.attention_score;
    return { item, lane };
  });
  return <section aria-label="Attention landscape" className="landscape-section">
    <div className="rail-heading"><span>Quieter</span><span>Needs attention ↗</span></div>
    <div className="landscape-scroll" tabIndex={0} role="region" aria-label="Attention spectrum; scroll horizontally on small screens">
      <div className="landscape" style={{ height: Math.max(230, lanes.length * 110 + 70) }}>
        <div className="spectrum-axis" aria-hidden="true">{[0, 25, 50, 75, 100].map(n => <span key={n} style={{ left: `${n}%` }}>{n}</span>)}</div>
        {markers.map(({ item, lane }) => <button key={item.symbol} className={`attention-marker ${item.attention_level.toLowerCase()}`} style={{ left: `${8 + item.attention_score * .84}%`, top: 22 + lane * 110 }} aria-pressed={selected === item.symbol} onClick={() => onSelect(item.symbol)} aria-label={`${item.symbol}, attention ${item.attention_score.toFixed(1)}, ${item.attention_level}. Focus stock`}>
          <span className="marker-dot" aria-hidden="true" style={{ width: 10 + item.attention_score / 5, height: 10 + item.attention_score / 5 }} />
          <strong>{item.symbol}</strong><span className="marker-score">{item.attention_score.toFixed(1)} <small>{item.attention_level}</small></span>
          <span className="marker-delta"><MarketDelta value={lens === 'today' ? item.session_change_pct : item.since_last_view_pct} /></span>
        </button>)}
      </div>
    </div>
    <p className="caption">Position = final attention. {lens === 'today' ? 'Deltas compare with the previous close.' : 'Deltas compare with your last view.'} Select a stock to focus. The lens does not change scores.</p>
  </section>;
}
