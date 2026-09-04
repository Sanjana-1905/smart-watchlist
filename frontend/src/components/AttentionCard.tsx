import type { WatchlistItem } from '../types/market';
import ReasonsList from './ReasonsList';
import AttentionScore from './AttentionScore';

interface AttentionCardProps {
  item: WatchlistItem;
}

export default function AttentionCard({ item }: AttentionCardProps) {
  const isPositive = item.session_change_pct >= 0;

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-6 space-y-4">
      <div className="flex justify-between items-start">
        <div>
          <p className="text-sm text-gray-600">{item.company_name}</p>
          <h3 className="text-2xl font-bold text-gray-900">{item.symbol}</h3>
        </div>
        <span className={`px-3 py-1 rounded-full text-xs font-semibold ${
          item.attention_level === 'HIGH'
            ? 'bg-gray-900 text-white'
            : item.attention_level === 'MEDIUM'
            ? 'border border-gray-400 text-gray-700'
            : 'text-gray-400'
        }`}>
          {item.attention_level}
        </span>
      </div>

      <div className="space-y-2">
        <p className="text-3xl font-bold text-gray-900">₹{item.current_price.toFixed(2)}</p>
        <div className="flex gap-4 text-sm">
          <div>
            <p className="text-gray-600">Today</p>
            <p className={`font-semibold ${isPositive ? 'text-green-600' : 'text-red-600'}`}>
              {isPositive ? '+' : ''}{item.session_change_pct.toFixed(2)}%
            </p>
          </div>
          {item.since_last_view_pct !== null && (
            <div>
              <p className="text-gray-600">Since you checked</p>
              <p className={`font-semibold ${item.since_last_view_pct >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                {item.since_last_view_pct >= 0 ? '+' : ''}{item.since_last_view_pct.toFixed(2)}%
              </p>
            </div>
          )}
        </div>
      </div>

      <div className="pt-3 border-t">
        <p className="text-xs font-semibold text-gray-900 uppercase tracking-wide mb-3">Why it surfaced</p>
        <ReasonsList reasons={item.reasons} maxReasons={3} />
      </div>

      <div className="pt-3 border-t">
        <AttentionScore objective={item.objective_score} preference={item.preference_fit} final={item.attention_score} level={item.attention_level} />
      </div>

      <div className="flex justify-between items-center text-xs text-gray-500 pt-2">
        <span>{item.freshness.status} · {item.freshness.age_minutes} min ago</span>
      </div>
    </div>
  );
}
