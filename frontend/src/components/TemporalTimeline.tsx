import type { Analytics } from '../types/analytics';
import type { Lens } from './TemporalLens';
export default function TemporalTimeline({ data, lens }: { data: Analytics; lens: Lens }) {
  const t = data.temporal;
  const points = [
    { name: 'Previous close', time: t.previous_session_observed_at, price: t.previous_session_close, active: lens === 'today' },
    { name: 'You looked', time: t.last_viewed_at, price: t.last_viewed_price, active: lens === 'since' },
    { name: 'Latest observation', time: data.observation.observed_at, price: data.observation.current_price, active: true },
  ].filter(p => p.time && p.price !== null).sort((a, b) => Date.parse(a.time!) - Date.parse(b.time!));
  return <section className="temporal-section" aria-label="Chronological comparison timeline">
    <p className="eyebrow">Your reference points · chronological order</p>
    <ol className="temporal-timeline">{points.map(p => <li key={p.name} className={p.active ? 'active' : ''}>
      <span className="timeline-dot" /><span className="eyebrow">{p.name}</span><strong>₹{p.price!.toFixed(2)}</strong>
      <time dateTime={p.time!}>{new Date(p.time!).toLocaleString()}</time>
    </li>)}</ol>
    {!t.last_viewed_at && <p className="muted">No baseline yet. Mark as caught up to save your reference point.</p>}
    <p className="caption">Last view is your saved price and time, not an additional market observation. Spacing does not represent elapsed time.</p>
  </section>;
}
