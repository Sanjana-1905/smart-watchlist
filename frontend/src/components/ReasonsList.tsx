import type { Reason } from '../types/market';

interface ReasonsListProps {
  reasons: Reason[];
  maxReasons?: number;
}

export default function ReasonsList({ reasons, maxReasons = 3 }: ReasonsListProps) {
  const displayed = reasons.slice(0, maxReasons);

  if (displayed.length === 0) {
    return <p className="text-sm text-slate-500">No additional reasons available.</p>;
  }

  return (
    <ul className="space-y-1">
      {displayed.map((reason, idx) => (
        <li key={idx} className="flex gap-2 text-sm">
          <span className="text-slate-400 mt-0.5">•</span>
          <span className="text-slate-700 leading-snug">{reason.message}</span>
        </li>
      ))}
    </ul>
  );
}
