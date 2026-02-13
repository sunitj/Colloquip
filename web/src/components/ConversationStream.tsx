import React, { useEffect, useRef } from 'react';
import type { Phase, Post, SessionStatus } from '../types/deliberation';
import { AGENT_META, PHASE_LABELS, STANCE_COLORS, TRIGGER_COLORS } from './agentMeta';

interface ConversationStreamProps {
  posts: Post[];
  status: SessionStatus;
  thinking: boolean;
}

export function ConversationStream({ posts, status, thinking }: ConversationStreamProps) {
  const bottomRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const userScrolled = useRef(false);
  /** Track the post count from the previous render so we can stagger new arrivals. */
  const prevCountRef = useRef(0);

  useEffect(() => {
    if (!userScrolled.current) {
      bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [posts.length, thinking]);

  // Snapshot previous post count after each render.
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
      <div className="conversation-stream empty">
        <div className="empty-state">
          <p>Enter a hypothesis and click Start to begin deliberation.</p>
        </div>
      </div>
    );
  }

  // Build the list with phase-separator elements injected between phase transitions.
  const items: React.JSX.Element[] = [];
  let lastPhase: Phase | null = null;
  const batchStart = prevCountRef.current;

  for (let i = 0; i < posts.length; i++) {
    const post = posts[i];
    const meta = AGENT_META[post.agent_id] || {
      name: post.agent_id,
      color: '#94a3b8',
      bgColor: '#94a3b818',
      icon: '?',
    };
    const isSeed = post.triggered_by.includes('seed_phase');

    // Phase separator when the phase changes (skip before first post).
    if (lastPhase !== null && post.phase !== lastPhase) {
      items.push(
        <div key={`phase-sep-${i}`} className="phase-separator">
          <span className="phase-separator-line" />
          <span className="phase-separator-label">
            {PHASE_LABELS[post.phase] || post.phase}
          </span>
          <span className="phase-separator-line" />
        </div>,
      );
    }
    lastPhase = post.phase;

    // Stagger animation delay for posts that arrived in this render batch.
    const isNew = i >= batchStart;
    const staggerDelay = isNew ? (i - batchStart) * 0.12 : 0;
    const animStyle = isNew
      ? { animationDelay: `${staggerDelay}s`, animationFillMode: 'backwards' as const }
      : undefined;

    items.push(
      <div
        key={post.id || i}
        className={`post-card ${isSeed ? 'seed' : ''}`}
        style={{
          borderLeftColor: meta.color,
          backgroundColor: meta.bgColor,
          ...animStyle,
        }}
      >
        <div className="post-header">
          <span className="post-agent" style={{ color: meta.color }}>
            {meta.icon} {meta.name}
          </span>
          {isSeed && <span className="seed-badge">SEED</span>}
          <span className="post-phase">{PHASE_LABELS[post.phase] || post.phase}</span>
          <span
            className="post-stance"
            style={{ color: STANCE_COLORS[post.stance] }}
          >
            {post.stance.replace(/_/g, ' ').toUpperCase()}
          </span>
          <span className="post-number">#{i + 1}</span>
        </div>

        <div className="post-content">
          {post.content.length > 300 ? post.content.slice(0, 300) + '...' : post.content}
        </div>

        {(post.key_claims.length > 0 || post.questions_raised.length > 0) && (
          <div className="post-details">
            {post.key_claims.length > 0 && (
              <div className="post-claims">
                <strong>Claims:</strong>
                {post.key_claims.map((c, j) => (
                  <span key={j} className="claim-tag">{c}</span>
                ))}
              </div>
            )}
            {post.questions_raised.length > 0 && (
              <div className="post-questions">
                <strong>Questions:</strong>
                {post.questions_raised.map((q, j) => (
                  <span key={j} className="question-tag">{q}</span>
                ))}
              </div>
            )}
          </div>
        )}

        <div className="post-triggers">
          {post.triggered_by.map(rule => (
            <span
              key={rule}
              className="trigger-badge"
              style={{ borderColor: TRIGGER_COLORS[rule] || '#64748b' }}
            >
              {rule.replace(/_/g, ' ')}
            </span>
          ))}
          <span className="novelty-badge">
            novelty: {(post.novelty_score * 100).toFixed(0)}%
          </span>
        </div>
      </div>,
    );
  }

  return (
    <div className="conversation-stream" ref={containerRef} onScroll={handleScroll}>
      <h2 className="panel-title">Conversation</h2>

      {/* Initial loading state — after Start but before first post */}
      {isRunning && posts.length === 0 && (
        <div className="thinking-indicator">
          <span className="thinking-dots">
            <span /><span /><span />
          </span>
          <span className="thinking-text">Initializing deliberation...</span>
        </div>
      )}

      {items}

      {/* Between-round thinking indicator */}
      {thinking && posts.length > 0 && (
        <div className="thinking-indicator">
          <span className="thinking-dots">
            <span /><span /><span />
          </span>
          <span className="thinking-text">Agents deliberating...</span>
        </div>
      )}

      <div ref={bottomRef} />
    </div>
  );
}
