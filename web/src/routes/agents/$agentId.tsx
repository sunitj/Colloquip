import { createFileRoute, Link } from '@tanstack/react-router';
import { useQuery } from '@tanstack/react-query';
import { Home, BookOpen, Target, BarChart3, ChevronRight } from 'lucide-react';
import { getAgent, getAgentCalibration } from '@/lib/api';
import { queryKeys } from '@/lib/queryKeys';
import { PageHeader } from '@/components/layout/PageHeader';
import { AgentProfileHeader } from '@/components/agents/AgentProfileHeader';
import { ExpertiseTagGrid } from '@/components/agents/ExpertiseTagGrid';
import { CalibrationGauge } from '@/components/agents/CalibrationGauge';
import { Skeleton } from '@/components/ui/skeleton';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';
import { PHASE_LABELS } from '@/lib/agentColors';

export const Route = createFileRoute('/agents/$agentId')({
  component: AgentProfilePage,
});

function ProfileSkeleton() {
  return (
    <div className="space-y-6">
      {/* Header skeleton */}
      <div className="flex items-start gap-5">
        <Skeleton className="h-16 w-16 rounded-full shrink-0" />
        <div className="flex-1 space-y-3">
          <Skeleton className="h-7 w-48" />
          <Skeleton className="h-4 w-32" />
          <div className="flex gap-2">
            <Skeleton className="h-5 w-16 rounded-full" />
            <Skeleton className="h-5 w-20 rounded-full" />
            <Skeleton className="h-5 w-14 rounded-full" />
          </div>
        </div>
      </div>
      {/* Tabs skeleton */}
      <div className="space-y-4">
        <Skeleton className="h-10 w-72" />
        <Skeleton className="h-32 w-full rounded-lg" />
        <Skeleton className="h-24 w-full rounded-lg" />
      </div>
    </div>
  );
}

function CalibrationSkeleton() {
  return (
    <div className="space-y-6">
      <div className="rounded-lg border border-border-default bg-bg-surface p-5 space-y-4">
        <Skeleton className="h-5 w-32" />
        <Skeleton className="h-10 w-20" />
        <Skeleton className="h-3 w-full" />
        <div className="grid grid-cols-4 gap-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="flex flex-col items-center gap-1">
              <Skeleton className="h-6 w-10" />
              <Skeleton className="h-3 w-12" />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function AgentProfilePage() {
  const { agentId } = Route.useParams();

  const detailQuery = useQuery({
    queryKey: queryKeys.agents.detail(agentId),
    queryFn: () => getAgent(agentId),
  });

  const calibrationQuery = useQuery({
    queryKey: queryKeys.agents.calibration(agentId),
    queryFn: () => getAgentCalibration(agentId),
  });

  const agent = detailQuery.data;
  const calibration = calibrationQuery.data;

  return (
    <div>
      {/* Breadcrumb */}
      <PageHeader
        title={agent?.display_name ?? 'Agent Profile'}
        breadcrumb={
          <nav className="flex items-center gap-1.5 text-sm text-text-muted">
            <Link
              to="/"
              className="inline-flex items-center gap-1 hover:text-text-primary transition-colors"
            >
              <Home className="h-3.5 w-3.5" />
              Home
            </Link>
            <ChevronRight className="h-3 w-3" />
            <Link
              to="/agents"
              className="hover:text-text-primary transition-colors"
            >
              Agents
            </Link>
            <ChevronRight className="h-3 w-3" />
            <span className="text-text-secondary">
              {agent?.display_name ?? agentId}
            </span>
          </nav>
        }
      />

      {/* Main content */}
      {detailQuery.isLoading ? (
        <ProfileSkeleton />
      ) : detailQuery.isError ? (
        <div className="text-sm text-destructive">
          Failed to load agent details.
        </div>
      ) : agent ? (
        <div className="space-y-6">
          {/* Profile header */}
          <AgentProfileHeader agent={agent} />

          <Separator />

          {/* Tabs */}
          <Tabs defaultValue="overview">
            <TabsList>
              <TabsTrigger value="overview" className="gap-1.5">
                <BookOpen className="h-4 w-4" />
                Overview
              </TabsTrigger>
              <TabsTrigger value="expertise" className="gap-1.5">
                <Target className="h-4 w-4" />
                Expertise
              </TabsTrigger>
              <TabsTrigger value="calibration" className="gap-1.5">
                <BarChart3 className="h-4 w-4" />
                Calibration
              </TabsTrigger>
            </TabsList>

            {/* Overview tab */}
            <TabsContent value="overview" className="space-y-6">
              {/* Persona prompt */}
              <Card>
                <CardHeader>
                  <CardTitle>Persona</CardTitle>
                </CardHeader>
                <CardContent>
                  <blockquote className="rounded-md bg-bg-elevated border-l-2 border-accent p-4 text-sm text-text-secondary italic leading-relaxed whitespace-pre-wrap">
                    {agent.persona_prompt}
                  </blockquote>
                </CardContent>
              </Card>

              {/* Knowledge scope */}
              {agent.knowledge_scope && (
                <Card>
                  <CardHeader>
                    <CardTitle>Knowledge Scope</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="text-sm text-text-secondary leading-relaxed">
                      {agent.knowledge_scope}
                    </p>
                  </CardContent>
                </Card>
              )}

              {/* Phase mandates */}
              {Object.keys(agent.phase_mandates).length > 0 && (
                <Card>
                  <CardHeader>
                    <CardTitle>Phase Mandates</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-2">
                    {Object.entries(agent.phase_mandates).map(
                      ([phase, mandate]) => (
                        <details
                          key={phase}
                          className="group rounded-sm border border-border-default"
                        >
                          <summary className="flex cursor-pointer items-center gap-2 px-4 py-3 text-sm font-medium text-text-primary hover:bg-bg-elevated transition-colors rounded-sm">
                            <ChevronRight className="h-4 w-4 text-text-muted transition-transform group-open:rotate-90" />
                            {PHASE_LABELS[phase] ?? phase}
                          </summary>
                          <div className="px-4 pb-3 pl-10 text-sm text-text-secondary leading-relaxed">
                            {mandate}
                          </div>
                        </details>
                      ),
                    )}
                  </CardContent>
                </Card>
              )}
            </TabsContent>

            {/* Expertise tab */}
            <TabsContent value="expertise" className="space-y-6">
              <Card>
                <CardContent className="pt-5 space-y-6">
                  <ExpertiseTagGrid
                    tags={agent.expertise_tags}
                    label="Expertise Tags"
                  />
                  <ExpertiseTagGrid
                    tags={agent.domain_keywords}
                    label="Domain Keywords"
                  />
                  <ExpertiseTagGrid
                    tags={agent.evaluation_criteria}
                    label="Evaluation Criteria"
                  />
                </CardContent>
              </Card>
            </TabsContent>

            {/* Calibration tab */}
            <TabsContent value="calibration">
              {calibrationQuery.isLoading ? (
                <CalibrationSkeleton />
              ) : calibrationQuery.isError ? (
                <div className="text-sm text-destructive">
                  Failed to load calibration data.
                </div>
              ) : calibration ? (
                <CalibrationGauge report={calibration} />
              ) : (
                <div className="flex flex-col items-center justify-center py-16 text-center">
                  <BarChart3 className="h-10 w-10 text-text-muted mb-4" />
                  <p className="text-lg font-medium text-text-primary">
                    No calibration data
                  </p>
                  <p className="mt-2 text-sm text-text-secondary max-w-md">
                    Calibration data will appear here once outcome reports have
                    been filed for threads this agent participated in.
                  </p>
                </div>
              )}
            </TabsContent>
          </Tabs>
        </div>
      ) : null}
    </div>
  );
}
