import type { PriceSnapshot } from '../types/market';

interface PriceChartProps {
  data: PriceSnapshot[];
  height?: number;
}

export default function PriceChart({ data, height = 160 }: PriceChartProps) {
  const width = 600;
  const padding = 8;

  const closes = data.map((d) => Number(d.close));
  const min = Math.min(...closes);
  const max = Math.max(...closes);
  const range = max - min || 1;

  const points = closes.map((close, i) => {
    const x = padding + (i / (closes.length - 1)) * (width - padding * 2);
    const y = padding + (1 - (close - min) / range) * (height - padding * 2);
    return `${x},${y}`;
  });

  const isUp = closes[closes.length - 1] >= closes[0];
  const stroke = isUp ? '#16a34a' : '#dc2626';
  const areaPoints = `${padding},${height - padding} ${points.join(' ')} ${width - padding},${height - padding}`;

  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="w-full" preserveAspectRatio="none">
      <polygon points={areaPoints} fill={stroke} opacity={0.06} />
      <polyline points={points.join(' ')} fill="none" stroke={stroke} strokeWidth={2} />
    </svg>
  );
}
