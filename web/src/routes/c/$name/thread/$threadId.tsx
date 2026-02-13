import { useEffect, useRef, useState } from 'react';
import { createFileRoute } from '@tanstack/react-router';
import { useQuery } from '@tanstack/react-query';
import { getDeliberationHistory, getSubreddit, exportMarkdown, exportJson } from '@/lib/api';
import { queryKeys } from '@/lib/queryKeys';
import { useWebSocket } from '@/hooks/useWebSocket';
import { useDeliberationStore } from '@/stores/deliberationStore';
import { ConversationStream } from '@/components/deliberation/ConversationStream';
import { EnergyChart } from '@/components/deliberation/EnergyChart';
import { PhaseTimeline } from '@/components/deliberation/PhaseTimeline';
import { PhaseTransitionBanner } from '@/components/deliberation/PhaseTransitionBanner';
import { AgentRoster } from '@/components/deliberation/AgentRoster';
import { ConsensusView } from '@/components/deliberation/ConsensusView';
import { InterventionBar } from '@/components/deliberation/InterventionBar';
import { TriggerLog } from '@/components/deliberation/TriggerLog';
import { ThreadCostSummary } from '@/components/threads/ThreadCostSummary';
import { ReportOutcomeDialog } from '@/components/dialogs/ReportOutcomeDialog';
import { Breadcrumb } from '@/components/layout/Breadcrumb';
import { Button } from '@/components/ui/Button';
import { Skeleton } from '@/components/ui/Skeleton';
import { cn } from '@/lib/utils';

export const Route = createFileRoute('/c/$name/thread/$threadId')({
  component: ThreadDetailPage,
});

function ThreadDetailPage() {
  const { name, threadId } = Route.useParams();
  const [showTriggers, setShowTriggers] = useState(false);
  const [showOutcomeDialog, setShowOutcomeDialog] = useState(false);
  const [showRightPanel, setShowRightPanel] = useState(false);
  const prevPhaseRef = useRef<string | null>(null);

  const store = useDeliberationStore();
  const { intervene } = useWebSocket(threadId);

  // Fetch community for member info
  const { data: community } = useQuery({
    queryKey: queryKeys.subreddits.detail(name),
    queryFn: () => getSubreddit(name),
  });

  // Load history on mount
  const { data: history, isLoading } = useQuery({
    queryKey: queryKeys.deliberations.history(threadId),
    queryFn: () => getDeliberationHistory(threadId),
  });

  // Load history into store once fetched
  useEffect(() => {
    if (history) {
      store.loadHistory({
        sessionId: history.session.id,
        hypothesis: history.session.hypothesis,
        status: history.session.status as 'pending' | 'running' | 'paused' | 'completed',
        phase: history.session.phase as 'explore' | 'debate' | 'deepen' | 'converge' | 'synthesis',
        posts: history.posts,
        energyHistory: history.energy_history,
        consensus: history.consensus,
      });
    }
  }, [history]); // eslint-disable-line react-hooks/exhaustive-deps

  // Track phase changes for transition banner
  useEffect(() => {
    if (store.phase) {
      const timer = setTimeout(() => {
        prevPhaseRef.current = store.phase;
      }, 3100);
      return () => clearTimeout(timer);
    }
  }, [store.phase]);

  // Clean up on unmount
  useEffect(() => {
    return () => {
      store.reset();
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const members = community?.members ?? [];
  const agents = members.map((m) => ({
    agent_id: m.agent_id,
    agent_type: m.agent_type,
    display_name: m.display_name,
    is_red_team: m.is_red_team,
  }));

  const handleIntervene = (content: string, type?: string) => {
    intervene(type || 'question', content);
  };

  const handleExportMarkdown = async () => {
    const md = await exportMarkdown(threadId);
    const blob = new Blob([md], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${threadId}.md`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleExportJson = async () => {
    const data = await exportJson(threadId);
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${threadId}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  if (isLoading) {
    return (
      <div className="flex h-full">
        <div className="flex-1 p-6 space-y-4">
          <Skeleton className="h-6 w-64" />
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-96 w-full" />
        </div>
        <div className="w-80 p-4 space-y-4 border-l border-border-default">
          <Skeleton className="h-32 w-full" />
          <Skeleton className="h-48 w-full" />
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-[calc(100vh-1px)] overflow-hidden">
      {/* Main content */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Header */}
        <div className="shrink-0 px-6 pt-4 pb-3 border-b border-border-subtle">
          <Breadcrumb
            items={[
              { label: 'Home', href: '/' },
              { label: `c/${name}`, href: `/c/${name}` },
              { label: store.hypothesis || threadId },
            ]}
          />
          {store.hypothesis && (
            <h1 className="text-lg font-bold text-text-primary mt-2 leading-snug">
              {store.hypothesis}
            </h1>
          )}
          <div className="flex items-center gap-3 mt-1.5 text-xs text-text-muted">
            <span className={cn(
              'font-semibold uppercase',
              store.status === 'running' ? 'text-green-400' :
              store.status === 'completed' ? 'text-text-muted' :
              store.status === 'paused' ? 'text-amber-400' : 'text-text-muted',
            )}>
              {store.status}
            </span>
            <span>{store.posts.length} posts</span>
            {store.connected && <span className="text-green-400">live</span>}
          </div>
        </div>

        {/* Conversation area */}
        <div className="flex-1 overflow-hidden px-6 py-4 relative" aria-live="polite">
          <PhaseTransitionBanner
            phase={store.phase}
            previousPhase={prevPhaseRef.current as typeof store.phase | null}
          />
          {store.consensus ? (
            <div className="overflow-y-auto h-full scrollbar-thin">
              <ConsensusView consensus={store.consensus} />
              <div className="mt-8 border-t border-border-default pt-6">
                <h3 className="text-xs font-bold uppercase tracking-widest text-text-muted mb-4">
                  Full Conversation
                </h3>
                <ConversationStream
                  posts={store.posts}
                  status={store.status}
                  thinking={store.thinking}
                />
              </div>
            </div>
          ) : (
            <ConversationStream
              posts={store.posts}
              status={store.status}
              thinking={store.thinking}
            />
          )}
        </div>

        {/* Intervention bar */}
        <div className="shrink-0 px-6 pb-4">
          <InterventionBar onIntervene={handleIntervene} status={store.status} />
        </div>

        {/* Trigger log toggle */}
        <div className="shrink-0 border-t border-border-subtle">
          <button
            onClick={() => setShowTriggers(!showTriggers)}
            className="w-full px-6 py-2 text-[10px] font-bold uppercase tracking-widest text-text-muted hover:text-text-secondary transition-colors text-left flex items-center gap-2"
          >
            <span className={cn('transition-transform', showTriggers && 'rotate-180')}>
              &#9660;
            </span>
            Trigger Log ({store.triggers.length})
          </button>
          {showTriggers && (
            <div className="px-6 pb-4 max-h-64 overflow-y-auto">
              <TriggerLog triggers={store.triggers} agents={agents} />
            </div>
          )}
        </div>
      </div>

      {/* Right panel toggle (mobile) */}
      <button
        onClick={() => setShowRightPanel(!showRightPanel)}
        className="lg:hidden fixed bottom-4 right-4 z-30 p-3 rounded-full bg-accent text-white shadow-lg hover:bg-accent-hover transition-colors"
        aria-label={showRightPanel ? 'Hide details panel' : 'Show details panel'}
      >
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
          {showRightPanel ? <path d="M18 6L6 18M6 6l12 12" /> : <path d="M4 6h16M4 12h16M4 18h16" />}
        </svg>
      </button>

      {/* Right panel */}
      <aside className={cn(
        'w-80 shrink-0 border-l border-border-default overflow-y-auto p-4 space-y-6 bg-bg-secondary scrollbar-thin',
        'fixed inset-y-0 right-0 z-40 lg:relative lg:z-auto transition-transform duration-200',
        showRightPanel ? 'translate-x-0' : 'translate-x-full lg:translate-x-0',
      )}>
        {/* Energy */}
        <div>
          <h3 className="text-[10px] font-bold uppercase tracking-widest text-text-muted mb-3">
            Energy
          </h3>
          <EnergyChart history={store.energyHistory} />
        </div>

        {/* Phase */}
        <div>
          <h3 className="text-[10px] font-bold uppercase tracking-widest text-text-muted mb-3">
            Phase
          </h3>
          <PhaseTimeline
            currentPhase={store.phase}
            phaseHistory={store.phaseHistory}
          />
        </div>

        {/* Agents */}
        {agents.length > 0 && (
          <div>
            <h3 className="text-[10px] font-bold uppercase tracking-widest text-text-muted mb-3">
              Agents ({agents.length})
            </h3>
            <AgentRoster
              agents={agents}
              posts={store.posts}
              triggers={store.triggers}
              status={store.status}
            />
          </div>
        )}

        {/* Costs */}
        <ThreadCostSummary threadId={threadId} />

        {/* Export */}
        <div>
          <h3 className="text-[10px] font-bold uppercase tracking-widest text-text-muted mb-3">
            Export
          </h3>
          <div className="flex gap-2">
            <Button size="sm" variant="outline" onClick={handleExportMarkdown}>
              Markdown
            </Button>
            <Button size="sm" variant="outline" onClick={handleExportJson}>
              JSON
            </Button>
          </div>
        </div>

        {/* Report Outcome (completed threads only) */}
        {store.status === 'completed' && (
          <div>
            <h3 className="text-[10px] font-bold uppercase tracking-widest text-text-muted mb-3">
              Feedback
            </h3>
            <Button size="sm" variant="outline" onClick={() => setShowOutcomeDialog(true)}>
              Report Outcome
            </Button>
          </div>
        )}
      </aside>

      <ReportOutcomeDialog
        open={showOutcomeDialog}
        onClose={() => setShowOutcomeDialog(false)}
        threadId={threadId}
      />
    </div>
  );
}
