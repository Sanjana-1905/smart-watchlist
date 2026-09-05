import type { Freshness } from '../types/market';

export function sourceLabel(source: string): string {
  const labels: Record<string, string> = {
    mock: 'Mock data',
    yfinance: 'Yahoo Finance',
    yfinance_fixture: 'Yahoo Finance historical fixture',
  };
  return labels[source] ?? (source || 'Unknown source');
}

export default function DataFreshness({ freshness }: { freshness: Freshness }) {
  const observed = new Date(freshness.observed_at);
  const validTime = freshness.status !== 'UNAVAILABLE' && Number.isFinite(observed.getTime());
  return (
    <div className="text-xs text-slate-500 leading-relaxed break-words">
      <p>{sourceLabel(freshness.source)} · {freshness.status}</p>
      <p>
        {validTime ? <>Observed <time dateTime={freshness.observed_at}>{observed.toLocaleString([], {
          day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit', timeZoneName: 'short',
        })}</time></> : 'Observation time unavailable'}
      </p>
    </div>
  );
}
