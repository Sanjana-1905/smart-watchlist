import { useState } from 'react';
import type { Analytics } from '../types/analytics';
import type { Lens } from './TemporalLens';
import AttentionScore from './AttentionScore';
const modes = ['Price', 'Volume', 'Volatility', 'Attention'] as const;
export default function AnalysisChart({ data, lens }: { data: Analytics; lens: Lens }) {
  const [mode, setMode] = useState<typeof modes[number]>('Price');
  const [range, setRange] = useState('all');
  const lastTime = Date.parse(data.history.at(-1)?.timestamp ?? '');
  const history = data.history.filter(p => range === 'all' || Date.parse(p.timestamp) >= lastTime - 7 * 86400000);
  const start = Date.parse(history[0]?.timestamp ?? '');
  const end = Date.parse(history.at(-1)?.timestamp ?? '');
  const x = (time: number) => 60 + (time - start) / (end - start || 1) * 820;
  const values = history.map(p => mode === 'Volume' ? p.volume : p.close);
  const baseline = mode === 'Volume' ? data.volume.baseline_average_volume : lens === 'today' ? data.temporal.previous_session_close : data.temporal.last_viewed_price;
  const allValues = baseline === null ? values : [...values, baseline];
  const min = mode === 'Volume' ? 0 : Math.min(...allValues) * .995;
  const max = Math.max(...allValues) * 1.005;
  const y = (v: number) => 260 - (v - min) / (max - min || 1) * 220;
  const viewed = Date.parse(data.temporal.last_viewed_at ?? '');
  return <section className="analysis-plot">
    <div className="plot-controls"><div className="mode-controls" role="group" aria-label="Analysis mode">{modes.map(m => <button key={m} aria-pressed={m === mode} onClick={() => setMode(m)}>{m}</button>)}</div>
      {(mode === 'Price' || mode === 'Volume') && <label>History <select aria-label="History range" value={range} onChange={e => setRange(e.target.value)}><option value="all">All available</option><option value="week">Last 7 days</option></select></label>}
    </div>
    <h2>{mode === 'Price' ? 'How has the observed price changed?' : mode === 'Volume' ? 'How active is this session?' : mode === 'Volatility' ? 'How unusual is today’s move?' : 'What contributes to your attention score?'}</h2>
    {(mode === 'Price' || mode === 'Volume') && (history.length ? <>
      <div className="chart-scroll" tabIndex={0} role="region" aria-label={`${mode} chart, horizontally scrollable`}><svg viewBox="0 0 920 310" role="img" aria-label={`${mode} over actual observation timestamps. ${history.length} observations. Latest ${values.at(-1)}. Reference ${baseline ?? 'unavailable'}.`}>
        {[min, (min + max) / 2, max].map(v => <g key={v}><line x1="60" x2="880" y1={y(v)} y2={y(v)} stroke="var(--line)"/><text x="55" y={y(v)} textAnchor="end">{mode === 'Volume' ? `${(v / 1e6).toFixed(1)}m` : v.toFixed(0)}</text></g>)}
        {baseline !== null && <line x1="60" x2="880" y1={y(baseline)} y2={y(baseline)} stroke="var(--intelligence)" strokeDasharray="5 5"/>}
        {mode === 'Price' ? <polyline points={history.map(p => `${x(Date.parse(p.timestamp))},${y(p.close)}`).join(' ')} fill="none" stroke="var(--ink)" strokeWidth="2"/> : history.map(p => <line key={p.timestamp} x1={x(Date.parse(p.timestamp))} x2={x(Date.parse(p.timestamp))} y1="260" y2={y(p.volume)} stroke="var(--intelligence)" strokeWidth="5"><title>{new Date(p.timestamp).toLocaleString()} · {p.volume.toLocaleString()}</title></line>)}
        {mode === 'Price' && viewed >= start && viewed <= end && <g><line x1={x(viewed)} x2={x(viewed)} y1="25" y2="265" stroke="var(--intelligence)" strokeDasharray="3 4"/><text x={Math.min(x(viewed), 730)} y="18">Last view ₹{data.temporal.last_viewed_price}</text></g>}
        <circle cx={x(end)} cy={y(values.at(-1)!)} r="5" fill="var(--intelligence)"/>
        <text x="60" y="290">{new Date(start).toLocaleDateString()}</text><text x="880" y="290" textAnchor="end">{new Date(end).toLocaleDateString()}</text>
      </svg></div>
      <p className="caption">{mode === 'Volume' ? `Latest-observation cumulative volumes; polls are not summed. Dashed line: prior ${data.volume.baseline_sample_count} sessions’ average.` : `Dashed reference: ${lens === 'today' ? 'previous session close' : 'your persisted last-view price'}. Lines connect observed points; gaps contain no additional observations.`}</p>
      <details className="chart-values"><summary>View observation values</summary><div className="table-scroll"><table><thead><tr><th>Observed at</th><th>Price</th><th>Volume</th><th>Source</th></tr></thead><tbody>{history.map(p => <tr key={p.timestamp}><td>{new Date(p.timestamp).toLocaleString()}</td><td>₹{p.close.toFixed(2)}</td><td>{p.volume.toLocaleString()}</td><td>{p.source}</td></tr>)}</tbody></table></div></details>
    </> : <p>Market history unavailable.</p>)}
    {mode === 'Volatility' && (data.volatility ? <div className="volatility-view"><strong>{data.volatility.unusualness_ratio.toFixed(2)}× normal</strong><NormalRange data={data}/><p>Today: {data.temporal.session_change_pct?.toFixed(2)}% · canonical daily volatility: ±{(data.volatility.canonical_value * 100).toFixed(3)}%</p><p className="caption">Population standard deviation of {data.volatility.sample_count} session returns, including the current session. {data.volatility.floor_applied ? 'The 0.5% volatility floor applies.' : 'The 0.5% floor does not apply.'} This describes observed variability, not a forecast.</p></div> : <p>Volatility unavailable.</p>)}
    {mode === 'Attention' && (data.attention && data.personal && data.final ? <AttentionScore objective={data.attention.objective_score} preference={data.personal.preference_fit} final={data.final.attention_score} level={data.final.attention_level}/> : <p>Attention analytics unavailable.</p>)}
  </section>;
}

function NormalRange({data}:{data:Analytics}) {
  const normal=data.volatility!.canonical_value, current=data.temporal.session_return!;
  const extent=Math.max(normal*2,Math.abs(current)*1.2);
  const x=(v:number)=>300+v/extent*260;
  return <svg className="normal-range" viewBox="0 0 600 100" role="img" aria-label={`Current return ${current*100} percent versus normal range plus or minus ${normal*100} percent`}>
    <line x1="40" x2="560" y1="45" y2="45" stroke="var(--line)"/>
    <rect x={x(-normal)} y="32" width={x(normal)-x(-normal)} height="26" fill="var(--color-intelligence-soft)"/>
    <line x1="300" x2="300" y1="25" y2="65" stroke="var(--muted)"/>
    <circle cx={x(current)} cy="45" r="7" fill="var(--ink)"/>
    <text x="300" y="88" textAnchor="middle" fill="var(--muted)" fontSize="12">Shaded band: ±1 canonical daily volatility · dot: current return</text>
  </svg>;
}
