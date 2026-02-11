import type { Phase, PhaseSignal } from '../types/deliberation';
import { PHASE_LABELS } from './agentMeta';

interface PhaseTimelineProps {
  currentPhase: Phase;
  phaseHistory: PhaseSignal[];
}

const PHASES: Phase[] = ['explore', 'debate', 'deepen', 'converge', 'synthesis'];

export function PhaseTimeline({ currentPhase, phaseHistory }: PhaseTimelineProps) {
  const latestSignal = phaseHistory[phaseHistory.length - 1];
  const confidence = latestSignal?.confidence ?? 1.0;

  // Track which phases have actually been visited (emergent order, not linear)
  const visitedPhases = new Set<Phase>();
  for (const signal of phaseHistory) {
    visitedPhases.add(signal.current_phase);
  }
  // Current phase is always considered visited
  visitedPhases.add(currentPhase);

  return (
    <div className="phase-timeline">
      <h2 className="panel-title">Phase</h2>
      <div className="phase-list">
        {PHASES.map((phase) => {
          const isCurrent = phase === currentPhase;
          const isVisited = visitedPhases.has(phase) && !isCurrent;

          return (
            <div
              key={phase}
              className={`phase-item ${isCurrent ? 'current' : ''} ${isVisited ? 'completed' : ''} ${!isCurrent && !isVisited ? 'future' : ''}`}
            >
              <div className="phase-dot">
                {isVisited ? '✓' : isCurrent ? '●' : '○'}
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
