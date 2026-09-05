export type Lens = 'today' | 'since';
export default function TemporalLens({ value, onChange }: { value: Lens; onChange: (value: Lens) => void }) {
  return <div className="temporal-control" role="group" aria-label="Temporal lens">
    <button aria-pressed={value === 'today'} onClick={() => onChange('today')}>Today<span>vs previous close</span></button>
    <button aria-pressed={value === 'since'} onClick={() => onChange('since')}>Since I looked<span>vs my last-view baseline</span></button>
  </div>;
}
