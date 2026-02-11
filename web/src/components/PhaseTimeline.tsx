import type { Phase, PhaseSignal } from '../types/deliberation';
import { PHASE_LABELS } from './agentMeta';

interface PhaseTimelineProps {
  currentPhase: Phase;
  phaseHistory: PhaseSignal[];
}

const PHASES: Phase[] = ['explore', 'debate', 'deepen', 'converge', 'synthesis'];

const PHASE_ORDER: Record<Phase, number> = {
  explore: 0,
  debate: 1,
  deepen: 2,
  converge: 3,
  synthesis: 4,
};

export function PhaseTimeline({ currentPhase, phaseHistory }: PhaseTimelineProps) {
  const currentIdx = PHASE_ORDER[currentPhase] ?? 0;
  const latestSignal = phaseHistory[phaseHistory.length - 1];
  const confidence = latestSignal?.confidence ?? 1.0;

  return (
    <div className="phase-timeline">
      <h2 className="panel-title">Phase</h2>
      <div className="phase-list">
        {PHASES.map((phase, i) => {
          const isCurrent = phase === currentPhase;
          const isCompleted = i < currentIdx;
          const isFuture = i > currentIdx;

          return (
            <div
              key={phase}
              className={`phase-item ${isCurrent ? 'current' : ''} ${isCompleted ? 'completed' : ''} ${isFuture ? 'future' : ''}`}
            >
              <div className="phase-dot">
                {isCompleted ? '✓' : isCurrent ? '●' : '○'}
              </div>
              <div className="phase-label">
                {PHASE_LABELS[phase]}
                {isCurrent && (
                  <span className="phase-confidence">
                    {(confidence * 100).toFixed(0)}%
                  </span>
                )}
              </div>
              {isCurrent && latestSignal?.observation && (
                <div className="phase-observation">{latestSignal.observation}</div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
