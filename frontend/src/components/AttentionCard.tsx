import { Link } from 'react-router-dom';
import DataFreshness from './DataFreshness';
import type { WatchlistItem } from '../types/market';
import ReasonsList from './ReasonsList';
import AttentionScore from './AttentionScore';

interface AttentionCardProps {
  item: WatchlistItem;
}

export default function AttentionCard({ item }: AttentionCardProps) {
  const isPositive = item.session_change_pct >= 0;

  const borderTopColor = item.attention_level === 'HIGH'
    ? 'border-t-slate-900'
    : item.attention_level === 'MEDIUM'
    ? 'border-t-slate-400'
    : 'border-t-transparent';

  return (
    <article className={`bg-white border border-slate-200 border-t-[3px] ${borderTopColor} rounded-lg p-5 flex flex-col h-full min-w-0 shadow-sm`}>
      <div className="flex justify-between items-start mb-4">
        <div>
          <h3 className="text-xl font-bold text-slate-900 leading-none"><Link to={`/stock/${item.symbol}`} className="rounded hover:underline">{item.symbol}<span className="sr-only"> details</span></Link></h3>
          <p className="text-xs text-slate-500 mt-1 truncate max-w-[150px]">{item.company_name}</p>
        </div>
        <span className={`px-2.5 py-1 rounded text-[11px] font-bold tracking-wider ${
          item.attention_level === 'HIGH' ? 'bg-slate-900 text-white' :
          item.attention_level === 'MEDIUM' ? 'border border-slate-300 text-slate-600 bg-slate-50' :
          'text-slate-400'
        }`}>
          {item.attention_level}
        </span>
      </div>

      <div className="mb-5">
        <p className="text-2xl font-bold text-slate-900">₹{item.current_price.toFixed(2)}</p>
      </div>

      <div className="grid grid-cols-2 gap-4 mb-5">
        <div>
          <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-0.5">Today</p>
          <p className={`text-sm font-semibold ${isPositive ? 'text-green-600' : 'text-red-600'}`}>
            {isPositive ? '+' : ''}{item.session_change_pct.toFixed(2)}%
          </p>
          <p className="text-xs text-slate-500 mt-1">vs previous close</p>
        </div>
        <div>
            <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-0.5">Since checked</p>
            {item.since_last_view_pct !== null ? <p className={`text-sm font-semibold ${item.since_last_view_pct >= 0 ? 'text-green-600' : 'text-red-600'}`}>
              {item.since_last_view_pct >= 0 ? '+' : ''}{item.since_last_view_pct.toFixed(2)}%
            </p> : <p className="text-sm text-slate-500">No baseline yet</p>}
            <p className="text-xs text-slate-500 mt-1">vs your last view</p>
          </div>
      </div>

      <div className="mb-6 flex-grow">
        <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-2">Why now?</p>
        <ReasonsList reasons={item.reasons} maxReasons={3} />
      </div>

      <div className="pt-4 border-t border-slate-100 mt-auto">
        <AttentionScore objective={item.objective_score} preference={item.preference_fit} final={item.attention_score} level={item.attention_level} />
      </div>
      <div className="mt-4"><DataFreshness freshness={item.freshness} /></div>
    </article>
  );
}
