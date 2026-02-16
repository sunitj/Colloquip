import type { AgentDetail } from '@/types/platform';
import { AgentAvatar } from '@/components/shared/AgentAvatar';
import { Badge } from '@/components/ui/badge';

interface AgentProfileHeaderProps {
  agent: AgentDetail;
}

function statusVariant(status: string) {
  switch (status) {
    case 'active':
      return 'success' as const;
    case 'inactive':
    case 'disabled':
      return 'secondary' as const;
    case 'error':
      return 'destructive' as const;
    default:
      return 'outline' as const;
  }
}

export function AgentProfileHeader({ agent }: AgentProfileHeaderProps) {
  return (
    <div className="flex flex-col sm:flex-row items-start gap-5">
      {/* Avatar */}
      <AgentAvatar
        displayName={agent.display_name}
        agentType={agent.agent_type}
        isRedTeam={agent.is_red_team}
        size="xl"
      />

      {/* Info */}
      <div className="flex-1 min-w-0">
        {/* Name row */}
        <div className="flex flex-wrap items-center gap-3">
          <h1 className="text-2xl font-bold text-text-primary">
            {agent.display_name}
          </h1>
          <Badge variant={statusVariant(agent.status)}>
            {agent.status}
          </Badge>
          <Badge variant="outline">v{agent.version}</Badge>
          {agent.is_red_team && (
            <Badge variant="destructive">Red Team</Badge>
          )}
        </div>

        {/* Agent type */}
        <p className="mt-1 text-sm text-text-muted">@{agent.agent_type}</p>

        {/* Expertise tags */}
        {agent.expertise_tags.length > 0 && (
          <div className="mt-3 flex flex-wrap gap-1.5">
            {agent.expertise_tags.map((tag) => (
              <Badge key={tag} variant="secondary">
                {tag}
              </Badge>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
