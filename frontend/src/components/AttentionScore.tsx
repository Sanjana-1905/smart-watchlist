interface AttentionScoreProps {
  objective: number;
  preference: number;
  final: number;
  level: 'LOW' | 'MEDIUM' | 'HIGH';
}

export default function AttentionScore({ objective, preference, final, level }: AttentionScoreProps) {
  return (
    <div className="space-y-3">
      <dl className="space-y-2 text-sm text-slate-600">
        <div className="flex justify-between gap-3">
          <dt>Objective significance</dt><dd>{objective.toFixed(1)}</dd>
        </div>
        <div className="flex justify-between gap-3">
          <dt>Personal relevance</dt><dd>+{preference.toFixed(1)}</dd>
        </div>
        <div className="flex flex-wrap justify-between items-baseline gap-3 border-t border-slate-100 pt-3">
          <dt className="font-semibold text-slate-900">Final attention</dt>
          <dd className={`text-2xl font-bold ${level === 'LOW' ? 'text-slate-500' : 'text-slate-900'}`}>
            {final.toFixed(1)} <span className="text-xs font-semibold">{level}</span>
          </dd>
        </div>
      </dl>
      {objective + preference > 100 && <p className="text-xs text-slate-500">Final attention is capped at 100.</p>}
    </div>
  );
}
