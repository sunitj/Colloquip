import { useEffect, useRef, useCallback } from 'react';
import { AnimatePresence, motion } from 'motion/react';
import { PostCard } from './PostCard';
import { PhaseTransition } from './PhaseTransition';
import { ThinkingIndicator } from '@/components/shared/ThinkingIndicator';
import type { Post, PhaseSignal, Phase } from '@/types/deliberation';
import type { AgentMember } from '@/types/platform';

interface ConversationFeedProps {
  posts: Post[];
  phaseHistory: PhaseSignal[];
  thinking: boolean;
  members?: AgentMember[];
}

type FeedItem =
  | { type: 'post'; post: Post; key: string }
  | { type: 'phase'; phase: Phase; signal: PhaseSignal | undefined; key: string };

function buildFeed(posts: Post[], phaseHistory: PhaseSignal[]): FeedItem[] {
  const items: FeedItem[] = [];
  let prevPhase: Phase | null = null;

  // Build a map of phase signals for lookup
  const phaseSignalMap = new Map<Phase, PhaseSignal>();
  for (const signal of phaseHistory) {
    phaseSignalMap.set(signal.current_phase, signal);
  }

  for (const post of posts) {
    if (post.phase !== prevPhase) {
      items.push({
        type: 'phase',
        phase: post.phase,
        signal: phaseSignalMap.get(post.phase),
        key: `phase-${post.phase}-${items.length}`,
      });
      prevPhase = post.phase;
    }
    items.push({
      type: 'post',
      post,
      key: `post-${post.id}`,
    });
  }

  return items;
}

export function ConversationFeed({ posts, phaseHistory, thinking, members }: ConversationFeedProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const shouldAutoScroll = useRef(true);
  const prevPostCount = useRef(posts.length);

  const handleScroll = useCallback(() => {
    const el = containerRef.current;
    if (!el) return;
    // Auto-scroll if user is within 100px of the bottom
    const distanceFromBottom = el.scrollHeight - el.scrollTop - el.clientHeight;
    shouldAutoScroll.current = distanceFromBottom < 100;
  }, []);

  useEffect(() => {
    if (posts.length > prevPostCount.current && shouldAutoScroll.current) {
      const el = containerRef.current;
      if (el) {
        requestAnimationFrame(() => {
          el.scrollTo({ top: el.scrollHeight, behavior: 'smooth' });
        });
      }
    }
    prevPostCount.current = posts.length;
  }, [posts.length]);

  const feedItems = buildFeed(posts, phaseHistory);

  return (
    <div
      ref={containerRef}
      onScroll={handleScroll}
      className="flex-1 overflow-y-auto space-y-4 pr-2"
    >
      <AnimatePresence mode="popLayout">
        {feedItems.map((item, index) => (
          <motion.div
            key={item.key}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{
              duration: 0.3,
              delay: Math.min(index * 0.08, 0.4),
              ease: 'easeOut',
            }}
          >
            {item.type === 'phase' ? (
              <PhaseTransition
                phase={item.phase}
                confidence={item.signal?.confidence}
                observation={item.signal?.observation}
              />
            ) : (
              <PostCard post={item.post} members={members} />
            )}
          </motion.div>
        ))}
      </AnimatePresence>

      {thinking && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.2 }}
        >
          <ThinkingIndicator />
        </motion.div>
      )}
    </div>
  );
}
