import { useState, useMemo } from 'react';
import { createFileRoute } from '@tanstack/react-router';
import { useQuery } from '@tanstack/react-query';
import { Search, Brain, LayoutGrid, Network } from 'lucide-react';
import { getMemories, getMemoryGraph } from '@/lib/api';
import { queryKeys } from '@/lib/queryKeys';
import { PageHeader } from '@/components/layout/PageHeader';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
} from '@/components/ui/select';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { Skeleton } from '@/components/ui/skeleton';
import { EmptyState } from '@/components/shared/EmptyState';
import { AnimatedList, AnimatedItem } from '@/components/shared/AnimatedList';
import { MemoryCard } from '@/components/memories/MemoryCard';
import { MemoryGraph } from '@/components/memories/MemoryGraph';

export const Route = createFileRoute('/memories')({
  component: MemoriesPage,
});

type ConfidenceFilter = 'all' | 'high' | 'medium' | 'low';

function MemoriesPage() {
  const [searchText, setSearchText] = useState('');
  const [confidenceFilter, setConfidenceFilter] = useState<ConfidenceFilter>('all');

  const { data, isLoading } = useQuery({
    queryKey: queryKeys.memories.all(),
    queryFn: () => getMemories(),
  });

  const { data: graphData } = useQuery({
    queryKey: queryKeys.memories.graph,
    queryFn: () => getMemoryGraph(),
  });

  const memories = data?.memories ?? [];

  const filtered = useMemo(() => {
    let result = memories;

    // Filter by search text
    if (searchText.trim()) {
      const query = searchText.toLowerCase();
      result = result.filter((m) =>
        m.topic.toLowerCase().includes(query),
      );
    }

    // Filter by confidence
    switch (confidenceFilter) {
      case 'high':
        result = result.filter((m) => m.confidence > 0.7);
        break;
      case 'medium':
        result = result.filter((m) => m.confidence > 0.4 && m.confidence <= 0.7);
        break;
      case 'low':
        result = result.filter((m) => m.confidence <= 0.4);
        break;
    }

    return result;
  }, [memories, searchText, confidenceFilter]);

  return (
    <div>
      <PageHeader
        title="Institutional Knowledge"
        subtitle="Memories distilled from deliberations across all communities"
      />

      <Tabs defaultValue="grid">
        <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-center">
          {/* View toggle */}
          <TabsList className="shrink-0">
            <TabsTrigger value="grid" className="gap-1.5">
              <LayoutGrid className="h-3.5 w-3.5" />
              Grid
            </TabsTrigger>
            <TabsTrigger value="graph" className="gap-1.5">
              <Network className="h-3.5 w-3.5" />
              Graph
            </TabsTrigger>
          </TabsList>

          {/* Filters */}
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-text-muted" />
            <Input
              value={searchText}
              onChange={(e) => setSearchText(e.target.value)}
              placeholder="Search memories by topic..."
              className="pl-9"
            />
          </div>
          <Select
            value={confidenceFilter}
            onValueChange={(v) => setConfidenceFilter(v as ConfidenceFilter)}
          >
            <SelectTrigger className="w-full sm:w-48">
              <SelectValue placeholder="Confidence" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Confidence</SelectItem>
              <SelectItem value="high">High (&gt;0.7)</SelectItem>
              <SelectItem value="medium">Medium (0.4-0.7)</SelectItem>
              <SelectItem value="low">Low (&lt;0.4)</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {/* Grid view */}
        <TabsContent value="grid">
          {isLoading ? (
            <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
              {Array.from({ length: 6 }).map((_, i) => (
                <Skeleton key={i} className="h-56 rounded-lg" />
              ))}
            </div>
          ) : filtered.length === 0 ? (
            <EmptyState
              icon={<Brain className="h-12 w-12" />}
              title="No memories found"
              description={
                memories.length === 0
                  ? 'Memories are created when deliberations conclude. Start a thread to build institutional knowledge.'
                  : 'Try adjusting your search or confidence filter.'
              }
            />
          ) : (
            <AnimatedList className="grid grid-cols-1 gap-6 lg:grid-cols-2">
              {filtered.map((memory) => (
                <AnimatedItem key={memory.id}>
                  <MemoryCard memory={memory} />
                </AnimatedItem>
              ))}
            </AnimatedList>
          )}
        </TabsContent>

        {/* Graph view */}
        <TabsContent value="graph">
          <MemoryGraph
            memories={filtered}
            crossReferences={graphData?.cross_references ?? []}
          />
        </TabsContent>
      </Tabs>
    </div>
  );
}
