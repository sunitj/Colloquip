import { cn } from '@/lib/utils';
import { getAgentColor } from '@/lib/agentColors';
import { TRIGGER_COLORS } from '@/lib/agentColors';
import { AgentAvatar } from '@/components/shared/AgentAvatar';
import { StanceBadge } from '@/components/shared/StanceBadge';
import { PhaseBadge } from '@/components/shared/PhaseBadge';
import { MarkdownContent } from '@/components/shared/MarkdownContent';
import { PostClaimsBlock } from './PostClaimsBlock';
import { PostQuestionsBlock } from './PostQuestionsBlock';
import { PostCitationsBlock } from './PostCitationsBlock';
import { Progress } from '@/components/ui/progress';
import type { Post } from '@/types/deliberation';
import type { AgentMember } from '@/types/platform';

interface PostCardProps {
  post: Post;
  members?: AgentMember[];
}

function isRedTeamAgent(agentId: string): boolean {
  const lower = agentId.toLowerCase();
  return lower.includes('red') || lower.includes('redteam');
}

function resolveAgent(agentId: string, members?: AgentMember[]) {
  const member = members?.find((m) => m.agent_id === agentId);
  return {
    displayName: member?.display_name ?? agentId,
    agentType: member?.agent_type ?? agentId,
    isRedTeam: member?.is_red_team ?? isRedTeamAgent(agentId),
  };
}

function noveltyColor(score: number): string {
  if (score > 0.6) return '#22C55E';
  if (score > 0.3) return '#F59E0B';
  return '#6B7280';
}

export function PostCard({ post, members }: PostCardProps) {
  const agent = resolveAgent(post.agent_id, members);
  const color = getAgentColor(agent.agentType, agent.isRedTeam);
  const triggerRules = post.triggered_by.filter((r) => r !== 'seed_phase');
  const nColor = noveltyColor(post.novelty_score);

  return (
    <div
      className={cn(
        'bg-bg-surface rounded-lg p-5',
        agent.isRedTeam && 'bg-red-500/[0.03]',
      )}
      style={{ borderLeft: `3px solid ${color}` }}
    >
      {/* Header row */}
      <div className="flex items-center gap-3 flex-wrap">
        <AgentAvatar
          displayName={agent.displayName}
          agentType={agent.agentType}
          isRedTeam={agent.isRedTeam}
          size="md"
        />
        <div className="flex items-center gap-2 flex-wrap min-w-0">
          <span className="font-semibold text-sm" style={{ color }}>
            {agent.displayName}
          </span>
          <span className="text-xs text-text-muted">@{agent.agentType}</span>
          <StanceBadge stance={post.stance} />
          <PhaseBadge phase={post.phase} />
        </div>
      </div>

      {/* Trigger rules */}
      {triggerRules.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mt-2 ml-[52px]">
          {triggerRules.map((rule) => (
            <span
              key={rule}
              className="text-xs text-text-muted px-1.5 py-0.5 rounded-sm"
              style={{
                backgroundColor: `${TRIGGER_COLORS[rule] ?? '#6B7280'}1A`,
                color: TRIGGER_COLORS[rule] ?? '#6B7280',
              }}
            >
              {rule.replace(/_/g, ' ')}
            </span>
          ))}
        </div>
      )}

      {/* Content */}
      <div className="mt-3 max-w-[680px]">
        <MarkdownContent content={post.content} />
      </div>

      {/* Key Claims */}
      {post.key_claims.length > 0 && (
        <PostClaimsBlock claims={post.key_claims} />
      )}

      {/* Questions Raised */}
      {post.questions_raised.length > 0 && (
        <PostQuestionsBlock questions={post.questions_raised} />
      )}

      {/* Citations */}
      {post.citations.length > 0 && (
        <PostCitationsBlock citations={post.citations} />
      )}

      {/* Novelty score */}
      <div className="mt-4 flex items-center gap-3">
        <span className="text-xs text-text-muted">Novelty</span>
        <div className="flex-1 max-w-[200px]">
          <Progress
            value={post.novelty_score * 100}
            color={nColor}
            className="h-1.5"
          />
        </div>
        <span className="text-xs text-text-muted">
          {Math.round(post.novelty_score * 100)}%
        </span>
      </div>
    </div>
  );
}
