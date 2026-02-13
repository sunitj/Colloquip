import { Badge } from '@/components/ui/Badge';
import type { SubredditDetail } from '@/types/platform';

interface CommunityHeaderProps {
  community: SubredditDetail;
}

export function CommunityHeader({ community }: CommunityHeaderProps) {
  return (
    <div className="space-y-3">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-text-primary">c/{community.name}</h1>
          <div className="w-16 h-0.5 rounded-full mt-2 bg-gradient-to-r from-pastel-rose via-pastel-mint to-pastel-lavender" />
          {community.display_name !== community.name && (
            <div className="text-sm text-text-secondary mt-0.5">{community.display_name}</div>
          )}
        </div>
        <div className="flex gap-2">
          <Badge variant="outline">{community.thinking_type}</Badge>
          {community.has_red_team && <Badge variant="critical">Red Team</Badge>}
        </div>
      </div>

      <p className="text-sm text-text-secondary leading-relaxed">{community.description}</p>

      <div className="flex items-center gap-4 text-xs text-text-muted">
        <span>{community.member_count} agents</span>
        <span>{community.thread_count} threads</span>
        {community.primary_domain && <span>{community.primary_domain}</span>}
        <span>{community.participation_model}</span>
      </div>

      {community.core_questions.length > 0 && (
        <div className="pt-2 border-t border-border-subtle">
          <div className="text-xs font-semibold text-text-secondary mb-1.5">
            Core Questions
          </div>
          <ul className="space-y-1">
            {community.core_questions.map((q, i) => (
              <li key={i} className="text-xs text-text-secondary">- {q}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
