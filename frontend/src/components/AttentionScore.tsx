interface AttentionScoreProps {
  objective: number;
  preference: number;
  final: number;
  level: 'LOW' | 'MEDIUM' | 'HIGH';
}

export default function AttentionScore({
  objective,
  preference,
  final,
  level,
}: AttentionScoreProps) {
  const levelColor = {
    HIGH: 'bg-gray-900 text-white',
    MEDIUM: 'border border-gray-400 text-gray-700',
    LOW: 'text-gray-400',
  };

  return (
    <div className="space-y-3">
      <div className="flex justify-between items-baseline">
        <span className="text-sm text-gray-600">Attention score</span>
        <span className={`text-2xl font-bold ${level === 'LOW' ? 'text-gray-400' : 'text-gray-900'}`}>
          {final.toFixed(0)}
        </span>
      </div>

      <div className="w-full bg-gray-200 h-1 rounded-full overflow-hidden">
        <div className="bg-gray-900 h-full" style={{ width: `${Math.min(final, 100)}%` }} />
      </div>

      <div className="flex items-center gap-2">
        <span className={`px-3 py-1 rounded-full text-xs font-semibold ${levelColor[level]}`}>
          {level}
        </span>
      </div>

      <div className="text-xs text-gray-500 space-y-1 pt-2 border-t">
        <div className="flex justify-between">
          <span>Objective</span>
          <span>{objective.toFixed(0)}</span>
        </div>
        <div className="flex justify-between">
          <span>Your preferences</span>
          <span className="text-gray-700">+{preference.toFixed(0)}</span>
        </div>
      </div>

      <p className="text-xs text-gray-500 pt-2 italic">
        This ranks attention. It's not a buy/sell recommendation.
      </p>
    </div>
  );
}
