import { AlertTriangle, Info } from 'lucide-react';
import type { CalibrationReport } from '@/types/platform';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { cn } from '@/lib/utils';

interface CalibrationGaugeProps {
  report: CalibrationReport;
}

function accuracyColor(accuracy: number): string {
  if (accuracy >= 0.7) return '#22C55E';
  if (accuracy >= 0.5) return '#F59E0B';
  return '#EF4444';
}

function accuracyTextClass(accuracy: number): string {
  if (accuracy >= 0.7) return 'text-success';
  if (accuracy >= 0.5) return 'text-warning';
  return 'text-destructive';
}

export function CalibrationGauge({ report }: CalibrationGaugeProps) {
  const pct = Math.round(report.accuracy * 100);
  const color = accuracyColor(report.accuracy);

  return (
    <div className="space-y-6">
      {/* Not meaningful notice */}
      {!report.is_meaningful && (
        <div className="flex items-start gap-3 rounded-md border border-border-default bg-bg-elevated p-4">
          <Info className="h-5 w-5 shrink-0 text-text-muted mt-0.5" />
          <div>
            <p className="text-sm font-medium text-text-primary">
              Not yet meaningful
            </p>
            <p className="text-sm text-text-secondary mt-0.5">
              This agent has too few evaluations for statistically meaningful
              calibration. Results shown are preliminary.
            </p>
          </div>
        </div>
      )}

      {/* Main accuracy */}
      <Card>
        <CardHeader>
          <CardTitle>Overall Accuracy</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-end gap-3">
            <span
              className={cn(
                'text-4xl font-mono font-bold',
                accuracyTextClass(report.accuracy),
              )}
            >
              {pct}%
            </span>
            <span className="text-sm text-text-muted mb-1">accuracy</span>
          </div>
          <Progress
            value={pct}
            color={color}
            className="mt-3 h-3"
          />

          {/* Stats row */}
          <div className="mt-4 grid grid-cols-2 sm:grid-cols-4 gap-4">
            <StatItem label="Total" value={report.total_evaluations} />
            <StatItem label="Correct" value={report.correct} color="#22C55E" />
            <StatItem label="Incorrect" value={report.incorrect} color="#EF4444" />
            <StatItem label="Partial" value={report.partial} color="#F59E0B" />
          </div>
        </CardContent>
      </Card>

      {/* Domain accuracy */}
      {Object.keys(report.domain_accuracy).length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Domain Accuracy</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {Object.entries(report.domain_accuracy).map(([domain, acc]) => {
              const domainPct = Math.round(acc * 100);
              const domainColor = accuracyColor(acc);
              return (
                <div key={domain}>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm text-text-primary">{domain}</span>
                    <span
                      className={cn(
                        'text-sm font-mono font-medium',
                        accuracyTextClass(acc),
                      )}
                    >
                      {domainPct}%
                    </span>
                  </div>
                  <Progress value={domainPct} color={domainColor} />
                </div>
              );
            })}
          </CardContent>
        </Card>
      )}

      {/* Systematic biases */}
      {report.systematic_biases.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Systematic Biases</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-2">
              {report.systematic_biases.map((bias) => (
                <Badge key={bias} variant="warning" className="gap-1">
                  <AlertTriangle className="h-3 w-3" />
                  {bias}
                </Badge>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

function StatItem({
  label,
  value,
  color,
}: {
  label: string;
  value: number;
  color?: string;
}) {
  return (
    <div className="text-center">
      <p
        className="text-xl font-semibold font-mono"
        style={color ? { color } : undefined}
      >
        {value}
      </p>
      <p className="text-xs text-text-muted">{label}</p>
    </div>
  );
}
