import { getAgentColor, getAgentInitials, STANCE_COLORS } from '@/lib/agentColors';
import type { ConsensusMap } from '@/types/deliberation';

interface ConsensusViewProps {
  consensus: ConsensusMap;
}

export function ConsensusView({ consensus }: ConsensusViewProps) {
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="text-center py-4 border-b border-border-subtle">
        <h2 className="text-lg font-bold text-text-primary font-[family-name:var(--font-heading)]">Deliberation Complete</h2>
      </div>

      {/* Summary */}
      <div className="bg-bg-tertiary/50 rounded-xl p-4">
        <h3 className="text-sm font-semibold text-text-primary mb-2">Summary</h3>
        <p className="text-sm text-text-secondary leading-relaxed">{consensus.summary}</p>
      </div>

      {/* Agreements */}
      {consensus.agreements.length > 0 && (
        <div className="rounded-xl bg-pastel-mint-bg p-4">
          <h3 className="text-sm font-semibold text-[#3D9B6E] mb-2">
            Areas of Agreement
          </h3>
          <ul className="space-y-1.5">
            {consensus.agreements.map((a, i) => (
              <li key={i} className="text-sm text-text-secondary flex gap-2">
                <span className="text-[#3D9B6E] shrink-0">+</span>
                <span>{a}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Disagreements */}
      {consensus.disagreements.length > 0 && (
        <div className="rounded-xl bg-pastel-rose-bg p-4">
          <h3 className="text-sm font-semibold text-[#C95A6B] mb-2">
            Areas of Disagreement
          </h3>
          <ul className="space-y-1.5">
            {consensus.disagreements.map((d, i) => (
              <li key={i} className="text-sm text-text-secondary flex gap-2">
                <span className="text-[#C95A6B] shrink-0">-</span>
                <span>{d}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Minority Positions */}
      {consensus.minority_positions.length > 0 && (
        <div className="rounded-xl bg-pastel-lavender-bg p-4">
          <h3 className="text-sm font-semibold text-[#8B6DBF] mb-2">
            Minority Positions
          </h3>
          <ul className="space-y-1.5">
            {consensus.minority_positions.map((m, i) => (
              <li key={i} className="text-sm text-text-secondary flex gap-2">
                <span className="text-[#8B6DBF] shrink-0">*</span>
                <span>{m}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Final Stances */}
      {Object.keys(consensus.final_stances).length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-text-primary mb-3">
            Final Stances
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {Object.entries(consensus.final_stances).map(([agentId, stance]) => {
              const color = getAgentColor(agentId);
              const initials = getAgentInitials(agentId);
              return (
                <div key={agentId} className="flex items-center gap-2 rounded-xl bg-bg-tertiary/50 p-2">
                  <div
                    className="w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold text-white shrink-0"
                    style={{ backgroundColor: color }}
                  >
                    {initials}
                  </div>
                  <div className="flex flex-col min-w-0">
                    <span className="text-xs text-text-secondary truncate">{agentId}</span>
                    <span
                      className="text-xs font-semibold uppercase"
                      style={{ color: STANCE_COLORS[stance] || '#6B7280' }}
                    >
                      {stance.replace(/_/g, ' ')}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
