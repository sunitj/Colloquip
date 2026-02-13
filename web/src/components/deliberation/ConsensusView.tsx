import { getAgentColor, getAgentInitials, STANCE_COLORS } from '@/lib/agentColors';
import type { ConsensusMap } from '@/types/deliberation';

interface ConsensusViewProps {
  consensus: ConsensusMap;
}

export function ConsensusView({ consensus }: ConsensusViewProps) {
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="text-center py-4 border-b border-border-default">
        <h2 className="text-lg font-bold text-text-primary">Deliberation Complete</h2>
      </div>

      {/* Summary */}
      <div className="bg-bg-tertiary/50 rounded-lg p-4">
        <h3 className="text-xs font-bold uppercase tracking-widest text-text-muted mb-2">Summary</h3>
        <p className="text-sm text-text-secondary leading-relaxed">{consensus.summary}</p>
      </div>

      {/* Agreements */}
      {consensus.agreements.length > 0 && (
        <div>
          <h3 className="text-xs font-bold uppercase tracking-widest text-stance-supportive mb-2">
            Areas of Agreement
          </h3>
          <ul className="space-y-1.5">
            {consensus.agreements.map((a, i) => (
              <li key={i} className="text-sm text-text-secondary flex gap-2">
                <span className="text-stance-supportive shrink-0">+</span>
                <span>{a}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Disagreements */}
      {consensus.disagreements.length > 0 && (
        <div>
          <h3 className="text-xs font-bold uppercase tracking-widest text-stance-critical mb-2">
            Areas of Disagreement
          </h3>
          <ul className="space-y-1.5">
            {consensus.disagreements.map((d, i) => (
              <li key={i} className="text-sm text-text-secondary flex gap-2">
                <span className="text-stance-critical shrink-0">-</span>
                <span>{d}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Minority Positions */}
      {consensus.minority_positions.length > 0 && (
        <div>
          <h3 className="text-xs font-bold uppercase tracking-widest text-stance-novel mb-2">
            Minority Positions
          </h3>
          <ul className="space-y-1.5">
            {consensus.minority_positions.map((m, i) => (
              <li key={i} className="text-sm text-text-secondary flex gap-2">
                <span className="text-stance-novel shrink-0">*</span>
                <span>{m}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Final Stances */}
      {Object.keys(consensus.final_stances).length > 0 && (
        <div>
          <h3 className="text-xs font-bold uppercase tracking-widest text-text-muted mb-3">
            Final Stances
          </h3>
          <div className="grid grid-cols-2 gap-2">
            {Object.entries(consensus.final_stances).map(([agentId, stance]) => {
              const color = getAgentColor(agentId);
              const initials = getAgentInitials(agentId);
              return (
                <div key={agentId} className="flex items-center gap-2 rounded-lg bg-bg-tertiary/50 p-2">
                  <div
                    className="w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-bold text-white shrink-0"
                    style={{ backgroundColor: color }}
                  >
                    {initials}
                  </div>
                  <div className="flex flex-col min-w-0">
                    <span className="text-xs text-text-secondary truncate">{agentId}</span>
                    <span
                      className="text-[10px] font-semibold uppercase"
                      style={{ color: STANCE_COLORS[stance] || '#94A3B8' }}
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
