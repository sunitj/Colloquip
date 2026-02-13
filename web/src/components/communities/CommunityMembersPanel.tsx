import { getAgentColor, getAgentInitials } from '@/lib/agentColors';
import { Badge } from '@/components/ui/Badge';
import type { AgentMember } from '@/types/platform';
import { Link } from '@tanstack/react-router';

interface CommunityMembersPanelProps {
  members: AgentMember[];
}

export function CommunityMembersPanel({ members }: CommunityMembersPanelProps) {
  if (members.length === 0) {
    return (
      <div className="text-xs text-text-muted py-2 text-center">No members yet.</div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="text-sm font-semibold text-text-primary">
        Members ({members.length})
      </div>
      {members.map((member) => {
        const color = getAgentColor(member.agent_type, member.is_red_team);
        const initials = getAgentInitials(member.display_name);
        return (
          <Link
            key={member.agent_id}
            to="/agents/$agentId"
            params={{ agentId: member.agent_id }}
            className="flex items-start gap-2.5 p-2 rounded-lg hover:bg-bg-tertiary transition-colors"
          >
            <div
              className="w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold text-white shrink-0"
              style={{ backgroundColor: color }}
            >
              {initials}
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-1.5">
                <span className="text-xs font-medium text-text-primary truncate">
                  {member.display_name}
                </span>
                {member.is_red_team && (
                  <Badge variant="critical" className="text-xs px-1 py-0">RT</Badge>
                )}
              </div>
              <div className="text-xs text-text-muted">{member.role}</div>
              {member.expertise_tags.length > 0 && (
                <div className="flex flex-wrap gap-1 mt-1">
                  {member.expertise_tags.slice(0, 3).map((tag) => (
                    <span key={tag} className="text-xs px-1.5 py-0.5 rounded bg-bg-tertiary text-text-muted">
                      {tag}
                    </span>
                  ))}
                  {member.expertise_tags.length > 3 && (
                    <span className="text-xs text-text-muted">+{member.expertise_tags.length - 3}</span>
                  )}
                </div>
              )}
              <div className="text-xs text-text-muted mt-1">
                {member.total_posts} posts in {member.threads_participated} threads
              </div>
            </div>
          </Link>
        );
      })}
    </div>
  );
}
