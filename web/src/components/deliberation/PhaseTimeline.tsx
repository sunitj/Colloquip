import { Check } from 'lucide-react';
import { PHASE_COLORS, PHASE_LABELS } from '@/lib/agentColors';
import type { Phase, PhaseSignal } from '@/types/deliberation';

interface PhaseTimelineProps {
  currentPhase: Phase;
  phaseHistory: PhaseSignal[];
}

const PHASES: Phase[] = ['explore', 'debate', 'deepen', 'converge', 'synthesis'];

export function PhaseTimeline({ currentPhase, phaseHistory }: PhaseTimelineProps) {
  const visitedPhases = new Set(phaseHistory.map((p) => p.current_phase));
  const currentIndex = PHASES.indexOf(currentPhase);

  // Find the confidence for each visited phase
  const phaseConfidence = new Map<Phase, number>();
  for (const signal of phaseHistory) {
    phaseConfidence.set(signal.current_phase, signal.confidence);
  }

  return (
    <div className="space-y-0">
      {PHASES.map((phase, index) => {
        const color = PHASE_COLORS[phase] ?? '#6B7280';
        const label = PHASE_LABELS[phase] ?? phase;
        const isCurrent = phase === currentPhase;
        const isVisited = visitedPhases.has(phase) && index < currentIndex;
        const isFuture = index > currentIndex && !visitedPhases.has(phase);
        const confidence = phaseConfidence.get(phase);

        return (
          <div key={phase} className="relative flex items-start gap-3 pb-6 last:pb-0">
            {/* Connecting line */}
            {index < PHASES.length - 1 && (
              <div
                className="absolute left-[11px] top-[24px] w-0.5 h-[calc(100%-12px)]"
                style={{
                  backgroundColor: isVisited || isCurrent
                    ? `${color}66`
                    : 'var(--color-border-subtle)',
                }}
              />
            )}

            {/* Dot */}
            <div className="relative z-10 shrink-0">
              {isVisited ? (
                <div
                  className="flex h-6 w-6 items-center justify-center rounded-full"
                  style={{ backgroundColor: `${color}33` }}
                >
                  <Check className="h-3.5 w-3.5" style={{ color }} />
                </div>
              ) : isCurrent ? (
                <div className="relative flex h-6 w-6 items-center justify-center">
                  <span
                    className="absolute inset-0 rounded-full animate-ping opacity-30"
                    style={{ backgroundColor: color }}
                  />
                  <span
                    className="relative h-3 w-3 rounded-full"
                    style={{ backgroundColor: color }}
                  />
                </div>
              ) : (
                <div
                  className="h-6 w-6 rounded-full border-2"
                  style={{
                    borderColor: isFuture
                      ? 'var(--color-border-subtle)'
                      : `${color}66`,
                  }}
                />
              )}
            </div>

            {/* Label */}
            <div className="min-w-0 pt-0.5">
              <p
                className="text-sm font-medium"
                style={{
                  color: isCurrent ? color : isVisited ? `${color}99` : 'var(--color-text-muted)',
                }}
              >
                {label}
              </p>
              {isCurrent && confidence != null && (
                <p className="text-xs text-text-secondary mt-0.5">
                  {Math.round(confidence * 100)}% confidence
                </p>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
