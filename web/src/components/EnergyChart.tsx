import type { EnergyUpdate } from '../types/deliberation';

interface EnergyChartProps {
  history: EnergyUpdate[];
}

export function EnergyChart({ history }: EnergyChartProps) {
  if (history.length === 0) {
    return (
      <div className="energy-chart">
        <h2 className="panel-title">Energy</h2>
        <div className="energy-empty">Waiting for data...</div>
      </div>
    );
  }

  const latest = history[history.length - 1];
  const energyPct = (latest.energy * 100).toFixed(0);

  // Energy color: green > 0.6, yellow 0.3-0.6, red < 0.3
  const energyColor = latest.energy > 0.6
    ? '#22c55e'
    : latest.energy > 0.3
      ? '#f59e0b'
      : '#ef4444';

  // SVG sparkline
  const width = 280;
  const height = 80;
  const padding = 4;
  const maxPoints = 40;
  const points = history.slice(-maxPoints);

  const xScale = (i: number) => padding + (i / Math.max(points.length - 1, 1)) * (width - 2 * padding);
  const yScale = (v: number) => height - padding - v * (height - 2 * padding);

  const pathData = points
    .map((p, i) => `${i === 0 ? 'M' : 'L'} ${xScale(i).toFixed(1)} ${yScale(p.energy).toFixed(1)}`)
    .join(' ');

  // Area fill
  const areaData = pathData + ` L ${xScale(points.length - 1).toFixed(1)} ${yScale(0).toFixed(1)} L ${xScale(0).toFixed(1)} ${yScale(0).toFixed(1)} Z`;

  return (
    <div className="energy-chart">
      <h2 className="panel-title">Energy</h2>

      {/* Current energy bar */}
      <div className="energy-bar-wrapper">
        <div className="energy-bar-label">
          <span style={{ color: energyColor, fontWeight: 700 }}>{energyPct}%</span>
        </div>
        <div className="energy-bar-track">
          <div
            className="energy-bar-fill"
            style={{
              width: `${energyPct}%`,
              backgroundColor: energyColor,
            }}
          />
          {/* Threshold marker at 20% */}
          <div className="energy-threshold-marker" style={{ left: '20%' }} />
        </div>
      </div>

      {/* Sparkline chart */}
      <svg className="energy-sparkline" viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none">
        {/* Threshold line */}
        <line
          x1={padding} y1={yScale(0.2)} x2={width - padding} y2={yScale(0.2)}
          stroke="#ef4444" strokeWidth="0.5" strokeDasharray="4 2" opacity="0.5"
        />
        {/* Area */}
        <path d={areaData} fill={energyColor} opacity="0.1" />
        {/* Line */}
        <path d={pathData} fill="none" stroke={energyColor} strokeWidth="1.5" />
        {/* Current point */}
        <circle
          cx={xScale(points.length - 1)} cy={yScale(latest.energy)}
          r="3" fill={energyColor}
        />
      </svg>

      {/* Component breakdown */}
      <div className="energy-components">
        {Object.entries(latest.components).map(([key, value]) => (
          <div key={key} className="energy-component">
            <span className="component-label">{key}</span>
            <div className="component-bar-track">
              <div
                className="component-bar-fill"
                style={{ width: `${(value as number) * 100}%` }}
              />
            </div>
            <span className="component-value">{((value as number) * 100).toFixed(0)}%</span>
          </div>
        ))}
      </div>
    </div>
  );
}
