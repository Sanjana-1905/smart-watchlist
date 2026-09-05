import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../services/api';
import type { Stock, BasicWatchlistItem } from '../types/market';
import type { Analytics } from '../types/analytics';
import DataFreshness from '../components/DataFreshness';
const sectorName = (sector: string | null) => ({Technology:'IT',Automobile:'Auto',Consumer:'FMCG'}[sector ?? ''] ?? sector ?? 'Sector unavailable');
export default function ExplorePage() {
  const [stocks, setStocks] = useState<Stock[]>([]), [members, setMembers] = useState<BasicWatchlistItem[]>([]);
  const [loading, setLoading] = useState(true), [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState(''), [sector, setSector] = useState('All sectors'), [page, setPage] = useState(0);
  const [analytics, setAnalytics] = useState<Record<string, Analytics | 'error'>>({});
  const [pending, setPending] = useState<string | null>(null);
  const inFlight = useRef(false);
  useEffect(() => { let active = true; Promise.all([api.getAllStocks(), api.getWatchlist()]).then(([s,m]) => { if(active){setStocks(s);setMembers(m);} }).catch(e => {if(active)setError(e.message);}).finally(()=>{if(active)setLoading(false);}); return()=>{active=false;}; }, []);
  const sectors = [...new Set(stocks.map(s=>sectorName(s.sector)))].sort();
  const filtered = stocks.filter(s => (sector === 'All sectors' || sectorName(s.sector) === sector) && `${s.symbol} ${s.company_name}`.toLowerCase().includes(query.trim().toLowerCase())).sort((a,b)=>a.symbol.localeCompare(b.symbol));
  const visible = filtered.slice(page*8,page*8+8);
  const symbolsKey = visible.map(s=>s.symbol).join(',');
  useEffect(()=>{let active=true; const symbols = symbolsKey ? symbolsKey.split(',') : []; for(const symbol of symbols){api.getAnalytics(symbol).then(d=>{if(active)setAnalytics(prev=>({...prev,[symbol]:d}));}).catch(()=>{if(active)setAnalytics(prev=>({...prev,[symbol]:'error'}));});} return()=>{active=false;};},[symbolsKey]);
  async function toggle(stock: Stock) {
    if(inFlight.current)return;
    inFlight.current=true;setPending(stock.symbol);setError(null);
    try {
      if(members.some(m=>m.symbol===stock.symbol)) await api.removeWatchlistStock(stock.symbol); else await api.addWatchlistStock(stock.symbol);
      setMembers(await api.getWatchlist());
    } catch(e){setError(e instanceof Error ? e.message : 'Could not update watchlist');}
    finally{inFlight.current=false;setPending(null);}
  }
  return <main className="explore-page"><p className="eyebrow">Expand your field of view</p><h1>Explore the market.</h1><p className="muted">Choose what you follow. Attention stays personal.</p>
    <div className="explore-search"><label htmlFor="stock-search">Search stocks<input id="stock-search" type="search" value={query} placeholder="Symbol or company" onChange={e=>{setQuery(e.target.value);setPage(0);}}/></label><label htmlFor="sector-filter">Sector<select id="sector-filter" value={sector} onChange={e=>{setSector(e.target.value);setPage(0);}}><option>All sectors</option>{sectors.map(s=><option key={s}>{s}</option>)}</select></label></div>
    {error && <p role="alert">{error}</p>}{loading ? <p role="status">Loading stock catalog…</p> : <>
      <div className="section-heading"><h2>Browse stocks</h2><p className="caption">{filtered.length} of {stocks.length} companies · {members.length} watched</p></div>
      <p className="caption">Observation dates and sources are shown per company. Catalog entries without imported history have no price or attention score.</p>
      <div className="explore-list">{visible.map(stock=>{const a=analytics[stock.symbol],watched=members.some(m=>m.symbol===stock.symbol);return <article key={stock.symbol} className="explore-entry"><div><p className="eyebrow">{sectorName(stock.sector)} / {stock.exchange}</p><Link className="explore-symbol" to={`/stock/${encodeURIComponent(stock.symbol)}`}>{stock.symbol} ↗</Link><p className="muted">{stock.company_name}</p></div><div className="explore-observation">{!a ? <p role="status">Loading observation…</p> : a==='error' ? <p>Analytics unavailable · unable to load</p> : <>{a.observation.current_price===null ? <p>Analytics unavailable · no market history</p> : <><strong>₹{a.observation.current_price.toFixed(2)}</strong><DataFreshness freshness={a.observation.freshness}/>{a.volatility && <p className="caption">{a.volatility.unusualness_ratio.toFixed(2)}× normal move · latest available session</p>}{!a.availability.analytics_available && <p className="caption">Analytics unavailable · insufficient sessions</p>}</>}</>}</div><button className="secondary-action" disabled={pending!==null} onClick={()=>toggle(stock)} aria-label={`${watched?'Remove':'Add'} ${stock.symbol} ${watched?'from':'to'} watchlist`}>{pending===stock.symbol?'Saving…':watched?'− Remove':'+ Watch'}</button></article>;})}</div>
      {!visible.length && <p className="availability-notice">No companies match your search.</p>}
      <nav className="explore-pagination" aria-label="Catalog pages"><button disabled={page===0} onClick={()=>setPage(p=>p-1)}>← Previous</button><span>Page {page+1} of {Math.max(1,Math.ceil(filtered.length/8))}</span><button disabled={(page+1)*8>=filtered.length} onClick={()=>setPage(p=>p+1)}>Next →</button></nav>
    </>}
  </main>;
}
