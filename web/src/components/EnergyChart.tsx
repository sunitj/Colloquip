import { useRef, useState } from 'react';
import type { EnergyUpdate } from '../types/deliberation';

interface EnergyChartProps {
  history: EnergyUpdate[];
}

export function EnergyChart({ history }: EnergyChartProps) {
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null);
  const svgRef = useRef<SVGSVGElement>(null);

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

  const colorForEnergy = (e: number) =>
    e > 0.6 ? '#22c55e' : e > 0.3 ? '#f59e0b' : '#ef4444';

  const energyColor = colorForEnergy(latest.energy);

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

  const areaData = pathData + ` L ${xScale(points.length - 1).toFixed(1)} ${yScale(0).toFixed(1)} L ${xScale(0).toFixed(1)} ${yScale(0).toFixed(1)} Z`;

  // Detect energy spikes (>0.1 jump from previous)
  const spikeIndices: number[] = [];
  for (let i = 1; i < points.length; i++) {
    if (points[i].energy - points[i - 1].energy > 0.1) {
      spikeIndices.push(i);
    }
  }

  const hoveredData = hoveredIndex !== null ? points[hoveredIndex] : null;

  // Tooltip position from SVG coordinates
  const tooltipStyle = (): React.CSSProperties => {
    if (hoveredIndex === null || !svgRef.current) return { display: 'none' };
    const svgRect = svgRef.current.getBoundingClientRect();
    const xFrac = hoveredIndex / Math.max(points.length - 1, 1);
    const xPx = xFrac * svgRect.width;
    const flipLeft = xFrac > 0.6;
    return {
      top: -4,
      ...(flipLeft ? { right: svgRect.width - xPx + 8 } : { left: xPx + 8 }),
    };
  };

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
            style={{ width: `${energyPct}%`, backgroundColor: energyColor }}
          />
          <div className="energy-threshold-marker" style={{ left: '20%' }} />
        </div>
      </div>

      {/* Sparkline chart with hover */}
      <div className="energy-chart-wrapper">
        <svg
          ref={svgRef}
          className="energy-sparkline"
          viewBox={`0 0 ${width} ${height}`}
          preserveAspectRatio="none"
        >
          {/* Threshold line */}
          <line
            x1={padding} y1={yScale(0.2)} x2={width - padding} y2={yScale(0.2)}
            stroke="#ef4444" strokeWidth="0.5" strokeDasharray="4 2" opacity="0.5"
          />
          {/* Area */}
          <path d={areaData} fill={energyColor} opacity="0.1" />
          {/* Line */}
          <path d={pathData} fill="none" stroke={energyColor} strokeWidth="1.5" />

          {/* Energy spike markers */}
          {spikeIndices.map(i => (
            <polygon
              key={`spike-${i}`}
              className="energy-spike-marker"
              points={`${xScale(i)},${yScale(points[i].energy) - 6} ${xScale(i) - 3},${yScale(points[i].energy) - 1} ${xScale(i) + 3},${yScale(points[i].energy) - 1}`}
            />
          ))}

          {/* Hover guide line */}
          {hoveredIndex !== null && (
            <line
              x1={xScale(hoveredIndex)} y1={yScale(points[hoveredIndex].energy)}
              x2={xScale(hoveredIndex)} y2={yScale(0)}
              stroke={colorForEnergy(points[hoveredIndex].energy)}
              strokeWidth="0.5" strokeDasharray="2 2" opacity="0.6"
            />
          )}

          {/* Current point */}
          <circle
            cx={xScale(points.length - 1)} cy={yScale(latest.energy)}
            r="3" fill={energyColor}
          />

          {/* Hovered point (highlighted) */}
          {hoveredIndex !== null && (
            <circle
              cx={xScale(hoveredIndex)} cy={yScale(points[hoveredIndex].energy)}
              r="4" fill={colorForEnergy(points[hoveredIndex].energy)}
              stroke={colorForEnergy(points[hoveredIndex].energy)}
              strokeWidth="2" strokeOpacity="0.3"
            />
          )}

          {/* Invisible hit targets for hover */}
          {points.map((_, i) => (
            <circle
              key={i}
              cx={xScale(i)} cy={yScale(points[i].energy)}
              r="8" fill="transparent"
              onMouseEnter={() => setHoveredIndex(i)}
              onMouseLeave={() => setHoveredIndex(null)}
              style={{ cursor: 'crosshair' }}
            />
          ))}
        </svg>

        {/* Tooltip */}
        {hoveredData && (
          <div className="energy-tooltip" style={tooltipStyle()}>
            <div className="energy-tooltip-header">Turn {hoveredData.turn}</div>
            <div className="energy-tooltip-value" style={{ color: colorForEnergy(hoveredData.energy) }}>
              {(hoveredData.energy * 100).toFixed(0)}%
            </div>
            <div className="energy-tooltip-components">
              {Object.entries(hoveredData.components).map(([key, value]) => (
                <div key={key} className="energy-tooltip-row">
                  <span className="energy-tooltip-label">{key}</span>
                  <div className="energy-tooltip-bar">
                    <div
                      className="energy-tooltip-bar-fill"
                      style={{ width: `${(value as number) * 100}%` }}
                    />
                  </div>
                  <span className="energy-tooltip-val">{((value as number) * 100).toFixed(0)}%</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Component breakdown (latest) */}
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
