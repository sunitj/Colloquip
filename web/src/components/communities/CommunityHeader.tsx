import { ChevronDown, HelpCircle, Users, MessageSquare } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import {
  Collapsible,
  CollapsibleTrigger,
  CollapsibleContent,
} from '@/components/ui/collapsible';
import type { SubredditDetail } from '@/types/platform';

interface CommunityHeaderProps {
  community: SubredditDetail;
}

export function CommunityHeader({ community }: CommunityHeaderProps) {
  return (
    <div className="space-y-4">
      {/* Title block */}
      <div>
        <h1 className="text-2xl font-bold text-text-primary">
          {community.display_name}
        </h1>
        <p className="text-sm text-text-accent mt-0.5">
          c/{community.name}
        </p>
      </div>

      {/* Description */}
      {community.description && (
        <p className="text-text-secondary text-sm leading-relaxed max-w-2xl">
          {community.description}
        </p>
      )}

      {/* Badges row */}
      <div className="flex flex-wrap items-center gap-2">
        <Badge variant="secondary">
          {community.thinking_type}
        </Badge>
        <Badge variant="secondary">
          {community.participation_model}
        </Badge>
        {community.has_red_team && (
          <Badge variant="destructive">
            Red Team
          </Badge>
        )}
        {community.primary_domain && (
          <Badge variant="outline">
            {community.primary_domain}
          </Badge>
        )}
      </div>

      {/* Stats row */}
      <div className="flex items-center gap-6 text-sm text-text-secondary">
        <span className="inline-flex items-center gap-1.5">
          <Users className="h-4 w-4 text-text-muted" />
          {community.member_count} agent{community.member_count !== 1 ? 's' : ''}
        </span>
        <span className="inline-flex items-center gap-1.5">
          <MessageSquare className="h-4 w-4 text-text-muted" />
          {community.thread_count} thread{community.thread_count !== 1 ? 's' : ''}
        </span>
        {community.max_cost_per_thread_usd > 0 && (
          <span className="text-text-muted">
            Max ${community.max_cost_per_thread_usd.toFixed(2)}/thread
          </span>
        )}
      </div>

      {/* Core questions */}
      {community.core_questions && community.core_questions.length > 0 && (
        <Collapsible defaultOpen>
          <CollapsibleTrigger className="group">
            <HelpCircle className="h-4 w-4 text-text-muted" />
            <span>Core Questions ({community.core_questions.length})</span>
            <ChevronDown className="h-4 w-4 text-text-muted transition-transform" />
          </CollapsibleTrigger>
          <CollapsibleContent>
            <blockquote className="mt-3 space-y-2 border-l-2 border-border-default pl-4">
              {community.core_questions.map((q, i) => (
                <p
                  key={i}
                  className="text-sm text-text-muted italic leading-relaxed"
                >
                  {q}
                </p>
              ))}
            </blockquote>
          </CollapsibleContent>
        </Collapsible>
      )}

      {/* Decision context */}
      {community.decision_context && (
        <p className="text-xs text-text-muted bg-bg-elevated/40 rounded-lg px-4 py-3 leading-relaxed max-w-2xl">
          {community.decision_context}
        </p>
      )}
    </div>
  );
}
