import { StatusBadge } from '@/components/shared/StatusBadge';
import { PhaseBadge } from '@/components/shared/PhaseBadge';

interface ThreadHeaderProps {
  title: string;
  hypothesis?: string;
  status: string;
  phase: string;
}

export function ThreadHeader({ title, hypothesis, status, phase }: ThreadHeaderProps) {
  return (
    <div className="space-y-2">
      <div className="flex items-center gap-3 flex-wrap">
        <h2 className="text-xl font-semibold text-text-primary">{title}</h2>
        <StatusBadge status={status} />
        <PhaseBadge phase={phase} />
      </div>
      {hypothesis && (
        <p className="text-text-secondary text-sm leading-relaxed">
          {hypothesis}
        </p>
      )}
    </div>
  );
}
