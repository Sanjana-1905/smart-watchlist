import { useEffect, useState } from 'react';
import { api, type StockContext } from '../services/api';
export default function RelatedContext({ symbol }: { symbol: string }) {
  const [data,setData]=useState<StockContext|null>(null),[failed,setFailed]=useState(false);
  useEffect(()=>{let active=true;const controller=new AbortController();const timeout=setTimeout(()=>controller.abort(),8000);
    setData(null);setFailed(false);
    api.getContext(symbol,controller.signal).then(d=>{if(active)setData(d);}).catch(()=>{if(active)setFailed(true);}).finally(()=>clearTimeout(timeout));
    return()=>{active=false;clearTimeout(timeout);controller.abort();};
  },[symbol]);
  return <section className="related-context"><p className="eyebrow">Research, in context</p><h2>Related context</h2>
    {failed || data?.status==='UNAVAILABLE' ? <p role="status">Related context is temporarily unavailable. Your stock analysis is still available.</p> : !data ? <p role="status">Loading related context…</p> : <><p className="caption">{data.provenance} Links verified {data.verified_at}.</p>{data.items.length ? <ul>{data.items.map(item=><li key={item.url}><a href={item.url} target="_blank" rel="noopener noreferrer">{item.headline} <span aria-label="opens in a new tab">↗</span></a><p className="caption">{item.source} · <time dateTime={item.published_date}>{item.published_date}</time></p></li>)}</ul> : <p>No curated context available for {symbol}.</p>}</>}
    <p className="caption">Context is shown for research and is not used in the current attention score.</p>
  </section>;
}
