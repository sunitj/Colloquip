import { createFileRoute } from '@tanstack/react-router';
import { useQuery, useMutation } from '@tanstack/react-query';
import { platformInit, getCalibrationOverview, getSubreddits, getAgents } from '@/lib/api';
import { queryKeys } from '@/lib/queryKeys';
import { useDeliberationStore } from '@/stores/deliberationStore';
import { PageHeader } from '@/components/layout/PageHeader';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { EmptyState } from '@/components/shared/EmptyState';
import { Skeleton } from '@/components/ui/Skeleton';
import { ErrorBanner } from '@/components/shared/ErrorBanner';
import { cn } from '@/lib/utils';
import type { CalibrationReport } from '@/types/platform';

export const Route = createFileRoute('/settings')({
  component: SettingsPage,
});

// ---------------------------------------------------------------------------
// Stat card used in both Calibration Overview and Platform Health
// ---------------------------------------------------------------------------
function StatCard({ value, label }: { value: string | number; label: string }) {
  return (
    <div className="rounded-2xl bg-bg-secondary border border-border-default p-5 text-center">
      <div className="text-2xl font-bold text-text-primary font-[family-name:var(--font-heading)]">{value}</div>
      <div className="text-xs text-text-muted mt-1">{label}</div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Section 1 -- Platform Actions
// ---------------------------------------------------------------------------
function PlatformActionsSection() {
  const mutation = useMutation({ mutationFn: platformInit });

  return (
    <section>
      <h2 className="text-sm font-semibold text-text-primary mb-3">
        Platform Actions
      </h2>
      <div className="rounded-2xl bg-bg-secondary border border-border-default p-6">
        <p className="text-sm text-text-secondary mb-4">
          Run platform initialization to set up communities, recruit agents, and configure watchers.
        </p>

        <div className="flex items-center gap-3">
          <Button
            onClick={() => mutation.mutate()}
            disabled={mutation.isPending}
          >
            {mutation.isPending ? 'Initializing...' : 'Initialize Platform'}
          </Button>

          {mutation.isSuccess && (
            <span className="text-sm text-green-600">
              Platform initialized successfully.
            </span>
          )}
          {mutation.isError && (
            <span className="text-sm text-red-600">
              {mutation.error instanceof Error
                ? mutation.error.message
                : 'Initialization failed.'}
            </span>
          )}
        </div>
      </div>
    </section>
  );
}

// ---------------------------------------------------------------------------
// Section 2 -- Calibration Overview
// ---------------------------------------------------------------------------
function AgentAccuracyBar({ report }: { report: CalibrationReport }) {
  const pct = Math.round(report.accuracy * 100);

  return (
    <div className="rounded-2xl bg-bg-secondary border border-border-default p-6">
      {/* Header row */}
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm font-medium text-text-primary">{report.agent_id}</span>
        <Badge variant={report.is_meaningful ? 'supportive' : 'neutral'}>
          {pct}% accuracy
        </Badge>
      </div>

      {/* Progress bar */}
      <div className="h-2 bg-bg-tertiary rounded-full mb-3">
        <div
          className="h-2 bg-pastel-lavender rounded-full transition-all"
          style={{ width: `${pct}%` }}
        />
      </div>

      {/* Counts */}
      <div className="flex gap-4 text-xs text-text-secondary mb-2">
        <span>
          Correct: <span className="text-green-600 font-medium">{report.correct}</span>
        </span>
        <span>
          Partial: <span className="text-gray-500 font-medium">{report.partial}</span>
        </span>
        <span>
          Incorrect: <span className="text-[#C95A6B] bg-pastel-rose-bg rounded px-1 font-medium">{report.incorrect}</span>
        </span>
        <span>
          Total: <span className="font-medium text-text-primary">{report.total_evaluations}</span>
        </span>
      </div>

      {/* Systematic biases */}
      {report.systematic_biases.length > 0 && (
        <div className="mt-2">
          <span className="text-xs text-text-muted">Systematic biases:</span>
          <div className="flex flex-wrap gap-1 mt-1">
            {report.systematic_biases.map((bias) => (
              <Badge key={bias} variant="critical">
                {bias}
              </Badge>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function CalibrationOverviewSection() {
  const { data, isLoading, isError, error } = useQuery({
    queryKey: queryKeys.calibration.overview,
    queryFn: getCalibrationOverview,
  });

  return (
    <section>
      <h2 className="text-sm font-semibold text-text-primary mb-3">
        Calibration Overview
      </h2>

      {isLoading && (
        <div className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-6">
            <Skeleton className="h-20" />
            <Skeleton className="h-20" />
            <Skeleton className="h-20" />
          </div>
          <Skeleton className="h-32" />
        </div>
      )}

      {isError && (
        <ErrorBanner
          message={error instanceof Error ? error.message : 'Failed to load calibration data.'}
        />
      )}

      {data && data.total_outcomes === 0 && (
        <EmptyState
          title="No calibration data yet"
          description="Report outcomes on completed threads to begin calibrating agent accuracy."
        />
      )}

      {data && data.total_outcomes > 0 && (
        <div className="space-y-4">
          {/* Stat cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-6">
            <StatCard value={data.total_outcomes} label="Total Outcomes" />
            <StatCard value={data.agents_with_data} label="Agents With Data" />
            <StatCard value={data.agents_calibrated} label="Agents Calibrated" />
          </div>

          {/* Agent reports */}
          {data.agent_reports.length > 0 && (
            <div className="space-y-3">
              <h3 className="text-xs font-semibold text-text-secondary">Agent Reports</h3>
              {data.agent_reports.map((report) => (
                <AgentAccuracyBar key={report.agent_id} report={report} />
              ))}
            </div>
          )}
        </div>
      )}
    </section>
  );
}

// ---------------------------------------------------------------------------
// Section 3 -- Platform Health
// ---------------------------------------------------------------------------
function PlatformHealthSection() {
  const connected = useDeliberationStore((s) => s.connected);

  const subredditsQuery = useQuery({
    queryKey: queryKeys.subreddits.all,
    queryFn: getSubreddits,
  });

  const agentsQuery = useQuery({
    queryKey: queryKeys.agents.all,
    queryFn: getAgents,
  });

  const communityCount = subredditsQuery.data?.subreddits.length ?? 0;
  const agentCount = agentsQuery.data?.agents.length ?? 0;
  const isLoading = subredditsQuery.isLoading || agentsQuery.isLoading;

  return (
    <section>
      <h2 className="text-sm font-semibold text-text-primary mb-3">
        Platform Health
      </h2>
      <div className="rounded-2xl bg-bg-secondary border border-border-default p-6 space-y-4">
        {/* Connection status */}
        <div className="flex items-center gap-2">
          <div
            className={cn(
              'h-2.5 w-2.5 rounded-full',
              connected ? 'bg-green-500' : 'bg-bg-tertiary',
            )}
          />
          <span className="text-sm text-text-primary">
            WebSocket: {connected ? 'Connected' : 'Standby'}
          </span>
          <Badge variant={connected ? 'supportive' : 'neutral'}>
            {connected ? 'Online' : 'Standby'}
          </Badge>
        </div>

        {/* Counts */}
        {isLoading ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
            <Skeleton className="h-20" />
            <Skeleton className="h-20" />
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
            <StatCard value={communityCount} label="Communities" />
            <StatCard value={agentCount} label="Agents" />
          </div>
        )}
      </div>
    </section>
  );
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------
function SettingsPage() {
  return (
    <div className="p-4 sm:p-6 md:p-8 lg:p-10 max-w-4xl mx-auto">
      <PageHeader title="Settings" subtitle="Platform configuration and health" />

      <div className="space-y-10">
        <PlatformActionsSection />
        <CalibrationOverviewSection />
        <PlatformHealthSection />
      </div>
    </div>
  );
}
