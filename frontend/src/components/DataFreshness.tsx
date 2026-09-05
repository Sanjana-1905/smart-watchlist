import type { Freshness } from '../types/market';

export function sourceLabel(source: string): string {
  const labels: Record<string, string> = {
    mock: 'Historical data',
    yfinance: 'Yahoo Finance',
    yfinance_fixture: 'Historical fixture',
  };
  return labels[source] ?? (source || 'Data');
}

function formatFreshnessDate(observed_at: string): string {
  const dt = new Date(observed_at);
  if (!Number.isFinite(dt.getTime())) return '';
  return dt.toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })
    + ', '
    + dt.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', hour12: false });
}

interface DataFreshnessProps {
  freshness: Freshness;
  compact?: boolean;
}

/**
 * compact=true → single subtle line in table rows
 * compact=false (default) → full multi-line provenance for detail pages
 */
export default function DataFreshness({ freshness, compact = false }: DataFreshnessProps) {
  const observed = new Date(freshness.observed_at);
  const validTime = freshness.status !== 'UNAVAILABLE' && Number.isFinite(observed.getTime());
  const dateStr = validTime ? formatFreshnessDate(freshness.observed_at) : null;

  if (compact) {
    if (!dateStr) return null;
    return (
      <small style={{ display: 'block', color: '#94a3b8', fontSize: '10px', marginTop: '2px' }}>
        Updated {dateStr}
      </small>
    );
  }

  return (
    <div style={{ fontSize: '11px', color: '#94a3b8', lineHeight: '1.5' }}>
      {dateStr && (
        <span>
          Updated <time dateTime={freshness.observed_at}>{dateStr}</time>
          {' '}· {sourceLabel(freshness.source)}
        </span>
      )}
    </div>
  );
}
