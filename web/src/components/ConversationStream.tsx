import { useEffect, useRef } from 'react';
import type { Post } from '../types/deliberation';
import { AGENT_META, PHASE_LABELS, STANCE_COLORS, TRIGGER_COLORS } from './agentMeta';

interface ConversationStreamProps {
  posts: Post[];
}

export function ConversationStream({ posts }: ConversationStreamProps) {
  const bottomRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const userScrolled = useRef(false);

  useEffect(() => {
    if (!userScrolled.current) {
      bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [posts.length]);

  const handleScroll = () => {
    const el = containerRef.current;
    if (!el) return;
    const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 60;
    userScrolled.current = !atBottom;
  };

  if (posts.length === 0) {
    return (
      <div className="conversation-stream empty">
        <div className="empty-state">
          <p>Enter a hypothesis and click Start to begin deliberation.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="conversation-stream" ref={containerRef} onScroll={handleScroll}>
      <h2 className="panel-title">Conversation</h2>
      {posts.map((post, i) => {
        const meta = AGENT_META[post.agent_id] || {
          name: post.agent_id,
          color: '#94a3b8',
          bgColor: '#94a3b818',
          icon: '?',
        };

        return (
          <div
            key={post.id || i}
            className="post-card"
            style={{ borderLeftColor: meta.color, backgroundColor: meta.bgColor }}
          >
            <div className="post-header">
              <span className="post-agent" style={{ color: meta.color }}>
                {meta.icon} {meta.name}
              </span>
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
          </div>
        );
      })}
      <div ref={bottomRef} />
    </div>
  );
}
