import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { useMissionProgress } from '@/hooks/dashboards';
import type { ObjectiveProgress } from '@/types/dashboards';

interface GoalProgressTrackerProps {
  subredditName: string;
}

function statusBadge(p: ObjectiveProgress) {
  if (p.qualitative) return <Badge variant="outline">Qualitative</Badge>;
  switch (p.status) {
    case 'met':
      return <Badge className="bg-state-success text-white">Met</Badge>;
    case 'not_met':
      return <Badge className="bg-state-warning text-white">Not met</Badge>;
    case 'in_progress':
      return <Badge className="bg-state-info text-white">In progress</Badge>;
    default:
      return <Badge variant="outline">Open</Badge>;
  }
}

function progressValue(p: ObjectiveProgress): number {
  if (p.qualitative || p.target == null || p.measured_value == null) return 0;
  if (p.target <= 0) return p.measured_value > 0 ? 100 : 0;
  return Math.min(100, Math.max(0, (p.measured_value / p.target) * 100));
}

export function GoalProgressTracker({ subredditName }: GoalProgressTrackerProps) {
  const { data, isLoading } = useMissionProgress(subredditName);
  const objectives = data?.objectives ?? [];

  return (
    <Card>
      <CardHeader>
        <CardTitle>Goal Progress</CardTitle>
        <CardDescription>
          Mission objectives scored against live deliberation metrics. Qualitative
          objectives surface for human review.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {isLoading && <p className="text-sm text-text-muted">Loading…</p>}
        {!isLoading && objectives.length === 0 && (
          <p className="text-sm text-text-muted">
            No objectives yet — edit the mission to add some.
          </p>
        )}
        {objectives.map((p) => (
          <div key={p.objective_id} className="space-y-1.5">
            <div className="flex items-start justify-between gap-2">
              <div>
                <p className="text-sm font-semibold text-text-primary">{p.title}</p>
                {p.metric && (
                  <p className="text-xs text-text-muted">
                    {p.metric}
                    {p.target != null && <> · target {p.target}</>}
                    {p.measured_value != null && (
                      <> · measured {p.measured_value.toFixed(3)}</>
                    )}
                    {p.sample_size > 0 && <> · n={p.sample_size}</>}
                  </p>
                )}
              </div>
              {statusBadge(p)}
            </div>
            {!p.qualitative && <Progress value={progressValue(p)} />}
            {p.detail && <p className="text-xs text-text-muted">{p.detail}</p>}
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
