import { useEffect, useState } from 'react';
import { cn } from '@/lib/utils';
import type { Phase } from '@/types/deliberation';

const PHASE_CONFIG: Record<Phase, { label: string; color: string; gradient: string }> = {
  explore: { label: 'Explore', color: '#3B82F6', gradient: 'from-blue-500/20 via-blue-500/5 to-transparent' },
  debate: { label: 'Debate', color: '#EF4444', gradient: 'from-red-500/20 via-red-500/5 to-transparent' },
  deepen: { label: 'Deepen', color: '#F59E0B', gradient: 'from-amber-500/20 via-amber-500/5 to-transparent' },
  converge: { label: 'Converge', color: '#22C55E', gradient: 'from-green-500/20 via-green-500/5 to-transparent' },
  synthesis: { label: 'Synthesis', color: '#A855F7', gradient: 'from-purple-500/20 via-purple-500/5 to-transparent' },
};

interface PhaseTransitionBannerProps {
  phase: Phase;
  previousPhase: Phase | null;
}

export function PhaseTransitionBanner({ phase, previousPhase }: PhaseTransitionBannerProps) {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    if (previousPhase !== null && previousPhase !== phase) {
      setVisible(true);
      const timer = setTimeout(() => setVisible(false), 3000);
      return () => clearTimeout(timer);
    }
  }, [phase, previousPhase]);

  if (!visible) return null;

  const config = PHASE_CONFIG[phase];

  return (
    <div
      className={cn(
        'absolute top-0 left-0 right-0 z-10 flex items-center justify-center py-3',
        'bg-gradient-to-b',
        config.gradient,
        'animate-[fadeIn_0.3s_ease-out]',
      )}
      role="status"
      aria-live="polite"
    >
      <div
        className="px-4 py-1.5 rounded-full text-xs font-bold uppercase tracking-widest text-white/90 border border-white/10"
        style={{ backgroundColor: `${config.color}30` }}
      >
        Phase: {config.label}
      </div>
    </div>
  );
}
