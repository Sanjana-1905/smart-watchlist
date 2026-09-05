export default function MarketDelta({ value }: { value: number | null }) {
  return value == null ? <span className="muted">No baseline yet</span> : <span className={value >= 0 ? 'market-up' : 'market-down'}>{value >= 0 ? '+' : ''}{value.toFixed(2)}%</span>;
}
