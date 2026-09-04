import type { Reason } from '../types/market';

interface ReasonsListProps {
  reasons: Reason[];
  maxReasons?: number;
}

export default function ReasonsList({ reasons, maxReasons = 3 }: ReasonsListProps) {
  const displayed = reasons.slice(0, maxReasons);

  if (displayed.length === 0) {
    return <p className="text-xs text-gray-500">No notable factors.</p>;
  }

  return (
    <div className="space-y-2">
      {displayed.map((reason, idx) => (
        <div key={idx} className="flex gap-2 text-sm">
          <span className="text-gray-400 font-semibold">
            {String(idx + 1).padStart(2, '0')}
          </span>
          <div>
            <p className="text-gray-700 font-medium capitalize">
              {reason.type.split('_').join(' ').toLowerCase()}
            </p>
            <p className="text-gray-600 text-xs">{reason.message}</p>
          </div>
        </div>
      ))}
    </div>
  );
}
