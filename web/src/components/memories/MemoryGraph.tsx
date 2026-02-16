import { useMemo, useState, useCallback } from 'react';
import { GraphCanvas, darkTheme, type GraphNode, type GraphEdge, type InternalGraphNode } from 'reagraph';
import { X } from 'lucide-react';
import { cn, timeAgo } from '@/lib/utils';
import type { Memory, CrossReference } from '@/types/platform';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';

interface MemoryGraphProps {
  memories: Memory[];
  crossReferences: CrossReference[];
}

// Community → color mapping (matches app.css agent/phase palette)
const COMMUNITY_COLORS: Record<string, string> = {
  neuropharmacology: '#60A5FA',     // blue
  enzyme_engineering: '#FBBF24',    // amber
  immuno_oncology: '#F472B6',       // pink
  synbio_manufacturing: '#2DD4BF',  // teal
  microbiome_therapeutics: '#34D399', // emerald
};

const DEFAULT_COMMUNITY_COLOR = '#A78BFA'; // purple fallback

function getCommunityColor(subredditName: string): string {
  return COMMUNITY_COLORS[subredditName] ?? DEFAULT_COMMUNITY_COLOR;
}

function confidenceColor(value: number): string {
  if (value > 0.7) return '#22C55E';
  if (value > 0.4) return '#F59E0B';
  return '#EF4444';
}

function truncate(text: string, max: number): string {
  if (text.length <= max) return text;
  return text.slice(0, max - 1) + '\u2026';
}

export function MemoryGraph({ memories, crossReferences }: MemoryGraphProps) {
  const [selectedMemory, setSelectedMemory] = useState<Memory | null>(null);

  const nodes: GraphNode[] = useMemo(
    () =>
      memories.map((m) => ({
        id: m.id,
        label: truncate(m.topic, 40),
        fill: getCommunityColor(m.subreddit_name),
        size: Math.max(3, m.confidence * 8),
        data: { ref: m },
      })),
    [memories],
  );

  const edges: GraphEdge[] = useMemo(() => {
    const memoryIds = new Set(memories.map((m) => m.id));
    return crossReferences
      .filter(
        (cr) => memoryIds.has(cr.source_memory_id) && memoryIds.has(cr.target_memory_id),
      )
      .map((cr) => ({
        id: cr.id,
        source: cr.source_memory_id,
        target: cr.target_memory_id,
        label: `${Math.round(cr.similarity * 100)}%`,
        size: cr.similarity * 3,
      }));
  }, [memories, crossReferences]);

  const handleNodeClick = useCallback(
    (node: InternalGraphNode) => {
      const mem = memories.find((m) => m.id === node.id);
      if (mem) setSelectedMemory(mem);
    },
    [memories],
  );

  // Collect unique communities for the legend
  const communities = useMemo(() => {
    const seen = new Map<string, string>();
    for (const m of memories) {
      if (!seen.has(m.subreddit_name)) {
        seen.set(m.subreddit_name, getCommunityColor(m.subreddit_name));
      }
    }
    return Array.from(seen.entries());
  }, [memories]);

  if (memories.length === 0) {
    return (
      <div className="flex h-96 items-center justify-center text-text-muted">
        No memories to visualize
      </div>
    );
  }

  return (
    <div className="relative h-[600px] w-full rounded-lg border border-border-default bg-bg-surface overflow-hidden">
      {/* Graph canvas */}
      <GraphCanvas
        nodes={nodes}
        edges={edges}
        layoutType="forceDirected2d"
        draggable
        onNodeClick={handleNodeClick}
        labelType="auto"
        theme={darkTheme}
        edgeArrowPosition="none"
        cameraMode="rotate"
      />

      {/* Community legend */}
      <div className="absolute left-3 top-3 flex flex-col gap-1.5 rounded-md border border-border-default bg-bg-overlay/90 px-3 py-2 backdrop-blur-sm">
        <span className="text-[10px] font-semibold uppercase tracking-wider text-text-muted">
          Communities
        </span>
        {communities.map(([name, color]) => (
          <div key={name} className="flex items-center gap-2">
            <div
              className="h-2.5 w-2.5 rounded-full"
              style={{ backgroundColor: color }}
            />
            <span className="text-xs text-text-secondary">{name}</span>
          </div>
        ))}
        {edges.length > 0 && (
          <>
            <div className="my-1 h-px bg-border-default" />
            <span className="text-[10px] text-text-muted">
              {edges.length} cross-reference{edges.length !== 1 ? 's' : ''}
            </span>
          </>
        )}
      </div>

      {/* Node detail panel */}
      {selectedMemory && (
        <MemoryDetailPanel
          memory={selectedMemory}
          onClose={() => setSelectedMemory(null)}
        />
      )}
    </div>
  );
}

/** Detail panel shown when a memory node is clicked */
function MemoryDetailPanel({
  memory,
  onClose,
}: {
  memory: Memory;
  onClose: () => void;
}) {
  const confidencePct = Math.round(memory.confidence * 100);

  return (
    <div
      className={cn(
        'absolute right-3 top-3 w-80 max-h-[560px] overflow-y-auto',
        'rounded-lg border border-border-accent bg-bg-overlay/95 backdrop-blur-sm',
        'p-4 shadow-lg',
      )}
    >
      <div className="flex items-start justify-between gap-2">
        <h4 className="text-sm font-semibold text-text-primary line-clamp-2">
          {memory.topic}
        </h4>
        <button
          onClick={onClose}
          className="shrink-0 rounded p-0.5 text-text-muted hover:bg-bg-elevated hover:text-text-primary"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      <div className="mt-2 flex items-center gap-1.5">
        <Badge
          variant="secondary"
          className="text-[10px]"
          style={{
            borderColor: getCommunityColor(memory.subreddit_name),
            color: getCommunityColor(memory.subreddit_name),
          }}
        >
          c/{memory.subreddit_name}
        </Badge>
        <span className="text-[10px] text-text-muted">{timeAgo(memory.created_at)}</span>
      </div>

      {/* Confidence */}
      <div className="mt-3 flex items-center gap-2">
        <Progress
          value={confidencePct}
          color={confidenceColor(memory.confidence)}
          className="flex-1"
        />
        <span
          className="text-xs font-medium"
          style={{ color: confidenceColor(memory.confidence) }}
        >
          {confidencePct}%
        </span>
      </div>

      {/* Key conclusions */}
      {memory.key_conclusions.length > 0 && (
        <ul className="mt-3 space-y-1">
          {memory.key_conclusions.slice(0, 4).map((c, i) => (
            <li
              key={i}
              className="flex items-start gap-1.5 text-xs text-text-secondary"
            >
              <span className="mt-1.5 inline-block h-1 w-1 shrink-0 rounded-full bg-text-muted" />
              <span className="line-clamp-2">{c}</span>
            </li>
          ))}
        </ul>
      )}

      {/* Meta */}
      <div className="mt-3 flex flex-wrap gap-1.5">
        <Badge variant="secondary" className="text-[10px]">
          {memory.evidence_quality}
        </Badge>
        <Badge variant="secondary" className="text-[10px]">
          {memory.confidence_level}
        </Badge>
      </div>

      {/* Agents */}
      {memory.agents_involved.length > 0 && (
        <p className="mt-2 text-[10px] text-text-muted">
          Agents: {memory.agents_involved.join(', ')}
        </p>
      )}

      {/* Annotations count */}
      {memory.annotations.length > 0 && (
        <p className="mt-1 text-[10px] text-text-muted">
          {memory.annotations.length} annotation{memory.annotations.length !== 1 ? 's' : ''}
        </p>
      )}
    </div>
  );
}
