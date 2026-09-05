import type { WatchlistItem } from '../types/market';
import MarketDelta from './MarketDelta';

interface AttentionPulseProps {
  items: WatchlistItem[];
}

export default function AttentionPulse({ items }: AttentionPulseProps) {
  const needsAttention = items.filter(i => i.attention_level === 'HIGH' || i.attention_level === 'MEDIUM');
  const quiet = items.filter(i => i.attention_level === 'LOW');

  const topMover = items.length > 0
    ? [...items].sort((a, b) => Math.abs(b.session_change_pct) - Math.abs(a.session_change_pct))[0]
    : null;

  const topMoverUnusual = topMover?.reasons.find(r => r.type === 'UNUSUAL_RETURN');

  return (
    <div
      aria-label="Attention Pulse summary"
      style={{
        background: '#f8fafc',
        border: '1px solid #e2e8f0',
        borderRadius: '8px',
        padding: '20px 24px',
        margin: '24px 0 32px',
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
        gap: '24px',
        alignItems: 'center',
      }}
    >
      <div>
        <span className="eyebrow" style={{ color: '#4f46e5', marginBottom: '8px', display: 'block' }}>
          Attention Pulse
        </span>
        <div style={{ display: 'flex', gap: '24px', alignItems: 'baseline' }}>
          <div>
            <span style={{ fontSize: '11px', color: '#64748b', display: 'block' }}>NEEDS ATTENTION</span>
            <strong style={{ fontSize: '28px', color: '#0f172a', fontWeight: 700 }}>
              {needsAttention.length}
            </strong>
          </div>
          <div>
            <span style={{ fontSize: '11px', color: '#64748b', display: 'block' }}>WATCHING</span>
            <strong style={{ fontSize: '28px', color: '#0f172a', fontWeight: 700 }}>
              {items.length}
            </strong>
          </div>
          <div>
            <span style={{ fontSize: '11px', color: '#64748b', display: 'block' }}>QUIET</span>
            <strong style={{ fontSize: '28px', color: '#64748b', fontWeight: 600 }}>
              {quiet.length}
            </strong>
          </div>
        </div>
      </div>

      {topMover && (
        <div style={{ borderLeft: '1px solid #cbd5e1', paddingLeft: '24px' }}>
          <span className="eyebrow" style={{ color: '#64748b', marginBottom: '6px', display: 'block' }}>
            Top Mover Today
          </span>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: '12px', flexWrap: 'wrap' }}>
            <strong style={{ fontSize: '18px', color: '#4f46e5', fontWeight: 700 }}>
              {topMover.symbol}
            </strong>
            <span style={{ fontSize: '14px', fontWeight: 600 }}>
              ₹{topMover.current_price.toFixed(2)}
            </span>
            <MarketDelta value={topMover.session_change_pct} />
            {topMoverUnusual && (
              <span style={{ fontSize: '12px', color: '#475569', background: '#eef2ff', padding: '2px 8px', borderRadius: '4px' }}>
                {topMoverUnusual.value}× normal
              </span>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
