import { motion } from 'motion/react';
import { PHASE_COLORS, PHASE_LABELS } from '@/lib/agentColors';
import type { Phase } from '@/types/deliberation';

interface PhaseTransitionProps {
  phase: Phase;
  confidence?: number;
  observation?: string | null;
}

export function PhaseTransition({ phase, confidence, observation }: PhaseTransitionProps) {
  const color = PHASE_COLORS[phase] ?? '#6B7280';
  const label = PHASE_LABELS[phase] ?? phase;

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.98 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.4, ease: 'easeOut' }}
      className="w-full py-6 my-4 px-6 rounded-lg"
      style={{
        backgroundColor: `${color}14`,
        borderLeft: `3px solid ${color}`,
      }}
    >
      <div className="flex items-baseline gap-3 flex-wrap">
        <span className="text-2xl font-bold" style={{ color }}>
          {label}
        </span>
        {confidence != null && (
          <span className="text-sm text-text-secondary">
            Confidence: {Math.round(confidence * 100)}%
          </span>
        )}
      </div>
      {observation && (
        <p className="mt-2 text-sm text-text-muted italic">
          {observation}
        </p>
      )}
    </motion.div>
  );
}
