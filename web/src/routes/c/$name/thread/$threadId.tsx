import { useEffect, useState } from 'react';
import { createFileRoute, Link } from '@tanstack/react-router';
import { useQuery } from '@tanstack/react-query';
import { ChevronRight, Home, FileCheck } from 'lucide-react';
import { useDeliberation } from '@/hooks/useDeliberation';
import { getSubredditMembers } from '@/lib/api';
import { queryKeys } from '@/lib/queryKeys';
import { PageHeader } from '@/components/layout/PageHeader';
import { RightPanel } from '@/components/layout/RightPanel';
import { ThreadHeader } from '@/components/threads/ThreadHeader';
import { ThreadCostSummary } from '@/components/threads/ThreadCostSummary';
import { ConversationFeed } from '@/components/deliberation/ConversationFeed';
import { InterventionBar } from '@/components/deliberation/InterventionBar';
import { TriggerDrawer } from '@/components/deliberation/TriggerDrawer';
import { PhaseTimeline } from '@/components/deliberation/PhaseTimeline';
import { EnergyGauge } from '@/components/deliberation/EnergyGauge';
import { AgentStage } from '@/components/deliberation/AgentStage';
import { ConsensusReveal } from '@/components/deliberation/ConsensusReveal';
import { EmptyState } from '@/components/shared/EmptyState';
import { ReportOutcomeDialog } from '@/components/dialogs/ReportOutcomeDialog';
import { Button } from '@/components/ui/button';

export const Route = createFileRoute('/c/$name/thread/$threadId')({
  component: ThreadPage,
});

function ThreadPage() {
  const { name, threadId } = Route.useParams();
  const { state, loadSession, intervene } = useDeliberation();
  const [reportOpen, setReportOpen] = useState(false);

  const { data: membersData } = useQuery({
    queryKey: queryKeys.subreddits.members(name),
    queryFn: () => getSubredditMembers(name),
  });

  const members = membersData?.members;

  useEffect(() => {
    loadSession(threadId);
  }, [threadId, loadSession]);

  const breadcrumb = (
    <nav className="flex items-center gap-1.5 text-sm text-text-muted">
      <Link to="/" className="hover:text-text-primary transition-colors">
        <Home className="h-3.5 w-3.5" />
      </Link>
      <ChevronRight className="h-3 w-3" />
      <Link
        to="/c/$name"
        params={{ name }}
        className="hover:text-text-primary transition-colors"
      >
        c/{name}
      </Link>
      <ChevronRight className="h-3 w-3" />
      <span className="text-text-secondary">Thread</span>
    </nav>
  );

  return (
    <div className="flex flex-col h-full">
      <div className="px-6 pt-6">
        <PageHeader
          title="Deliberation"
          subtitle={state.hypothesis || undefined}
          breadcrumb={breadcrumb}
          actions={
            state.status === 'completed' ? (
              <Button size="sm" variant="outline" onClick={() => setReportOpen(true)}>
                <FileCheck className="h-4 w-4" />
                Report Outcome
              </Button>
            ) : undefined
          }
        />
      </div>

      <div className="flex flex-1 min-h-0">
        {/* Main area */}
        <div className="flex-1 flex flex-col min-h-0 px-6">
          {/* Thread header */}
          <div className="mb-4">
            <ThreadHeader
              title={state.hypothesis || 'Loading...'}
              hypothesis={state.hypothesis}
              status={state.status}
              phase={state.phase}
            />
          </div>

          {/* Consensus reveal (when completed) */}
          {state.consensus ? (
            <div className="flex-1 overflow-y-auto space-y-6 pb-4">
              {/* Show feed above consensus */}
              <ConversationFeed
                posts={state.posts}
                phaseHistory={state.phaseHistory}
                thinking={state.thinking}
                members={members}
              />

              {/* Consensus section */}
              <div className="border-t border-border-default pt-6">
                <h3 className="text-lg font-semibold text-text-primary mb-4">
                  Consensus Reached
                </h3>
                <ConsensusReveal consensus={state.consensus} members={members} />
              </div>
            </div>
          ) : state.posts.length > 0 ? (
            <ConversationFeed
              posts={state.posts}
              phaseHistory={state.phaseHistory}
              thinking={state.thinking}
              members={members}
            />
          ) : state.error ? (
            <EmptyState
              title="Error Loading Thread"
              description={state.error}
            />
          ) : (
            <EmptyState
              title="Loading deliberation..."
              description="Fetching session history"
            />
          )}

          {/* Intervention bar */}
          <InterventionBar
            onIntervene={intervene}
            status={state.status}
          />

          {/* Trigger drawer */}
          <TriggerDrawer triggers={state.triggers} />
        </div>

        {/* Right panel */}
        <RightPanel>
          <div className="space-y-6">
            {/* Phase timeline */}
            <div>
              <h4 className="text-xs font-medium text-text-muted uppercase tracking-wider mb-3">
                Phase Progress
              </h4>
              <PhaseTimeline
                currentPhase={state.phase}
                phaseHistory={state.phaseHistory}
              />
            </div>

            {/* Energy gauge */}
            {state.energyHistory.length > 0 && (
              <div>
                <h4 className="text-xs font-medium text-text-muted uppercase tracking-wider mb-3">
                  Energy
                </h4>
                <EnergyGauge energyHistory={state.energyHistory} />
              </div>
            )}

            {/* Agent stage */}
            {members && members.length > 0 && (
              <div>
                <h4 className="text-xs font-medium text-text-muted uppercase tracking-wider mb-3">
                  Agents
                </h4>
                <AgentStage members={members} posts={state.posts} />
              </div>
            )}

            {/* Cost summary */}
            <div>
              <ThreadCostSummary threadId={threadId} />
            </div>
          </div>
        </RightPanel>
      </div>

      <ReportOutcomeDialog
        open={reportOpen}
        onOpenChange={setReportOpen}
        threadId={threadId}
      />
    </div>
  );
}
