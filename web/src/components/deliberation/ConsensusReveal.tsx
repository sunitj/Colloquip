import { motion } from 'motion/react';
import { AgentAvatar } from '@/components/shared/AgentAvatar';
import { MarkdownContent } from '@/components/shared/MarkdownContent';
import { StanceBadge } from '@/components/shared/StanceBadge';
import type { ConsensusMap, AgentStance } from '@/types/deliberation';
import type { AgentMember } from '@/types/platform';

interface ConsensusRevealProps {
  consensus: ConsensusMap;
  members?: AgentMember[];
}

function resolveMember(agentId: string, members?: AgentMember[]) {
  const member = members?.find((m) => m.agent_id === agentId);
  return {
    displayName: member?.display_name ?? agentId,
    agentType: member?.agent_type ?? agentId,
    isRedTeam: member?.is_red_team ?? false,
  };
}

export function ConsensusReveal({ consensus, members }: ConsensusRevealProps) {
  return (
    <div className="space-y-6">
      {/* Summary hero card */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="bg-bg-surface p-6 rounded-xl border border-border-default"
      >
        <h3 className="text-sm font-medium text-text-muted mb-2">Consensus Summary</h3>
        <MarkdownContent content={consensus.summary} className="text-text-primary leading-relaxed" />
      </motion.div>

      {/* Agreements */}
      {consensus.agreements.length > 0 && (
        <div className="space-y-3">
          <h4 className="text-sm font-medium text-text-muted">Agreements</h4>
          {consensus.agreements.map((agreement, i) => (
            <motion.div
              key={`agree-${i}`}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.4, delay: 0.15 * i + 0.3 }}
              className="bg-bg-surface p-4 rounded-lg"
              style={{ borderLeft: '3px solid #22C55E' }}
            >
              <MarkdownContent content={agreement} className="text-sm text-text-primary" />
            </motion.div>
          ))}
        </div>
      )}

      {/* Disagreements */}
      {consensus.disagreements.length > 0 && (
        <div className="space-y-3">
          <h4 className="text-sm font-medium text-text-muted">Disagreements</h4>
          {consensus.disagreements.map((disagreement, i) => (
            <motion.div
              key={`disagree-${i}`}
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.4, delay: 0.15 * i + 0.5 }}
              className="bg-bg-surface p-4 rounded-lg"
              style={{ borderLeft: '3px solid #EF4444' }}
            >
              <MarkdownContent content={disagreement} className="text-sm text-text-primary" />
            </motion.div>
          ))}
        </div>
      )}

      {/* Minority Positions */}
      {consensus.minority_positions.length > 0 && (
        <div className="space-y-3">
          <h4 className="text-sm font-medium text-text-muted">Minority Positions</h4>
          {consensus.minority_positions.map((position, i) => (
            <motion.div
              key={`minority-${i}`}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.4, delay: 0.15 * i + 0.8 }}
              className="bg-bg-surface p-4 rounded-lg"
              style={{ borderLeft: '3px solid #F59E0B' }}
            >
              <MarkdownContent content={position} className="text-sm text-text-primary" />
            </motion.div>
          ))}
        </div>
      )}

      {/* Serendipity Connections */}
      {consensus.serendipity_connections.length > 0 && (
        <div className="space-y-3">
          <h4 className="text-sm font-medium text-text-muted">Serendipity Connections</h4>
          {consensus.serendipity_connections.map((conn, i) => (
            <motion.div
              key={`serendipity-${i}`}
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.4, delay: 0.15 * i + 1.0 }}
              className="bg-bg-surface p-4 rounded-lg"
              style={{ borderLeft: '3px solid #A855F7' }}
            >
              <p className="text-xs font-medium mb-1" style={{ color: '#A855F7' }}>
                {conn.agent}
              </p>
              <MarkdownContent content={conn.connection} className="text-sm text-text-primary" />
            </motion.div>
          ))}
        </div>
      )}

      {/* Final Stances */}
      {Object.keys(consensus.final_stances).length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 1.2 }}
          className="space-y-3"
        >
          <h4 className="text-sm font-medium text-text-muted">Final Stances</h4>
          <div className="flex flex-wrap gap-4">
            {Object.entries(consensus.final_stances).map(([agentId, stance]) => {
              const agent = resolveMember(agentId, members);
              return (
                <div key={agentId} className="flex flex-col items-center gap-1.5">
                  <AgentAvatar
                    displayName={agent.displayName}
                    agentType={agent.agentType}
                    isRedTeam={agent.isRedTeam}
                    size="md"
                  />
                  <span className="text-xs text-text-muted">{agent.displayName}</span>
                  <StanceBadge stance={stance as AgentStance} />
                </div>
              );
            })}
          </div>
        </motion.div>
      )}
    </div>
  );
}
