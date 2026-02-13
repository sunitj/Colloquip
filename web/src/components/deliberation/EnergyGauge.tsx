import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  ReferenceLine,
  ResponsiveContainer,
} from 'recharts';
import { Progress } from '@/components/ui/progress';
import type { EnergyUpdate } from '@/types/deliberation';

interface EnergyGaugeProps {
  energyHistory: EnergyUpdate[];
}

function energyColor(value: number): string {
  if (value > 0.6) return '#22C55E';
  if (value > 0.3) return '#F59E0B';
  return '#EF4444';
}

const ACCENT = '#60A5FA';

interface ChartPayload {
  turn: number;
  energy: number;
}

function CustomTooltip({
  active,
  payload,
  label,
}: {
  active?: boolean;
  payload?: Array<{ value: number }>;
  label?: number;
}) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-md border border-border-default bg-bg-overlay px-3 py-2 text-text-primary shadow-lg">
      <p className="text-xs text-text-muted">Turn {label}</p>
      <p className="text-sm font-semibold">{(payload[0].value as number).toFixed(3)}</p>
    </div>
  );
}

export function EnergyGauge({ energyHistory }: EnergyGaugeProps) {
  const current = energyHistory.length > 0
    ? energyHistory[energyHistory.length - 1]
    : null;

  const currentEnergy = current?.energy ?? 0;
  const color = energyColor(currentEnergy);

  const chartData: ChartPayload[] = energyHistory.map((e) => ({
    turn: e.turn,
    energy: e.energy,
  }));

  return (
    <div className="space-y-4">
      {/* Current energy number */}
      <div className="text-center">
        <span
          className="text-3xl font-mono font-bold"
          style={{ color }}
        >
          {currentEnergy.toFixed(2)}
        </span>
        <p className="text-xs text-text-muted mt-1">Conversation Energy</p>
      </div>

      {/* Progress bar */}
      <Progress value={currentEnergy * 100} color={color} className="h-2" />

      {/* Area chart */}
      {chartData.length > 1 && (
        <div className="h-[140px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartData} margin={{ top: 4, right: 4, bottom: 0, left: -20 }}>
              <CartesianGrid
                strokeDasharray="3 3"
                stroke="rgba(255,255,255,0.03)"
                vertical={false}
              />
              <XAxis
                dataKey="turn"
                tick={{ fill: 'var(--color-text-muted)', fontSize: 11 }}
                axisLine={false}
                tickLine={false}
              />
              <YAxis
                domain={[0, 1]}
                tick={{ fill: 'var(--color-text-muted)', fontSize: 11 }}
                axisLine={false}
                tickLine={false}
              />
              <RechartsTooltip content={<CustomTooltip />} />
              <ReferenceLine
                y={0.2}
                stroke="#EF4444"
                strokeDasharray="4 4"
                strokeOpacity={0.6}
              />
              <Area
                type="monotone"
                dataKey="energy"
                stroke={ACCENT}
                fill={ACCENT}
                fillOpacity={0.2}
                strokeWidth={2}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Component bars */}
      {current?.components && (
        <div className="space-y-2">
          {(
            [
              { key: 'novelty' as const, label: 'Novelty', color: '#A855F7' },
              { key: 'disagreement' as const, label: 'Disagreement', color: '#EF4444' },
              { key: 'questions' as const, label: 'Questions', color: '#F59E0B' },
              { key: 'staleness' as const, label: 'Staleness', color: '#6B7280' },
            ] as const
          ).map(({ key, label, color: barColor }) => (
            <div key={key} className="flex items-center gap-2">
              <span className="text-xs text-text-muted w-24 shrink-0">{label}</span>
              <Progress
                value={current.components[key] * 100}
                color={barColor}
                className="h-1.5 flex-1"
              />
              <span className="text-xs text-text-muted w-8 text-right">
                {Math.round(current.components[key] * 100)}%
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
