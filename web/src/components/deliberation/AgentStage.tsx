import { useMemo } from 'react';
import { cn } from '@/lib/utils';
import { getAgentColor } from '@/lib/agentColors';
import { AgentAvatar } from '@/components/shared/AgentAvatar';
import { StanceBadge } from '@/components/shared/StanceBadge';
import {
  TooltipProvider,
  Tooltip,
  TooltipTrigger,
  TooltipContent,
} from '@/components/ui/tooltip';
import type { Post, AgentStance } from '@/types/deliberation';
import type { AgentMember } from '@/types/platform';

interface AgentStageProps {
  members: AgentMember[];
  posts: Post[];
}

interface AgentStats {
  postCount: number;
  lastStance: AgentStance | null;
  isActive: boolean;
}

export function AgentStage({ members, posts }: AgentStageProps) {
  const agentStats = useMemo(() => {
    const stats = new Map<string, AgentStats>();

    // Initialize for all members
    for (const member of members) {
      stats.set(member.agent_id, {
        postCount: 0,
        lastStance: null,
        isActive: false,
      });
    }

    // Count posts and find last stance
    for (const post of posts) {
      const existing = stats.get(post.agent_id);
      if (existing) {
        existing.postCount += 1;
        existing.lastStance = post.stance;
      } else {
        stats.set(post.agent_id, {
          postCount: 1,
          lastStance: post.stance,
          isActive: false,
        });
      }
    }

    // Determine active agents (posted in last 2 posts)
    const recentPosts = posts.slice(-2);
    const recentAgentIds = new Set(recentPosts.map((p) => p.agent_id));
    for (const agentId of recentAgentIds) {
      const existing = stats.get(agentId);
      if (existing) {
        existing.isActive = true;
      }
    }

    return stats;
  }, [members, posts]);

  return (
    <TooltipProvider>
      <div className="flex flex-wrap gap-3">
        {members.map((member) => {
          const stats = agentStats.get(member.agent_id);
          const isActive = stats?.isActive ?? false;
          const color = getAgentColor(member.agent_type, member.is_red_team);

          return (
            <Tooltip key={member.agent_id}>
              <TooltipTrigger asChild>
                <div className="flex flex-col items-center gap-1 cursor-default">
                  <div
                    className={cn(
                      'rounded-full transition-all duration-200',
                      isActive
                        ? 'opacity-100 ring-2 ring-offset-2 ring-offset-bg-surface'
                        : 'opacity-60',
                    )}
                    style={isActive ? { '--tw-ring-color': color } as React.CSSProperties : undefined}
                  >
                    <AgentAvatar
                      displayName={member.display_name}
                      agentType={member.agent_type}
                      isRedTeam={member.is_red_team}
                      size="sm"
                    />
                  </div>
                  <span className="text-xs text-text-muted truncate max-w-[56px] text-center">
                    {member.display_name.split(' ')[0]}
                  </span>
                </div>
              </TooltipTrigger>
              <TooltipContent>
                <div className="space-y-1">
                  <p className="font-medium" style={{ color }}>
                    {member.display_name}
                  </p>
                  <p className="text-text-muted">@{member.agent_type}</p>
                  <p className="text-text-secondary">
                    {stats?.postCount ?? 0} post{(stats?.postCount ?? 0) !== 1 ? 's' : ''}
                  </p>
                  {stats?.lastStance && (
                    <div className="pt-1">
                      <StanceBadge stance={stats.lastStance} />
                    </div>
                  )}
                </div>
              </TooltipContent>
            </Tooltip>
          );
        })}
      </div>
    </TooltipProvider>
  );
}
