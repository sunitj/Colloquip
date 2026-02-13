import { useState } from 'react';
import { createFileRoute } from '@tanstack/react-router';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getMemories, annotateMemory } from '@/lib/api';
import { queryKeys } from '@/lib/queryKeys';
import { PageHeader } from '@/components/layout/PageHeader';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { EmptyState } from '@/components/shared/EmptyState';
import { Skeleton } from '@/components/ui/Skeleton';
import { cn } from '@/lib/utils';
import { timeAgo } from '@/lib/utils';
import type { Memory, MemoryAnnotation, AnnotationType } from '@/types/platform';

export const Route = createFileRoute('/memories')({
  component: MemoriesPage,
});

type ConfidenceFilter = 'all' | 'high' | 'medium' | 'low';

function getConfidenceLevel(confidence: number): 'high' | 'medium' | 'low' {
  if (confidence > 0.8) return 'high';
  if (confidence > 0.5) return 'medium';
  return 'low';
}

function getConfidenceColor(confidence: number): string {
  if (confidence > 0.8) return 'bg-green-500';
  if (confidence > 0.5) return 'bg-amber-500';
  return 'bg-red-500';
}

function getAnnotationVariant(type: AnnotationType): 'critical' | 'novel' | 'supportive' | 'phase' {
  switch (type) {
    case 'outdated':
      return 'critical';
    case 'correction':
      return 'novel';
    case 'confirmed':
      return 'supportive';
    case 'context':
      return 'phase';
  }
}

function MemoriesPage() {
  const [searchQuery, setSearchQuery] = useState('');
  const [confidenceFilter, setConfidenceFilter] = useState<ConfidenceFilter>('all');

  const { data, isLoading, isError, error } = useQuery({
    queryKey: queryKeys.memories.all(),
    queryFn: () => getMemories(),
  });

  const memories = data?.memories ?? [];

  const filteredMemories = memories.filter((memory) => {
    if (confidenceFilter !== 'all' && getConfidenceLevel(memory.confidence) !== confidenceFilter) {
      return false;
    }
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const matchesTopic = memory.topic.toLowerCase().includes(q);
      const matchesSubreddit = memory.subreddit_name.toLowerCase().includes(q);
      const matchesConclusions = memory.key_conclusions.some((c) => c.toLowerCase().includes(q));
      if (!matchesTopic && !matchesSubreddit && !matchesConclusions) {
        return false;
      }
    }
    return true;
  });

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <PageHeader
        title="Memories"
        subtitle="Institutional knowledge from deliberations"
      />

      {/* Filter controls */}
      <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-center">
        <input
          type="text"
          placeholder="Search memories..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="h-9 rounded-md border border-border-default bg-bg-secondary px-3 text-sm text-text-primary placeholder:text-text-muted focus:outline-none focus:ring-1 focus:ring-accent sm:w-72"
        />
        <div className="flex items-center gap-1">
          <span className="text-[10px] font-bold uppercase tracking-widest text-text-muted mr-2">
            Confidence
          </span>
          {(['all', 'high', 'medium', 'low'] as ConfidenceFilter[]).map((level) => (
            <button
              key={level}
              onClick={() => setConfidenceFilter(level)}
              className={cn(
                'rounded-md px-3 py-1 text-xs font-medium transition-colors cursor-pointer',
                confidenceFilter === level
                  ? 'bg-accent text-white'
                  : 'bg-bg-tertiary text-text-secondary hover:text-text-primary',
              )}
            >
              {level.charAt(0).toUpperCase() + level.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {/* Loading state */}
      {isLoading && (
        <div className="space-y-4">
          <Skeleton className="h-40 w-full" />
          <Skeleton className="h-40 w-full" />
          <Skeleton className="h-40 w-full" />
        </div>
      )}

      {/* Error state */}
      {isError && (
        <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-400">
          Failed to load memories: {error?.message ?? 'Unknown error'}
        </div>
      )}

      {/* Empty state */}
      {!isLoading && !isError && filteredMemories.length === 0 && (
        <EmptyState
          title="No memories found"
          description={
            searchQuery || confidenceFilter !== 'all'
              ? 'Try adjusting your search or filter criteria.'
              : 'Memories are created when deliberations produce conclusions.'
          }
        />
      )}

      {/* Memory list */}
      {!isLoading && !isError && filteredMemories.length > 0 && (
        <div className="space-y-4">
          {filteredMemories.map((memory) => (
            <MemoryCard key={memory.id} memory={memory} />
          ))}
        </div>
      )}
    </div>
  );
}

function MemoryCard({ memory }: { memory: Memory }) {
  const [annotationsExpanded, setAnnotationsExpanded] = useState(false);
  const [showAnnotationForm, setShowAnnotationForm] = useState(false);

  return (
    <div className="rounded-lg border border-border-subtle bg-bg-secondary p-4">
      {/* Header row */}
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex items-center gap-2 flex-wrap">
          <h3 className="text-sm font-bold text-text-primary">{memory.topic}</h3>
          <Badge variant="outline">c/{memory.subreddit_name}</Badge>
        </div>
        <span className="text-xs text-text-muted whitespace-nowrap">{timeAgo(memory.created_at)}</span>
      </div>

      {/* Confidence bar */}
      <div className="mb-3">
        <div className="flex items-center justify-between mb-1">
          <span className="text-[10px] font-bold uppercase tracking-widest text-text-muted">
            Confidence
          </span>
          <span className="text-xs text-text-secondary">
            {(memory.confidence * 100).toFixed(0)}%
          </span>
        </div>
        <div className="h-1.5 w-full rounded-full bg-bg-tertiary overflow-hidden">
          <div
            className={cn('h-full rounded-full transition-all', getConfidenceColor(memory.confidence))}
            style={{ width: `${memory.confidence * 100}%` }}
          />
        </div>
      </div>

      {/* Key conclusions */}
      {memory.key_conclusions.length > 0 && (
        <div className="mb-3">
          <span className="text-[10px] font-bold uppercase tracking-widest text-text-muted">
            Key Conclusions
          </span>
          <ul className="mt-1 space-y-1">
            {memory.key_conclusions.map((conclusion, i) => (
              <li key={i} className="flex items-start gap-2 text-xs text-text-secondary">
                <span className="mt-1 h-1 w-1 shrink-0 rounded-full bg-text-muted" />
                {conclusion}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Metadata row */}
      <div className="flex flex-wrap items-center gap-2 mb-3">
        <Badge variant="default">{memory.evidence_quality}</Badge>
        <Badge variant="default">{memory.template_type}</Badge>
        <span className="text-xs text-text-muted">
          {memory.citations_used.length} citation{memory.citations_used.length !== 1 ? 's' : ''}
        </span>
        <span className="text-xs text-text-muted">
          {memory.agents_involved.length} agent{memory.agents_involved.length !== 1 ? 's' : ''}
        </span>
      </div>

      {/* Annotations section */}
      <div className="border-t border-border-subtle pt-3">
        <div className="flex items-center justify-between">
          <button
            onClick={() => setAnnotationsExpanded(!annotationsExpanded)}
            className="flex items-center gap-1.5 text-xs text-text-secondary hover:text-text-primary transition-colors cursor-pointer"
          >
            <svg
              className={cn('h-3 w-3 transition-transform', annotationsExpanded && 'rotate-90')}
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
            >
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
            </svg>
            {memory.annotations.length} annotation{memory.annotations.length !== 1 ? 's' : ''}
          </button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => {
              setShowAnnotationForm(!showAnnotationForm);
              if (!annotationsExpanded) setAnnotationsExpanded(true);
            }}
          >
            Add Annotation
          </Button>
        </div>

        {annotationsExpanded && (
          <div className="mt-3 space-y-2">
            {memory.annotations.length === 0 && !showAnnotationForm && (
              <p className="text-xs text-text-muted">No annotations yet.</p>
            )}
            {memory.annotations.map((annotation) => (
              <AnnotationItem key={annotation.id} annotation={annotation} />
            ))}
            {showAnnotationForm && (
              <AnnotationForm
                memoryId={memory.id}
                onClose={() => setShowAnnotationForm(false)}
              />
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function AnnotationItem({ annotation }: { annotation: MemoryAnnotation }) {
  return (
    <div className="rounded-md border border-border-subtle bg-bg-tertiary p-3">
      <div className="flex items-center gap-2 mb-1.5">
        <Badge variant={getAnnotationVariant(annotation.annotation_type)}>
          {annotation.annotation_type}
        </Badge>
        <span className="text-xs text-text-muted">by {annotation.created_by}</span>
        <span className="text-xs text-text-muted">{timeAgo(annotation.created_at)}</span>
      </div>
      <p className="text-xs text-text-secondary">{annotation.content}</p>
    </div>
  );
}

function AnnotationForm({ memoryId, onClose }: { memoryId: string; onClose: () => void }) {
  const queryClient = useQueryClient();
  const [annotationType, setAnnotationType] = useState<AnnotationType>('context');
  const [content, setContent] = useState('');
  const [createdBy, setCreatedBy] = useState('human');

  const mutation = useMutation({
    mutationFn: (data: { annotation_type: string; content: string; created_by: string }) =>
      annotateMemory(memoryId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.memories.all() });
      onClose();
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!content.trim()) return;
    mutation.mutate({ annotation_type: annotationType, content: content.trim(), created_by: createdBy.trim() || 'human' });
  };

  return (
    <form onSubmit={handleSubmit} className="rounded-md border border-border-default bg-bg-tertiary p-3 space-y-3">
      <div>
        <label className="text-[10px] font-bold uppercase tracking-widest text-text-muted block mb-1">
          Type
        </label>
        <select
          value={annotationType}
          onChange={(e) => setAnnotationType(e.target.value as AnnotationType)}
          className="h-8 w-full rounded-md border border-border-default bg-bg-secondary px-2 text-xs text-text-primary focus:outline-none focus:ring-1 focus:ring-accent"
        >
          <option value="outdated">Outdated</option>
          <option value="correction">Correction</option>
          <option value="confirmed">Confirmed</option>
          <option value="context">Context</option>
        </select>
      </div>
      <div>
        <label className="text-[10px] font-bold uppercase tracking-widest text-text-muted block mb-1">
          Content
        </label>
        <textarea
          value={content}
          onChange={(e) => setContent(e.target.value)}
          rows={3}
          placeholder="Enter annotation content..."
          className="w-full rounded-md border border-border-default bg-bg-secondary px-3 py-2 text-xs text-text-primary placeholder:text-text-muted focus:outline-none focus:ring-1 focus:ring-accent resize-none"
        />
      </div>
      <div>
        <label className="text-[10px] font-bold uppercase tracking-widest text-text-muted block mb-1">
          Created By
        </label>
        <input
          type="text"
          value={createdBy}
          onChange={(e) => setCreatedBy(e.target.value)}
          className="h-8 w-full rounded-md border border-border-default bg-bg-secondary px-3 text-xs text-text-primary placeholder:text-text-muted focus:outline-none focus:ring-1 focus:ring-accent"
        />
      </div>
      <div className="flex items-center gap-2 justify-end">
        <Button type="button" variant="ghost" size="sm" onClick={onClose}>
          Cancel
        </Button>
        <Button type="submit" size="sm" disabled={!content.trim() || mutation.isPending}>
          {mutation.isPending ? 'Submitting...' : 'Submit'}
        </Button>
      </div>
      {mutation.isError && (
        <p className="text-xs text-red-400">
          Failed to submit: {mutation.error?.message ?? 'Unknown error'}
        </p>
      )}
    </form>
  );
}
