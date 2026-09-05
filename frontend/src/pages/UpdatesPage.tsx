import { useEffect, useState } from 'react';
import { api, type Stock, type StockContext } from '../services/api';

export default function UpdatesPage() {
  const [stocks, setStocks] = useState<Stock[]>([]);
  const [selectedSymbol, setSelectedSymbol] = useState<string>('RELIANCE');
  const [contextData, setContextData] = useState<StockContext | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    api.getAllStocks()
      .then(s => {
        if (active && s.length > 0) {
          setStocks(s);
        }
      })
      .catch(err => {
        if (active) setError(err.message);
      });
    return () => { active = false; };
  }, []);

  useEffect(() => {
    let active = true;
    const controller = new AbortController();
    setLoading(true);
    setError(null);

    api.getContext(selectedSymbol, controller.signal)
      .then(data => {
        if (active) setContextData(data);
      })
      .catch(err => {
        if (active) setError(err instanceof Error ? err.message : 'Context unavailable');
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
      controller.abort();
    };
  }, [selectedSymbol]);

  return (
    <main className="explore-page">
      <p className="eyebrow">Market Research & Background</p>
      <h1>Company Updates</h1>
      <p className="muted">
        Curated background context and reference releases for catalog stocks.
      </p>

      <div className="explore-search" style={{ padding: '24px 0' }}>
        <label htmlFor="company-select" style={{ maxWidth: '400px' }}>
          Select Stock Company
          <select
            id="company-select"
            value={selectedSymbol}
            onChange={e => setSelectedSymbol(e.target.value)}
          >
            {stocks.map(s => (
              <option key={s.symbol} value={s.symbol}>
                {s.symbol} — {s.company_name}
              </option>
            ))}
          </select>
        </label>
      </div>

      <section style={{ borderTop: '1px solid #e2e8f0', paddingTop: '32px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', flexWrap: 'wrap', gap: '16px', marginBottom: '24px' }}>
          <h2>Updates for {selectedSymbol}</h2>
          {contextData && (
            <span className="caption">
              Source: {contextData.provenance} {contextData.verified_at ? `· Verified ${contextData.verified_at}` : ''}
            </span>
          )}
        </div>

        <p className="caption" style={{ marginBottom: '24px', background: '#f8fafc', padding: '12px 16px', borderRadius: '4px', borderLeft: '3px solid #4f46e5' }}>
          <strong>Honesty Notice:</strong> Context items are reference background materials. Context operates on a separate provider boundary and is <em>not</em> used in calculating objective or personal attention scores.
        </p>

        {loading ? (
          <p role="status">Loading company context…</p>
        ) : error || !contextData || contextData.status === 'UNAVAILABLE' ? (
          <p className="availability-notice">
            No recent verified company updates available for {selectedSymbol}. Market analytics and scoring remain available.
          </p>
        ) : contextData.items.length === 0 ? (
          <p className="availability-notice">
            No recent verified company updates available for {selectedSymbol}.
          </p>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            {contextData.items.map((item, idx) => (
              <article
                key={idx}
                style={{
                  padding: '20px',
                  border: '1px solid #e2e8f0',
                  borderRadius: '6px',
                  background: '#ffffff',
                }}
              >
                <h3 style={{ fontSize: '16px', fontWeight: 600, margin: '0 0 8px' }}>
                  <a
                    href={item.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    style={{ color: '#0f172a', textDecoration: 'none' }}
                  >
                    {item.headline} <span style={{ color: '#4f46e5' }}>↗</span>
                  </a>
                </h3>
                <div style={{ display: 'flex', gap: '16px', fontSize: '12px', color: '#64748b' }}>
                  <span>Source: <strong>{item.source}</strong></span>
                  <span>Published: <time dateTime={item.published_date}>{item.published_date}</time></span>
                </div>
              </article>
            ))}
          </div>
        )}
      </section>
    </main>
  );
}
