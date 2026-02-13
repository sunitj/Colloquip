import { createFileRoute } from '@tanstack/react-router';
import { useQuery, useMutation } from '@tanstack/react-query';
import { Rocket, BarChart3, Users, MessageSquare, Activity } from 'lucide-react';
import { platformInit, getCalibrationOverview, getSubreddits, getAgents } from '@/lib/api';
import { queryKeys } from '@/lib/queryKeys';
import { formatNumber } from '@/lib/utils';
import { PageHeader } from '@/components/layout/PageHeader';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { Skeleton } from '@/components/ui/skeleton';
import { Progress } from '@/components/ui/progress';
import { ConnectionIndicator } from '@/components/shared/ConnectionIndicator';

export const Route = createFileRoute('/settings')({
  component: SettingsPage,
});

function SettingsPage() {
  // Platform init mutation
  const initMutation = useMutation({
    mutationFn: platformInit,
  });

  // Calibration overview
  const {
    data: calibration,
    isLoading: calibrationLoading,
  } = useQuery({
    queryKey: queryKeys.calibration.overview,
    queryFn: getCalibrationOverview,
  });

  // Community count
  const { data: subredditsData, isLoading: subredditsLoading } = useQuery({
    queryKey: queryKeys.subreddits.all,
    queryFn: getSubreddits,
  });

  // Agent count
  const { data: agentsData, isLoading: agentsLoading } = useQuery({
    queryKey: queryKeys.agents.all,
    queryFn: getAgents,
  });

  const communityCount = subredditsData?.subreddits?.length ?? 0;
  const agentCount = agentsData?.agents?.length ?? 0;

  return (
    <div>
      <PageHeader
        title="Settings"
        subtitle="Platform configuration, calibration, and health monitoring"
      />

      <div className="space-y-8">
        {/* Platform Initialization */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Rocket className="h-5 w-5 text-text-accent" />
              Platform
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-text-secondary mb-4">
              Initialize the platform to set up default communities, agents, and configurations.
              This is typically done once when first deploying Colloquip.
            </p>
            <Button
              onClick={() => initMutation.mutate()}
              disabled={initMutation.isPending}
            >
              <Rocket className="h-4 w-4" />
              {initMutation.isPending ? 'Initializing...' : 'Initialize Platform'}
            </Button>

            {initMutation.isSuccess && (
              <p className="mt-3 text-sm text-success">
                Platform initialized successfully.
              </p>
            )}
            {initMutation.isError && (
              <p className="mt-3 text-sm text-destructive">
                Initialization failed. Please check the server logs.
              </p>
            )}
          </CardContent>
        </Card>

        {/* Calibration Overview */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <BarChart3 className="h-5 w-5 text-text-accent" />
              Calibration Overview
            </CardTitle>
          </CardHeader>
          <CardContent>
            {calibrationLoading ? (
              <div className="space-y-3">
                <Skeleton className="h-5 w-48" />
                <Skeleton className="h-5 w-64" />
                <Skeleton className="h-5 w-40" />
              </div>
            ) : calibration ? (
              <div className="space-y-4">
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
                  <div className="rounded-md bg-bg-elevated p-4">
                    <p className="text-xs font-medium uppercase tracking-wide text-text-muted">
                      Total Outcomes
                    </p>
                    <p className="mt-1 text-2xl font-bold text-text-primary">
                      {formatNumber(calibration.total_outcomes)}
                    </p>
                  </div>
                  <div className="rounded-md bg-bg-elevated p-4">
                    <p className="text-xs font-medium uppercase tracking-wide text-text-muted">
                      Agents with Data
                    </p>
                    <p className="mt-1 text-2xl font-bold text-text-primary">
                      {calibration.agents_with_data}
                    </p>
                  </div>
                  <div className="rounded-md bg-bg-elevated p-4">
                    <p className="text-xs font-medium uppercase tracking-wide text-text-muted">
                      Agents Calibrated
                    </p>
                    <p className="mt-1 text-2xl font-bold text-text-primary">
                      {calibration.agents_calibrated}
                    </p>
                  </div>
                </div>

                {/* Agent calibration reports */}
                {calibration.agent_reports.length > 0 && (
                  <>
                    <Separator />
                    <div className="space-y-3">
                      <h4 className="text-sm font-medium text-text-primary">
                        Agent Reports
                      </h4>
                      {calibration.agent_reports.map((report) => (
                        <div
                          key={report.agent_id}
                          className="rounded-md border border-border-default bg-bg-elevated p-4"
                        >
                          <div className="flex items-center justify-between gap-2">
                            <span className="text-sm font-medium text-text-primary truncate">
                              {report.agent_id}
                            </span>
                            <div className="flex items-center gap-2">
                              <Badge
                                variant={report.is_meaningful ? 'success' : 'secondary'}
                              >
                                {report.is_meaningful ? 'Meaningful' : 'Insufficient data'}
                              </Badge>
                            </div>
                          </div>

                          {report.is_meaningful && (
                            <div className="mt-3 space-y-2">
                              <div className="flex items-center justify-between text-xs text-text-secondary">
                                <span>Accuracy</span>
                                <span className="font-medium text-text-primary">
                                  {Math.round(report.accuracy * 100)}%
                                </span>
                              </div>
                              <Progress
                                value={report.accuracy * 100}
                                color={
                                  report.accuracy > 0.7
                                    ? '#22C55E'
                                    : report.accuracy > 0.4
                                      ? '#F59E0B'
                                      : '#EF4444'
                                }
                              />
                              <div className="mt-2 flex gap-4 text-xs text-text-muted">
                                <span>
                                  {report.correct} correct
                                </span>
                                <span>
                                  {report.partial} partial
                                </span>
                                <span>
                                  {report.incorrect} incorrect
                                </span>
                              </div>
                            </div>
                          )}

                          {report.systematic_biases.length > 0 && (
                            <div className="mt-2 flex flex-wrap gap-1.5">
                              {report.systematic_biases.map((bias, i) => (
                                <Badge key={i} variant="warning">
                                  {bias}
                                </Badge>
                              ))}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  </>
                )}
              </div>
            ) : (
              <p className="text-sm text-text-muted">
                No calibration data available yet. Report outcomes on completed threads to build calibration data.
              </p>
            )}
          </CardContent>
        </Card>

        {/* Platform Health */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Activity className="h-5 w-5 text-text-accent" />
              Platform Health
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {/* Connection status */}
              <div className="flex items-center justify-between">
                <span className="text-sm text-text-secondary">API Connection</span>
                <ConnectionIndicator connected={!subredditsLoading && !!subredditsData} />
              </div>

              <Separator />

              {/* Community count */}
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <MessageSquare className="h-4 w-4 text-text-muted" />
                  <span className="text-sm text-text-secondary">Communities</span>
                </div>
                {subredditsLoading ? (
                  <Skeleton className="h-5 w-12" />
                ) : (
                  <span className="text-sm font-medium text-text-primary">
                    {communityCount}
                  </span>
                )}
              </div>

              {/* Agent count */}
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Users className="h-4 w-4 text-text-muted" />
                  <span className="text-sm text-text-secondary">Agents</span>
                </div>
                {agentsLoading ? (
                  <Skeleton className="h-5 w-12" />
                ) : (
                  <span className="text-sm font-medium text-text-primary">
                    {agentCount}
                  </span>
                )}
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
