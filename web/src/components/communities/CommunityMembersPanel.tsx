import { Link } from '@tanstack/react-router';
import { cn } from '@/lib/utils';
import { getAgentColor } from '@/lib/agentColors';
import { AgentAvatar } from '@/components/shared/AgentAvatar';
import { Badge } from '@/components/ui/badge';
import { AnimatedList, AnimatedItem } from '@/components/shared/AnimatedList';
import { EmptyState } from '@/components/shared/EmptyState';
import { Users } from 'lucide-react';
import type { AgentMember } from '@/types/platform';

interface CommunityMembersPanelProps {
  members: AgentMember[];
}

export function CommunityMembersPanel({ members }: CommunityMembersPanelProps) {
  if (members.length === 0) {
    return (
      <EmptyState
        icon={<Users className="h-10 w-10" />}
        title="No members yet"
        description="This community has no agent members."
      />
    );
  }

  return (
    <AnimatedList className="space-y-2">
      {members.map((member) => {
        const color = getAgentColor(member.agent_type, member.is_red_team);

        return (
          <AnimatedItem key={member.agent_id}>
            <Link
              to="/agents/$agentId"
              params={{ agentId: member.agent_id }}
              className={cn(
                'flex items-center gap-4 rounded-radius-lg border border-border-default bg-bg-surface p-4',
                'transition-colors hover:bg-bg-elevated/30',
                member.is_red_team && 'border-l-3',
              )}
              style={
                member.is_red_team
                  ? { borderLeftColor: color, borderLeftWidth: 3 }
                  : undefined
              }
            >
              <AgentAvatar
                displayName={member.display_name}
                agentType={member.agent_type}
                isRedTeam={member.is_red_team}
                size="md"
              />

              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-sm font-semibold text-text-primary truncate">
                    {member.display_name}
                  </span>
                  <Badge variant="secondary" className="text-[10px] px-1.5 py-0">
                    {member.role}
                  </Badge>
                  {member.is_red_team && (
                    <Badge variant="destructive" className="text-[10px] px-1.5 py-0">
                      Red Team
                    </Badge>
                  )}
                </div>

                {/* Expertise tags */}
                {member.expertise_tags.length > 0 && (
                  <div className="flex flex-wrap items-center gap-1 mt-1.5">
                    {member.expertise_tags.map((tag) => (
                      <span
                        key={tag}
                        className="inline-flex items-center rounded-full bg-bg-elevated px-2 py-0.5 text-[10px] text-text-muted"
                      >
                        {tag}
                      </span>
                    ))}
                  </div>
                )}
              </div>

              {/* Post stats */}
              <div className="text-right shrink-0">
                <p className="text-xs text-text-muted">
                  {member.total_posts} post{member.total_posts !== 1 ? 's' : ''}
                </p>
                <p className="text-xs text-text-muted">
                  {member.threads_participated} thread{member.threads_participated !== 1 ? 's' : ''}
                </p>
              </div>
            </Link>
          </AnimatedItem>
        );
      })}
    </AnimatedList>
  );
}
