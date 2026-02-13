import { cn } from '@/lib/utils';
import { PHASE_COLORS, PHASE_LABELS } from '@/lib/agentColors';
import type { Phase, PhaseSignal } from '@/types/deliberation';

interface PhaseTimelineProps {
  currentPhase: Phase;
  phaseHistory: PhaseSignal[];
}

const PHASES: Phase[] = ['explore', 'debate', 'deepen', 'converge', 'synthesis'];

export function PhaseTimeline({ currentPhase, phaseHistory }: PhaseTimelineProps) {
  const latestSignal = phaseHistory[phaseHistory.length - 1];
  const confidence = latestSignal?.confidence ?? 1.0;

  const visitedPhases = new Set<Phase>();
  for (const signal of phaseHistory) {
    visitedPhases.add(signal.current_phase);
  }
  visitedPhases.add(currentPhase);

  return (
    <div className="space-y-2">
      {PHASES.map((phase, idx) => {
        const isCurrent = phase === currentPhase;
        const isVisited = visitedPhases.has(phase) && !isCurrent;
        const color = PHASE_COLORS[phase] || '#6B7280';

        return (
          <div key={phase} className="flex items-start gap-3">
            {/* Dot + connector line */}
            <div className="flex flex-col items-center">
              <div
                className={cn(
                  'w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold shrink-0 transition-all',
                  isCurrent && 'ring-2 ring-offset-2 ring-offset-bg-primary',
                  !isCurrent && !isVisited && 'opacity-40',
                )}
                style={{
                  backgroundColor: isCurrent || isVisited ? color : 'transparent',
                  borderColor: color,
                  border: !isCurrent && !isVisited ? `1px solid ${color}` : 'none',
                  ...(isCurrent ? { ringColor: color } : {}),
                }}
              >
                {isVisited ? (
                  <span className="text-white text-xs">&#10003;</span>
                ) : isCurrent ? (
                  <span className="text-white text-xs">&#9679;</span>
                ) : null}
              </div>
              {idx < PHASES.length - 1 && (
                <div
                  className="w-px h-4"
                  style={{ backgroundColor: isVisited || isCurrent ? color : 'var(--color-border-default)' }}
                />
              )}
            </div>

            {/* Label */}
            <div className="flex-1 pb-1">
              <div className={cn(
                'text-sm font-semibold tracking-wider',
                isCurrent ? 'text-text-primary' : isVisited ? 'text-text-secondary' : 'text-text-muted',
              )}>
                {PHASE_LABELS[phase]}
                {isCurrent && (
                  <span className="ml-2 text-xs font-normal text-text-muted">
                    {(confidence * 100).toFixed(0)}%
                  </span>
                )}
              </div>
              {isCurrent && latestSignal?.observation && (
                <div className="text-xs text-text-muted mt-0.5 leading-snug">
                  {latestSignal.observation}
                </div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
