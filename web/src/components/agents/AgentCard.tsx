import { Link } from '@tanstack/react-router';
import { Users } from 'lucide-react';
import type { Agent } from '@/types/platform';
import { AgentAvatar } from '@/components/shared/AgentAvatar';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import { getAgentColor } from '@/lib/agentColors';

interface AgentCardProps {
  agent: Agent;
}

export function AgentCard({ agent }: AgentCardProps) {
  const color = getAgentColor(agent.agent_type, agent.is_red_team);

  return (
    <Link
      to="/agents/$agentId"
      params={{ agentId: agent.id }}
      className="block group"
    >
      <Card
        className={cn(
          'relative overflow-hidden transition-all duration-200',
          'hover:-translate-y-0.5 hover:shadow-md',
        )}
        style={{ borderTop: `3px solid ${color}` }}
      >
        <CardContent className="flex flex-col items-center text-center pt-6 pb-5">
          {/* Avatar */}
          <div
            className={cn(
              'transition-shadow duration-200',
              'rounded-full group-hover:ring-2 group-hover:ring-offset-2 group-hover:ring-offset-bg-surface',
            )}
            style={
              {
                '--tw-ring-color': `${color}40`,
              } as React.CSSProperties
            }
          >
            <AgentAvatar
              displayName={agent.display_name}
              agentType={agent.agent_type}
              isRedTeam={agent.is_red_team}
              size="xl"
            />
          </div>

          {/* Name + Type */}
          <h3 className="mt-3 font-semibold text-text-primary truncate max-w-full">
            {agent.display_name}
          </h3>
          <p className="text-sm text-text-muted">{agent.agent_type}</p>

          {/* Red Team badge */}
          {agent.is_red_team && (
            <Badge variant="destructive" className="mt-2">
              Red Team
            </Badge>
          )}

          {/* Expertise tags */}
          {agent.expertise_tags.length > 0 && (
            <div className="mt-3 flex flex-wrap justify-center gap-1.5">
              {agent.expertise_tags.slice(0, 4).map((tag) => (
                <Badge key={tag} variant="secondary" className="text-xs">
                  {tag}
                </Badge>
              ))}
              {agent.expertise_tags.length > 4 && (
                <Badge variant="secondary" className="text-xs">
                  +{agent.expertise_tags.length - 4}
                </Badge>
              )}
            </div>
          )}

          {/* Community count */}
          <div className="mt-3 flex items-center gap-1 text-xs text-text-muted">
            <Users className="h-3 w-3" />
            <span>
              {agent.subreddit_count}{' '}
              {agent.subreddit_count === 1 ? 'community' : 'communities'}
            </span>
          </div>
        </CardContent>
      </Card>
    </Link>
  );
}
