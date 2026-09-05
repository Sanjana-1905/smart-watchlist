import { useState } from 'react';
import type { AnalyticsHistoryPoint } from '../types/analytics';

interface PriceChartProps {
  history: AnalyticsHistoryPoint[];
  lastViewedPrice?: number | null;
  lastViewedAt?: string | null;
  companyName?: string;
  symbol?: string;
}

type RangeOption = '1M' | '3M' | '6M' | '1Y';

export default function PriceChart({
  history,
  lastViewedPrice,
  lastViewedAt,
  symbol,
}: PriceChartProps) {
  const [range, setRange] = useState<RangeOption>('1Y');
  const [hoverIndex, setHoverIndex] = useState<number | null>(null);

  if (!history || history.length === 0) {
    return (
      <div className="availability-notice">
        Price history unavailable for this stock.
      </div>
    );
  }

  // Filter history based on range selection
  const lastTime = new Date(history[history.length - 1].timestamp).getTime();
  const rangeDays: Record<RangeOption, number> = {
    '1M': 30,
    '3M': 90,
    '6M': 180,
    '1Y': 365,
  };

  const cutoff = lastTime - rangeDays[range] * 86400000;
  const filtered = history.filter(p => new Date(p.timestamp).getTime() >= cutoff);
  const dataPoints = filtered.length >= 2 ? filtered : history;

  const startMs = new Date(dataPoints[0].timestamp).getTime();
  const endMs = new Date(dataPoints[dataPoints.length - 1].timestamp).getTime();
  const msSpan = endMs - startMs || 1;

  const closes = dataPoints.map(p => p.close);
  const minPrice = Math.min(...closes);
  const maxPrice = Math.max(...closes);
  const priceSpan = maxPrice - minPrice || 1;

  // Chart dimensions
  const svgWidth = 800;
  const svgHeight = 240;
  const padLeft = 60;
  const padRight = 20;
  const padTop = 20;
  const padBottom = 35;
  const plotW = svgWidth - padLeft - padRight;
  const plotH = svgHeight - padTop - padBottom;

  const getX = (ts: string) => {
    const t = new Date(ts).getTime();
    return padLeft + ((t - startMs) / msSpan) * plotW;
  };

  const getY = (val: number) => {
    return padTop + plotH - ((val - minPrice) / priceSpan) * plotH;
  };

  const pointsString = dataPoints
    .map(p => `${getX(p.timestamp).toFixed(1)},${getY(p.close).toFixed(1)}`)
    .join(' ');

  const hoveredPoint = hoverIndex !== null ? dataPoints[hoverIndex] : dataPoints[dataPoints.length - 1];

  const firstClose = dataPoints[0].close;
  const latestClose = dataPoints[dataPoints.length - 1].close;
  const netChange = latestClose - firstClose;
  const netChangePct = (netChange / firstClose) * 100;
  const isUp = netChange >= 0;

  return (
    <div style={{ marginTop: '24px', borderTop: '1px solid #e2e8f0', paddingTop: '24px' }}>
      {/* Header controls & stats */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px', marginBottom: '16px' }}>
        <div>
          <span className="eyebrow" style={{ color: '#4f46e5' }}>Price History ({symbol})</span>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: '12px', marginTop: '4px' }}>
            <strong style={{ fontSize: '24px', fontWeight: 600, color: '#0f172a' }}>
              ₹{hoveredPoint.close.toFixed(2)}
            </strong>
            <span style={{ fontSize: '13px', fontWeight: 600, color: isUp ? '#16a34a' : '#dc2626' }}>
              {netChange >= 0 ? '+' : ''}{netChangePct.toFixed(2)}% ({range})
            </span>
            <span style={{ fontSize: '11px', color: '#64748b' }}>
              {new Date(hoveredPoint.timestamp).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })}
            </span>
          </div>
        </div>

        {/* Range selectors */}
        <div style={{ display: 'flex', gap: '4px', background: '#f1f5f9', padding: '4px', borderRadius: '6px' }}>
          {(['1M', '3M', '6M', '1Y'] as RangeOption[]).map(r => (
            <button
              key={r}
              type="button"
              onClick={() => { setRange(r); setHoverIndex(null); }}
              style={{
                padding: '6px 12px',
                fontSize: '12px',
                fontWeight: 600,
                borderRadius: '4px',
                border: 0,
                background: range === r ? '#ffffff' : 'transparent',
                color: range === r ? '#4f46e5' : '#64748b',
                cursor: 'pointer',
                boxShadow: range === r ? '0 1px 3px rgba(0,0,0,0.1)' : 'none',
              }}
            >
              {r}
            </button>
          ))}
        </div>
      </div>

      {/* SVG Price Chart */}
      <div style={{ width: '100%', overflowX: 'auto' }}>
        <svg
          viewBox={`0 0 ${svgWidth} ${svgHeight}`}
          style={{ width: '100%', minWidth: '600px', display: 'block' }}
        >
          {/* Horizontal Grid lines */}
          {[minPrice, (minPrice + maxPrice) / 2, maxPrice].map((val, idx) => {
            const yPos = getY(val);
            return (
              <g key={idx}>
                <line x1={padLeft} x2={svgWidth - padRight} y1={yPos} y2={yPos} stroke="#e2e8f0" strokeDasharray="3 3" />
                <text x={padLeft - 8} y={yPos + 4} textAnchor="end" fontSize="10" fill="#94a3b8">
                  ₹{val.toFixed(0)}
                </text>
              </g>
            );
          })}

          {/* Saved Last-View Baseline Line */}
          {lastViewedPrice && lastViewedPrice >= minPrice && lastViewedPrice <= maxPrice && (
            <g>
              <line
                x1={padLeft}
                x2={svgWidth - padRight}
                y1={getY(lastViewedPrice)}
                y2={getY(lastViewedPrice)}
                stroke="#4f46e5"
                strokeDasharray="4 4"
                strokeWidth="1.5"
              />
              <text x={svgWidth - padRight - 5} y={getY(lastViewedPrice) - 6} textAnchor="end" fontSize="10" fill="#4f46e5" fontWeight="600">
                Last Saved: ₹{lastViewedPrice.toFixed(2)}
              </text>
            </g>
          )}

          {/* Area Fill under Price Line */}
          <polygon
            points={`${padLeft},${padTop + plotH} ${pointsString} ${svgWidth - padRight},${padTop + plotH}`}
            fill={isUp ? '#16a34a' : '#dc2626'}
            opacity="0.06"
          />

          {/* Main Price Polyline */}
          <polyline
            points={pointsString}
            fill="none"
            stroke={isUp ? '#16a34a' : '#dc2626'}
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          />

          {/* Interactive Data Points */}
          {dataPoints.map((p, i) => {
            const cx = getX(p.timestamp);
            const cy = getY(p.close);
            const isSelected = hoverIndex === i || (hoverIndex === null && i === dataPoints.length - 1);

            return (
              <g key={i} style={{ cursor: 'pointer' }} onMouseEnter={() => setHoverIndex(i)}>
                <circle cx={cx} cy={cy} r={isSelected ? 5 : 2} fill={isSelected ? '#4f46e5' : isUp ? '#16a34a' : '#dc2626'} />
              </g>
            );
          })}

          {/* Date Axis Labels */}
          <text x={padLeft} y={svgHeight - 8} fontSize="10" fill="#94a3b8">
            {new Date(dataPoints[0].timestamp).toLocaleDateString('en-IN', { month: 'short', day: 'numeric', year: 'numeric' })}
          </text>
          <text x={svgWidth - padRight} y={svgHeight - 8} textAnchor="end" fontSize="10" fill="#94a3b8">
            {new Date(dataPoints[dataPoints.length - 1].timestamp).toLocaleDateString('en-IN', { month: 'short', day: 'numeric', year: 'numeric' })}
          </text>
        </svg>
      </div>

      <p className="caption" style={{ marginTop: '8px', color: '#64748b' }}>
        Chronological yfinance price observations ({dataPoints.length} bars displayed). Dashed purple line indicates your persisted last-view baseline {lastViewedAt ? `(set ${new Date(lastViewedAt).toLocaleDateString('en-IN')})` : ''}.
      </p>
    </div>
  );
}
