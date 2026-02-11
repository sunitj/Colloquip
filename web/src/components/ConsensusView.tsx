import type { ConsensusMap } from '../types/deliberation';
import { AGENT_META, STANCE_COLORS } from './agentMeta';

interface ConsensusViewProps {
  consensus: ConsensusMap;
}

export function ConsensusView({ consensus }: ConsensusViewProps) {
  return (
    <div className="consensus-view">
      <h2 className="consensus-title">Deliberation Complete</h2>

      <div className="consensus-summary">
        <h3>Summary</h3>
        <p>{consensus.summary}</p>
      </div>

      {consensus.agreements.length > 0 && (
        <div className="consensus-section agreements">
          <h3>Areas of Agreement</h3>
          <ul>
            {consensus.agreements.map((a, i) => (
              <li key={i}>{a}</li>
            ))}
          </ul>
        </div>
      )}

      {consensus.disagreements.length > 0 && (
        <div className="consensus-section disagreements">
          <h3>Areas of Disagreement</h3>
          <ul>
            {consensus.disagreements.map((d, i) => (
              <li key={i}>{d}</li>
            ))}
          </ul>
        </div>
      )}

      {consensus.minority_positions.length > 0 && (
        <div className="consensus-section minority">
          <h3>Minority Positions</h3>
          <ul>
            {consensus.minority_positions.map((m, i) => (
              <li key={i}>{m}</li>
            ))}
          </ul>
        </div>
      )}

      {Object.keys(consensus.final_stances).length > 0 && (
        <div className="consensus-section stances">
          <h3>Final Stances</h3>
          <div className="stance-grid">
            {Object.entries(consensus.final_stances).map(([agentId, stance]) => {
              const meta = AGENT_META[agentId];
              return (
                <div key={agentId} className="stance-card">
                  <span className="stance-agent" style={{ color: meta?.color }}>
                    {meta?.icon} {meta?.name || agentId}
                  </span>
                  <span
                    className="stance-value"
                    style={{ color: STANCE_COLORS[stance] }}
                  >
                    {stance.replace(/_/g, ' ').toUpperCase()}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
