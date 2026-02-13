import { useState } from 'react';
import { createFileRoute } from '@tanstack/react-router';
import { useQuery } from '@tanstack/react-query';
import { getAgent, getAgentCalibration } from '@/lib/api';
import { queryKeys } from '@/lib/queryKeys';
import { getAgentColor, getAgentInitials, PHASE_LABELS } from '@/lib/agentColors';
import { Badge } from '@/components/ui/Badge';
import { Skeleton } from '@/components/ui/Skeleton';
import { Breadcrumb } from '@/components/layout/Breadcrumb';
import { cn } from '@/lib/utils';

export const Route = createFileRoute('/agents/$agentId')({
  component: AgentProfilePage,
});

type Tab = 'overview' | 'expertise' | 'calibration';

function AgentProfilePage() {
  const { agentId } = Route.useParams();
  const [activeTab, setActiveTab] = useState<Tab>('overview');

  const { data: agent, isLoading } = useQuery({
    queryKey: queryKeys.agents.detail(agentId),
    queryFn: () => getAgent(agentId),
  });

  const { data: calibration } = useQuery({
    queryKey: queryKeys.agents.calibration(agentId),
    queryFn: () => getAgentCalibration(agentId),
    enabled: activeTab === 'calibration',
  });

  if (isLoading) {
    return (
      <div className="p-4 sm:p-6 md:p-8 lg:p-10 max-w-4xl mx-auto space-y-4">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  if (!agent) {
    return (
      <div className="p-4 sm:p-6 md:p-8 lg:p-10 max-w-4xl mx-auto">
        <div className="text-text-muted text-sm">Agent not found.</div>
      </div>
    );
  }

  const color = getAgentColor(agent.agent_type, agent.is_red_team);
  const initials = getAgentInitials(agent.display_name);

  const tabs: { id: Tab; label: string }[] = [
    { id: 'overview', label: 'Overview' },
    { id: 'expertise', label: 'Expertise' },
    { id: 'calibration', label: 'Calibration' },
  ];

  return (
    <div className="p-4 sm:p-6 md:p-8 lg:p-10 max-w-4xl mx-auto">
      <Breadcrumb
        items={[
          { label: 'Agents', href: '/agents' },
          { label: agent.display_name },
        ]}
      />

      {/* Header */}
      <div className="flex items-center gap-4 mt-4 mb-8">
        <div
          className="w-14 h-14 rounded-full flex items-center justify-center text-lg font-bold shrink-0"
          style={{ backgroundColor: `${color}30`, color: color }}
        >
          {initials}
        </div>
        <div>
          <h1 className="text-lg sm:text-xl md:text-2xl font-bold text-text-primary font-[family-name:var(--font-heading)]">{agent.display_name}</h1>
          <div className="flex items-center gap-2 mt-1">
            <span className="text-xs text-text-muted">{agent.agent_type}</span>
            {agent.is_red_team && <Badge variant="critical">Red Team</Badge>}
            <Badge variant="outline">v{agent.version}</Badge>
            <span className="text-xs text-text-muted">{agent.status}</span>
          </div>
        </div>
      </div>

      {/* Tabs -- border-b style */}
      <div className="flex items-center gap-4 border-b border-border-default mb-6">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={cn(
              'px-1 pb-2 text-sm font-medium transition-all duration-200 cursor-pointer -mb-px',
              activeTab === tab.id
                ? 'text-text-primary border-b-2 border-accent'
                : 'text-text-muted hover:text-text-secondary',
            )}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {activeTab === 'overview' && (
        <div className="space-y-6">
          {agent.persona_prompt && (
            <div>
              <h3 className="text-sm font-semibold text-text-primary mb-2">Persona</h3>
              <p className="text-sm text-text-secondary leading-relaxed bg-bg-tertiary/50 rounded-xl p-4">
                {agent.persona_prompt}
              </p>
            </div>
          )}

          {agent.knowledge_scope && (
            <div>
              <h3 className="text-sm font-semibold text-text-primary mb-2">Knowledge Scope</h3>
              <p className="text-sm text-text-secondary">{agent.knowledge_scope}</p>
            </div>
          )}

          {Object.keys(agent.phase_mandates).length > 0 && (
            <div>
              <h3 className="text-sm font-semibold text-text-primary mb-2">Phase Mandates</h3>
              <div className="space-y-2">
                {Object.entries(agent.phase_mandates).map(([phase, mandate]) => (
                  <div key={phase} className="bg-bg-tertiary/50 rounded-xl p-3">
                    <span className="text-xs font-semibold text-accent">
                      {PHASE_LABELS[phase] || phase}
                    </span>
                    <p className="text-xs text-text-secondary mt-1">{mandate}</p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {activeTab === 'expertise' && (
        <div className="space-y-6">
          {agent.expertise_tags.length > 0 && (
            <div>
              <h3 className="text-sm font-semibold text-text-primary mb-3">Expertise Tags</h3>
              <div className="flex flex-wrap gap-2">
                {agent.expertise_tags.map((tag) => (
                  <span key={tag} className="text-xs px-2.5 py-1 rounded-full bg-bg-tertiary text-text-secondary border border-border-default">
                    {tag}
                  </span>
                ))}
              </div>
            </div>
          )}

          {agent.domain_keywords.length > 0 && (
            <div>
              <h3 className="text-sm font-semibold text-text-primary mb-3">Domain Keywords</h3>
              <div className="flex flex-wrap gap-2">
                {agent.domain_keywords.map((kw) => (
                  <span key={kw} className="text-xs px-2.5 py-1 rounded-full bg-pastel-lavender-bg text-[#8B6DBF]">
                    {kw}
                  </span>
                ))}
              </div>
            </div>
          )}

          {agent.evaluation_criteria.length > 0 && (
            <div>
              <h3 className="text-sm font-semibold text-text-primary mb-2">Evaluation Criteria</h3>
              <ul className="space-y-1.5">
                {agent.evaluation_criteria.map((c, i) => (
                  <li key={i} className="text-sm text-text-secondary flex gap-2">
                    <span className="text-accent shrink-0">{i + 1}.</span>
                    <span>{c}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {activeTab === 'calibration' && (
        <div className="space-y-6">
          {!calibration ? (
            <div className="space-y-3">
              <Skeleton className="h-32 w-full" />
              <Skeleton className="h-24 w-full" />
            </div>
          ) : !calibration.is_meaningful ? (
            <div className="text-sm text-text-muted py-8 text-center">
              Not enough data for meaningful calibration. Need more outcome reports.
            </div>
          ) : (
            <>
              {/* Accuracy gauge */}
              <div className="bg-bg-tertiary/50 rounded-xl p-6 text-center">
                <div className="text-3xl font-bold text-text-primary font-[family-name:var(--font-heading)]">
                  {(calibration.accuracy * 100).toFixed(0)}%
                </div>
                <div className="text-xs text-text-muted mt-1">Overall Accuracy</div>
                <div className="flex justify-center gap-6 mt-4 text-xs">
                  <div>
                    <div className="text-green-600 font-semibold">{calibration.correct}</div>
                    <div className="text-text-muted">Correct</div>
                  </div>
                  <div>
                    <div className="text-amber-600 font-semibold">{calibration.partial}</div>
                    <div className="text-text-muted">Partial</div>
                  </div>
                  <div>
                    <div className="text-red-600 font-semibold">{calibration.incorrect}</div>
                    <div className="text-text-muted">Incorrect</div>
                  </div>
                </div>
                <div className="text-xs text-text-muted mt-3">
                  {calibration.total_evaluations} total evaluations
                </div>
              </div>

              {/* Domain accuracy */}
              {Object.keys(calibration.domain_accuracy).length > 0 && (
                <div>
                  <h3 className="text-sm font-semibold text-text-primary mb-3">Domain Accuracy</h3>
                  <div className="space-y-2">
                    {Object.entries(calibration.domain_accuracy).map(([domain, acc]) => (
                      <div key={domain} className="flex items-center gap-3">
                        <span className="text-xs text-text-secondary w-32 truncate">{domain}</span>
                        <div className="flex-1 h-2 bg-bg-tertiary rounded-full overflow-hidden">
                          <div
                            className="h-full rounded-full bg-pastel-lavender transition-all"
                            style={{ width: `${acc * 100}%` }}
                          />
                        </div>
                        <span className="text-xs text-text-muted w-10 text-right">{(acc * 100).toFixed(0)}%</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Biases */}
              {calibration.systematic_biases.length > 0 && (
                <div>
                  <h3 className="text-sm font-semibold text-text-primary mb-2">Systematic Biases</h3>
                  <ul className="space-y-1">
                    {calibration.systematic_biases.map((bias, i) => (
                      <li key={i} className="text-sm text-amber-600 flex gap-2">
                        <span className="shrink-0">!</span>
                        <span>{bias}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}
