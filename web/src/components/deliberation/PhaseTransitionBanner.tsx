import { useEffect, useState } from 'react';
import { cn } from '@/lib/utils';
import type { Phase } from '@/types/deliberation';

const PHASE_CONFIG: Record<Phase, { label: string; color: string; gradient: string }> = {
  explore: { label: 'Explore', color: '#7CB9E8', gradient: 'from-[#EDF6FA]/80 via-[#EDF6FA]/30 to-transparent' },
  debate: { label: 'Debate', color: '#E8788A', gradient: 'from-[#FFF0F3]/80 via-[#FFF0F3]/30 to-transparent' },
  deepen: { label: 'Deepen', color: '#F0C060', gradient: 'from-[#FFFBEC]/80 via-[#FFFBEC]/30 to-transparent' },
  converge: { label: 'Converge', color: '#5EBD8A', gradient: 'from-[#EDFAF4]/80 via-[#EDFAF4]/30 to-transparent' },
  synthesis: { label: 'Synthesis', color: '#B49ADE', gradient: 'from-[#F3EFFA]/80 via-[#F3EFFA]/30 to-transparent' },
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
        className="px-4 py-1.5 rounded-full text-xs font-bold uppercase tracking-widest shadow-sm"
        style={{ backgroundColor: `${config.color}15`, color: config.color }}
      >
        Phase: {config.label}
      </div>
    </div>
  );
}
