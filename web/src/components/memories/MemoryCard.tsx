import { Link } from '@tanstack/react-router';
import { Brain, MessageSquareText, Users } from 'lucide-react';
import { cn, timeAgo } from '@/lib/utils';
import type { Memory } from '@/types/platform';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';

interface MemoryCardProps {
  memory: Memory;
}

function confidenceColor(value: number): string {
  if (value > 0.7) return '#22C55E';
  if (value > 0.4) return '#F59E0B';
  return '#EF4444';
}

function qualityVariant(quality: string) {
  switch (quality.toLowerCase()) {
    case 'strong':
    case 'high':
      return 'success' as const;
    case 'moderate':
    case 'medium':
      return 'warning' as const;
    case 'weak':
    case 'low':
      return 'destructive' as const;
    default:
      return 'secondary' as const;
  }
}

export function MemoryCard({ memory }: MemoryCardProps) {
  const confidencePct = Math.round(memory.confidence * 100);

  return (
    <div
      className={cn(
        'rounded-lg border border-border-default bg-bg-surface p-5',
        'transition-all duration-200 ease-out',
        'hover:border-border-accent hover:shadow-md',
      )}
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <h3 className="font-semibold text-text-primary line-clamp-2">
            {memory.topic}
          </h3>
        </div>

        {memory.annotations.length > 0 && (
          <Badge variant="secondary" className="shrink-0">
            <MessageSquareText className="mr-1 h-3 w-3" />
            {memory.annotations.length}
          </Badge>
        )}
      </div>

      {/* Confidence bar */}
      <div className="mt-3 flex items-center gap-3">
        <Progress
          value={confidencePct}
          color={confidenceColor(memory.confidence)}
          className="flex-1"
        />
        <span
          className="shrink-0 text-xs font-medium"
          style={{ color: confidenceColor(memory.confidence) }}
        >
          {confidencePct}%
        </span>
      </div>

      {/* Key conclusions */}
      {memory.key_conclusions.length > 0 && (
        <ul className="mt-3 space-y-1">
          {memory.key_conclusions.slice(0, 3).map((conclusion, i) => (
            <li
              key={i}
              className="flex items-start gap-2 text-sm text-text-secondary"
            >
              <span className="mt-1.5 inline-block h-1.5 w-1.5 shrink-0 rounded-full bg-text-muted" />
              <span className="line-clamp-2">{conclusion}</span>
            </li>
          ))}
          {memory.key_conclusions.length > 3 && (
            <li className="text-xs text-text-muted pl-3.5">
              +{memory.key_conclusions.length - 3} more
            </li>
          )}
        </ul>
      )}

      {/* Meta badges */}
      <div className="mt-3 flex flex-wrap items-center gap-2">
        <Badge variant={qualityVariant(memory.evidence_quality)}>
          {memory.evidence_quality}
        </Badge>
        <Badge variant="secondary">{memory.confidence_level}</Badge>
        <Badge variant="secondary">{memory.template_type}</Badge>
      </div>

      {/* Agents involved */}
      {memory.agents_involved.length > 0 && (
        <div className="mt-3 flex items-center gap-1.5 text-xs text-text-muted">
          <Users className="h-3 w-3 shrink-0" />
          <span className="truncate">
            {memory.agents_involved.join(', ')}
          </span>
        </div>
      )}

      {/* Footer */}
      <div className="mt-3 flex items-center justify-between gap-2">
        <Link
          to="/c/$name"
          params={{ name: memory.subreddit_name }}
          className="inline-flex items-center gap-1 text-xs font-medium text-text-accent hover:underline"
        >
          <Brain className="h-3 w-3" />
          c/{memory.subreddit_name}
        </Link>

        <span className="text-xs text-text-muted">
          {timeAgo(memory.created_at)}
        </span>
      </div>
    </div>
  );
}
