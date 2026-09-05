interface MarketDeltaProps {
  value: number | null | undefined;
  large?: boolean;
}

export default function MarketDelta({ value, large = false }: MarketDeltaProps) {
  if (value == null) {
    return <span className="muted" style={{ fontSize: large ? '18px' : undefined }}>—</span>;
  }
  const style = large ? { fontSize: '28px', fontWeight: 600, letterSpacing: '-.02em' } : {};
  return (
    <span className={value >= 0 ? 'market-up' : 'market-down'} style={style}>
      {value >= 0 ? '+' : ''}{value.toFixed(2)}%
    </span>
  );
}
