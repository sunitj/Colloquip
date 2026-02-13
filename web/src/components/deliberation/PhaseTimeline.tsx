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
    <div className="space-y-1">
      {PHASES.map((phase, idx) => {
        const isCurrent = phase === currentPhase;
        const isVisited = visitedPhases.has(phase) && !isCurrent;
        const color = PHASE_COLORS[phase] || '#94A3B8';

        return (
          <div key={phase} className="flex items-start gap-3">
            {/* Dot + connector line */}
            <div className="flex flex-col items-center">
              <div
                className={cn(
                  'w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold shrink-0 transition-all',
                  isCurrent && 'ring-2 ring-offset-1 ring-offset-bg-primary',
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
                  <span className="text-white text-[10px]">&#10003;</span>
                ) : isCurrent ? (
                  <span className="text-white text-[10px]">&#9679;</span>
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
                'text-xs font-semibold uppercase tracking-wider',
                isCurrent ? 'text-text-primary' : isVisited ? 'text-text-secondary' : 'text-text-muted',
              )}>
                {PHASE_LABELS[phase]}
                {isCurrent && (
                  <span className="ml-2 text-[10px] font-normal text-text-muted">
                    {(confidence * 100).toFixed(0)}%
                  </span>
                )}
              </div>
              {isCurrent && latestSignal?.observation && (
                <div className="text-[11px] text-text-muted mt-0.5 leading-snug">
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
