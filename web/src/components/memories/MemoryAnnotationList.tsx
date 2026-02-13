import { CheckCircle2, AlertTriangle, XCircle, Info } from 'lucide-react';
import { timeAgo } from '@/lib/utils';
import type { MemoryAnnotation, AnnotationType } from '@/types/platform';
import { Badge } from '@/components/ui/badge';

interface MemoryAnnotationListProps {
  annotations: MemoryAnnotation[];
}

const ANNOTATION_CONFIG: Record<
  AnnotationType,
  { label: string; variant: 'success' | 'warning' | 'destructive' | 'default'; icon: React.ReactNode }
> = {
  confirmed: {
    label: 'Confirmed',
    variant: 'success',
    icon: <CheckCircle2 className="h-3.5 w-3.5" />,
  },
  correction: {
    label: 'Correction',
    variant: 'warning',
    icon: <AlertTriangle className="h-3.5 w-3.5" />,
  },
  outdated: {
    label: 'Outdated',
    variant: 'destructive',
    icon: <XCircle className="h-3.5 w-3.5" />,
  },
  context: {
    label: 'Context',
    variant: 'default',
    icon: <Info className="h-3.5 w-3.5" />,
  },
};

export function MemoryAnnotationList({ annotations }: MemoryAnnotationListProps) {
  if (annotations.length === 0) {
    return (
      <p className="py-4 text-center text-sm text-text-muted">
        No annotations yet.
      </p>
    );
  }

  return (
    <div className="space-y-3">
      {annotations.map((annotation) => {
        const config = ANNOTATION_CONFIG[annotation.annotation_type];

        return (
          <div
            key={annotation.id}
            className="rounded-radius-md border border-border-default bg-bg-elevated p-4"
          >
            <div className="flex items-center justify-between gap-2">
              <Badge variant={config.variant} className="gap-1">
                {config.icon}
                {config.label}
              </Badge>
              <span className="text-xs text-text-muted">
                {timeAgo(annotation.created_at)}
              </span>
            </div>

            <p className="mt-2 text-sm text-text-secondary">
              {annotation.content}
            </p>

            <p className="mt-2 text-xs text-text-muted">
              by {annotation.created_by}
            </p>
          </div>
        );
      })}
    </div>
  );
}
