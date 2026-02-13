import React, { useEffect, useRef } from 'react';
import { cn } from '@/lib/utils';
import { getAgentColor, getAgentBgColor, getAgentInitials, STANCE_COLORS, PHASE_COLORS, PHASE_LABELS, TRIGGER_COLORS } from '@/lib/agentColors';
import { ThinkingIndicator } from './ThinkingIndicator';
import type { Phase, Post, SessionStatus } from '@/types/deliberation';

interface ConversationStreamProps {
  posts: Post[];
  status: SessionStatus;
  thinking: boolean;
}

export function ConversationStream({ posts, status, thinking }: ConversationStreamProps) {
  const bottomRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const userScrolled = useRef(false);
  const prevCountRef = useRef(0);

  useEffect(() => {
    if (!userScrolled.current) {
      bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [posts.length, thinking]);

  useEffect(() => {
    prevCountRef.current = posts.length;
  });

  const handleScroll = () => {
    const el = containerRef.current;
    if (!el) return;
    const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 60;
    userScrolled.current = !atBottom;
  };

  const isRunning = status === 'running';

  if (posts.length === 0 && !isRunning) {
    return (
      <div className="flex items-center justify-center h-64 text-text-muted text-sm">
        No posts yet. Start a deliberation to begin.
      </div>
    );
  }

  const items: React.JSX.Element[] = [];
  let lastPhase: Phase | null = null;
  const batchStart = prevCountRef.current;

  for (let i = 0; i < posts.length; i++) {
    const post = posts[i];
    const agentColor = getAgentColor(post.agent_id, post.agent_id === 'redteam' || post.agent_id.includes('red_team'));
    const agentBg = getAgentBgColor(agentColor);
    const initials = getAgentInitials(post.agent_id);
    const isSeed = post.triggered_by.includes('seed_phase');

    // Phase separator
    if (lastPhase !== null && post.phase !== lastPhase) {
      const phaseColor = PHASE_COLORS[post.phase] || '#6B7280';
      items.push(
        <div key={`phase-sep-${i}`} className="flex items-center gap-3 py-3">
          <div className="flex-1 h-px" style={{ background: `linear-gradient(to right, transparent, ${phaseColor}40, transparent)` }} />
          <span
            className="text-xs font-bold tracking-widest uppercase px-2"
            style={{ color: phaseColor }}
          >
            {PHASE_LABELS[post.phase] || post.phase}
          </span>
          <div className="flex-1 h-px" style={{ background: `linear-gradient(to right, transparent, ${phaseColor}40, transparent)` }} />
        </div>,
      );
    }
    lastPhase = post.phase;

    const isNew = i >= batchStart;
    const staggerDelay = isNew ? (i - batchStart) * 0.12 : 0;
    const animClass = isNew ? 'animate-[slideUp_0.3s_ease-out_backwards]' : '';

    items.push(
      <div
        key={post.id || i}
        className={cn(
          'rounded-xl border-l-2 p-5 mb-2 transition-colors',
          isSeed && 'opacity-70',
          animClass,
        )}
        style={{
          borderLeftColor: agentColor,
          backgroundColor: agentBg,
          animationDelay: isNew ? `${staggerDelay}s` : undefined,
        }}
      >
        {/* Header */}
        <div className="flex items-center gap-3 mb-2 flex-wrap">
          <div
            className="w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold text-white shrink-0"
            style={{ backgroundColor: agentColor }}
          >
            {initials}
          </div>
          <span className="text-sm font-medium" style={{ color: agentColor }}>
            {post.agent_id}
          </span>
          {isSeed && (
            <span className="text-xs font-bold tracking-wider uppercase px-1.5 py-0.5 rounded-full bg-bg-tertiary text-text-muted">
              SEED
            </span>
          )}
          <span className="text-xs text-text-muted uppercase tracking-wider">
            {PHASE_LABELS[post.phase] || post.phase}
          </span>
          <span
            className="text-xs font-semibold uppercase tracking-wider"
            style={{ color: STANCE_COLORS[post.stance] || '#6B7280' }}
          >
            {post.stance.replace(/_/g, ' ')}
          </span>
          <span className="text-xs text-text-muted ml-auto">#{i + 1}</span>
        </div>

        {/* Content */}
        <div className="text-base text-text-secondary leading-relaxed mb-3">
          {post.content.length > 300 ? post.content.slice(0, 300) + '...' : post.content}
        </div>

        {/* Claims & Questions */}
        {(post.key_claims.length > 0 || post.questions_raised.length > 0) && (
          <div className="space-y-2 mb-3">
            {post.key_claims.length > 0 && (
              <div className="flex flex-wrap gap-1.5 items-center">
                <span className="text-xs font-semibold text-text-muted uppercase tracking-wider">Claims:</span>
                {post.key_claims.map((c, j) => (
                  <span key={j} className="text-xs px-2 py-0.5 rounded-full bg-pastel-mint-bg text-[#3D9B6E]">
                    {c}
                  </span>
                ))}
              </div>
            )}
            {post.questions_raised.length > 0 && (
              <div className="flex flex-wrap gap-1.5 items-center">
                <span className="text-xs font-semibold text-text-muted uppercase tracking-wider">Questions:</span>
                {post.questions_raised.map((q, j) => (
                  <span key={j} className="text-xs px-2 py-0.5 rounded-full bg-pastel-sky-bg text-[#3B7AB5]">
                    {q}
                  </span>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Triggers */}
        <div className="flex flex-wrap gap-2 items-center">
          {post.triggered_by.map((rule) => (
            <span
              key={rule}
              className="text-xs px-1.5 py-0.5 rounded-full border text-text-muted"
              style={{ borderColor: TRIGGER_COLORS[rule] || '#6b7280' }}
            >
              {rule.replace(/_/g, ' ')}
            </span>
          ))}
          <span className="text-xs px-1.5 py-0.5 rounded-full bg-bg-tertiary/50 text-text-muted ml-auto">
            novelty: {(post.novelty_score * 100).toFixed(0)}%
          </span>
        </div>
      </div>,
    );
  }

  return (
    <div
      className="flex-1 overflow-y-auto space-y-2 pr-2 scrollbar-thin"
      ref={containerRef}
      onScroll={handleScroll}
    >
      {isRunning && posts.length === 0 && (
        <ThinkingIndicator message="Initializing deliberation..." />
      )}

      {items}

      {thinking && posts.length > 0 && (
        <ThinkingIndicator />
      )}

      <div ref={bottomRef} />
    </div>
  );
}
