import { useEffect, useRef, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import type { Analytics } from '../types/analytics';
import { api } from '../services/api';
import AttentionScore from '../components/AttentionScore';
import DataFreshness from '../components/DataFreshness';
import ReasonsList from '../components/ReasonsList';
import TemporalLens, { type Lens } from '../components/TemporalLens';
import TemporalTimeline from '../components/TemporalTimeline';
import MarketDelta from '../components/MarketDelta';
import RelatedContext from '../components/RelatedContext';
import ShowMath from '../components/ShowMath';
import AnalysisChart from '../components/AnalysisChart';

export default function StockDetail() {
  const { symbol } = useParams<{ symbol: string }>();
  return <StockDetailContent key={symbol} symbol={symbol} />;
}
function StockDetailContent({ symbol }: { symbol: string | undefined }) {
  const [data, setData] = useState<Analytics | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [lens, setLens] = useState<Lens>('today');
  const [marking, setMarking] = useState(false);
  const [justViewed, setJustViewed] = useState(false);
  const [markError, setMarkError] = useState<string | null>(null);
  const markInFlight = useRef(false);
  useEffect(() => {
    let active = true;
    if (!symbol) { setError('Stock not found'); return; }
    api.getAnalytics(symbol).then(result => { if (active) setData(result); })
      .catch(err => { if (active) setError(err instanceof Error ? err.message : 'Failed to load analytics'); });
    return () => { active = false; };
  }, [symbol]);
  async function markViewed() {
    if (!symbol || markInFlight.current || justViewed) return;
    markInFlight.current = true; setMarking(true); setMarkError(null);
    try {
      await api.markViewed(symbol); setJustViewed(true);
      try { setData(await api.getAnalytics(symbol)); }
      catch (err) { setMarkError(`Caught-up state saved, but refresh failed: ${err instanceof Error ? err.message : 'Please reload.'}`); }
    } catch (err) { setMarkError(err instanceof Error ? err.message : 'Failed to mark as caught up'); }
    finally { markInFlight.current = false; setMarking(false); }
  }
  if (error) return <main className="analysis-page"><p role="alert">{error}</p><Link to="/">Back to attention</Link></main>;
  if (!data) return <main className="analysis-page" role="status">Loading analysis…</main>;
  const { identity, observation, temporal, volatility, volume, technical, attention, personal, final } = data;
  return <main className="analysis-page">
    <Link className="text-link" to="/">← Attention landscape</Link>
    <header className="analysis-heading"><div><p className="eyebrow">Analysis / {identity.exchange} · {identity.sector ?? 'Sector unavailable'}</p><h1>{identity.symbol}</h1><p>{identity.company_name}</p></div><TemporalLens value={lens} onChange={setLens}/></header>
    <div className="analysis-lead"><div><strong className="analysis-price">{observation.current_price === null ? 'Price unavailable' : `₹${observation.current_price.toFixed(2)}`}</strong><p><MarketDelta value={lens === 'today' ? temporal.session_change_pct : temporal.since_last_view_pct}/> · {lens === 'today' ? 'Today · vs previous close' : 'Since I looked · vs your last view'}</p></div>
      {final ? <div className="attention-total"><span className="eyebrow">Attention</span><strong>{final.attention_score}</strong><span>{final.attention_level}</span></div> : <p>Analytics unavailable</p>}
    </div>
    <DataFreshness freshness={observation.freshness}/><p className="caption">Market {observation.freshness.market_status?.toLowerCase()}</p>
    {!data.availability.analytics_available && <p className="availability-notice">Analytics unavailable: {data.availability.reason}</p>}
    <TemporalTimeline data={data} lens={lens}/>
    <AnalysisChart data={data} lens={lens}/>
    <section className="signal-map" aria-label="Signal map">{[
      ['Move', volatility ? `${volatility.unusualness_ratio.toFixed(2)}× normal` : 'Unavailable', 'Magnitude vs daily volatility'],
      ['Volume', volume.volume_ratio === null ? 'Unavailable' : `${volume.volume_ratio.toFixed(2)}× baseline`, `${volume.baseline_sample_count} prior sessions`],
      ['Trend', technical ? technical.is_new_high ? 'New closing high' : 'Within prior range' : 'Unavailable', technical ? `Previous ${technical.sample_count} sessions` : 'No historical baseline'],
      ['Since view', temporal.since_last_view_pct === null ? 'No baseline yet' : `${temporal.since_last_view_pct.toFixed(2)}%`, 'Vs your last saved price'],
    ].map(([label, value, hint]) => <div key={label}><p className="eyebrow">{label}</p><strong>{value}</strong><p className="caption">{hint}</p></div>)}</section>
    <section className="analysis-explanation"><div><h2>Why now?</h2><ReasonsList reasons={data.reasons} maxReasons={data.reasons.length}/></div><div>{attention && personal && final && <AttentionScore objective={attention.objective_score} preference={personal.preference_fit} final={final.attention_score} level={final.attention_level}/>}</div></section>
    <ShowMath data={data}/>
    <RelatedContext symbol={identity.symbol}/>
    <footer className="analysis-actions"><p className="muted">Your baseline changes only when you explicitly mark this stock as caught up.</p><button className="primary-action" disabled={marking || justViewed || observation.current_price === null} onClick={markViewed}>{marking ? 'Marking…' : justViewed ? 'Caught up' : 'Mark as caught up'}</button></footer>
    {markError && <p role="alert">{markError}</p>}
  </main>;
}
