import { useMemo, useRef, useEffect } from 'react';
import { AnimatePresence, motion } from 'motion/react';
import {
  Zap,
  ShieldAlert,
  GitBranch,
  ArrowUpRight,
  MessageSquareWarning,
  Sparkles,
  User,
} from 'lucide-react';
import { PHASE_COLORS, PHASE_LABELS, TRIGGER_COLORS } from '@/lib/agentColors';
import type { Post, EnergyUpdate, PhaseSignal, Phase } from '@/types/deliberation';
import type { AgentMember } from '@/types/platform';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type AhaType =
  | 'phase_transition'
  | 'red_team_fires'
  | 'energy_spike'
  | 'energy_critical'
  | 'bridge_connection'
  | 'novelty_breakthrough'
  | 'human_intervention';

export interface AhaMoment {
  id: string;
  type: AhaType;
  title: string;
  description: string;
  color: string;
  timestamp: string;
  turn?: number;
}

// ---------------------------------------------------------------------------
// Detection logic
// ---------------------------------------------------------------------------

const AHA_ICONS: Record<AhaType, React.ComponentType<{ className?: string }>> = {
  phase_transition: ArrowUpRight,
  red_team_fires: ShieldAlert,
  energy_spike: Zap,
  energy_critical: MessageSquareWarning,
  bridge_connection: GitBranch,
  novelty_breakthrough: Sparkles,
  human_intervention: User,
};

const AHA_COLORS: Record<AhaType, string> = {
  phase_transition: '#3B82F6',
  red_team_fires: '#F87171',
  energy_spike: '#22C55E',
  energy_critical: '#EF4444',
  bridge_connection: '#A855F7',
  novelty_breakthrough: '#FBBF24',
  human_intervention: '#818CF8',
};

function resolveAgentName(agentId: string, members?: AgentMember[]): string {
  const m = members?.find((m) => m.agent_id === agentId);
  return m?.display_name ?? agentId;
}

/**
 * Detect "aha" moments from the deliberation event stream.
 *
 * We scan posts, energy updates, and phase signals for significant events
 * that would be worth highlighting during a demo.
 */
export function detectAhaMoments(
  posts: Post[],
  energyHistory: EnergyUpdate[],
  phaseHistory: PhaseSignal[],
  members?: AgentMember[],
): AhaMoment[] {
  const moments: AhaMoment[] = [];

  // Track phase transitions
  let prevPhase: Phase | null = null;
  for (const signal of phaseHistory) {
    if (prevPhase !== null && signal.current_phase !== prevPhase) {
      const phaseColor = PHASE_COLORS[signal.current_phase] ?? '#6B7280';
      const fromLabel = PHASE_LABELS[prevPhase] ?? prevPhase;
      const toLabel = PHASE_LABELS[signal.current_phase] ?? signal.current_phase;
      moments.push({
        id: `phase-${prevPhase}-${signal.current_phase}`,
        type: 'phase_transition',
        title: `Phase: ${fromLabel} \u2192 ${toLabel}`,
        description: signal.observation
          ?? `Observer detected shift to ${toLabel} from conversation metrics`,
        color: phaseColor,
        timestamp: new Date().toISOString(),
      });
    }
    prevPhase = signal.current_phase;
  }

  // Track red team firing (non-seed posts with red team triggers)
  const RED_TEAM_TRIGGERS = ['consensus_forming', 'criticism_gap', 'premature_convergence'];
  for (const post of posts) {
    const redTeamRules = post.triggered_by.filter((r) => RED_TEAM_TRIGGERS.includes(r));
    if (redTeamRules.length > 0) {
      const name = resolveAgentName(post.agent_id, members);
      const trigger = redTeamRules[0];
      moments.push({
        id: `redteam-${post.id}`,
        type: 'red_team_fires',
        title: `Red Team: ${name}`,
        description: `Activated by ${trigger.replace(/_/g, ' ')} \u2014 challenging assumptions`,
        color: AHA_COLORS.red_team_fires,
        timestamp: post.created_at,
      });
    }
  }

  // Track bridge opportunities
  for (const post of posts) {
    if (post.triggered_by.includes('bridge_opportunity')) {
      const name = resolveAgentName(post.agent_id, members);
      moments.push({
        id: `bridge-${post.id}`,
        type: 'bridge_connection',
        title: `Bridge: ${name}`,
        description: 'Connected insights across different agents\u2019 domains',
        color: AHA_COLORS.bridge_connection,
        timestamp: post.created_at,
      });
    }
  }

  // Track novelty breakthroughs (novelty_score > 0.7)
  for (const post of posts) {
    if (post.novelty_score > 0.7 && !post.triggered_by.includes('seed_phase')) {
      const name = resolveAgentName(post.agent_id, members);
      moments.push({
        id: `novelty-${post.id}`,
        type: 'novelty_breakthrough',
        title: `High Novelty: ${name}`,
        description: `Novelty score ${Math.round(post.novelty_score * 100)}% \u2014 new ground being broken`,
        color: AHA_COLORS.novelty_breakthrough,
        timestamp: post.created_at,
      });
    }
  }

  // Track energy spikes (energy jumps up by > 0.15 between consecutive turns)
  for (let i = 1; i < energyHistory.length; i++) {
    const prev = energyHistory[i - 1];
    const curr = energyHistory[i];
    const delta = curr.energy - prev.energy;
    if (delta > 0.15) {
      moments.push({
        id: `energy-spike-${curr.turn}`,
        type: 'energy_spike',
        title: `Energy Spike: +${Math.round(delta * 100)}%`,
        description: `Energy surged from ${prev.energy.toFixed(2)} to ${curr.energy.toFixed(2)} \u2014 new ideas injected`,
        color: AHA_COLORS.energy_spike,
        timestamp: new Date().toISOString(),
        turn: curr.turn,
      });
    }
  }

  // Track energy approaching termination
  const lastThree = energyHistory.slice(-3);
  if (lastThree.length === 3 && lastThree.every((e) => e.energy < 0.2)) {
    moments.push({
      id: `energy-critical-${lastThree[2].turn}`,
      type: 'energy_critical',
      title: 'Termination Approaching',
      description: `Energy below 0.2 for 3 turns \u2014 deliberation winding down`,
      color: AHA_COLORS.energy_critical,
      timestamp: new Date().toISOString(),
      turn: lastThree[2].turn,
    });
  }

  // Track human interventions
  for (const post of posts) {
    if (post.triggered_by.includes('human_intervention')) {
      const name = resolveAgentName(post.agent_id, members);
      moments.push({
        id: `human-${post.id}`,
        type: 'human_intervention',
        title: `Human \u2192 ${name}`,
        description: 'Agent responding to human intervention',
        color: AHA_COLORS.human_intervention,
        timestamp: post.created_at,
      });
    }
  }

  // Deduplicate by id (can get dupes from re-renders)
  const seen = new Set<string>();
  return moments.filter((m) => {
    if (seen.has(m.id)) return false;
    seen.add(m.id);
    return true;
  });
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

interface AhaMomentFeedProps {
  posts: Post[];
  energyHistory: EnergyUpdate[];
  phaseHistory: PhaseSignal[];
  members?: AgentMember[];
}

export function AhaMomentFeed({ posts, energyHistory, phaseHistory, members }: AhaMomentFeedProps) {
  const containerRef = useRef<HTMLDivElement>(null);

  const moments = useMemo(
    () => detectAhaMoments(posts, energyHistory, phaseHistory, members),
    [posts, energyHistory, phaseHistory, members],
  );

  // Auto-scroll to latest moment
  useEffect(() => {
    if (containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [moments.length]);

  if (moments.length === 0) return null;

  return (
    <div>
      <h4 className="text-xs font-medium text-text-muted uppercase tracking-wider mb-3 flex items-center gap-1.5">
        <Zap className="h-3 w-3 text-warning" />
        Key Moments
      </h4>
      <div
        ref={containerRef}
        className="space-y-2 max-h-[280px] overflow-y-auto pr-1"
      >
        <AnimatePresence mode="popLayout">
          {moments.map((moment) => {
            const Icon = AHA_ICONS[moment.type];
            return (
              <motion.div
                key={moment.id}
                initial={{ opacity: 0, x: 20, scale: 0.95 }}
                animate={{ opacity: 1, x: 0, scale: 1 }}
                exit={{ opacity: 0, scale: 0.95 }}
                transition={{ duration: 0.3, ease: 'easeOut' }}
                className="relative rounded-md border px-3 py-2.5"
                style={{
                  borderColor: `${moment.color}33`,
                  backgroundColor: `${moment.color}0A`,
                }}
              >
                {/* Accent stripe */}
                <div
                  className="absolute left-0 top-0 bottom-0 w-0.5 rounded-l-md"
                  style={{ backgroundColor: moment.color }}
                />

                <div className="flex items-start gap-2 ml-1">
                  <div
                    className="shrink-0 mt-0.5 rounded-full p-1"
                    style={{ backgroundColor: `${moment.color}20` }}
                  >
                    <Icon className="h-3 w-3" style={{ color: moment.color }} />
                  </div>
                  <div className="min-w-0">
                    <p
                      className="text-xs font-semibold leading-tight"
                      style={{ color: moment.color }}
                    >
                      {moment.title}
                    </p>
                    <p className="text-xs text-text-secondary mt-0.5 leading-snug">
                      {moment.description}
                    </p>
                  </div>
                </div>
              </motion.div>
            );
          })}
        </AnimatePresence>
      </div>
    </div>
  );
}
