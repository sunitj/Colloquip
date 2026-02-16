import { useQuery } from '@tanstack/react-query';
import { DollarSign, Zap, Hash, Clock } from 'lucide-react';
import { formatCost, formatNumber } from '@/lib/utils';
import { getThreadCosts } from '@/lib/api';
import { queryKeys } from '@/lib/queryKeys';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';

interface ThreadCostSummaryProps {
  threadId: string;
}

function formatDuration(seconds: number | null): string {
  if (seconds == null) return '--';
  if (seconds < 60) return `${Math.round(seconds)}s`;
  const mins = Math.floor(seconds / 60);
  const secs = Math.round(seconds % 60);
  return `${mins}m ${secs}s`;
}

export function ThreadCostSummary({ threadId }: ThreadCostSummaryProps) {
  const { data: costs, isLoading } = useQuery({
    queryKey: queryKeys.threads.costs(threadId),
    queryFn: () => getThreadCosts(threadId),
  });

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-sm">Cost Summary</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-3/4" />
          <Skeleton className="h-4 w-1/2" />
        </CardContent>
      </Card>
    );
  }

  if (!costs) return null;

  const items = [
    {
      icon: DollarSign,
      label: 'Total Cost',
      value: formatCost(costs.estimated_cost_usd),
    },
    {
      icon: Zap,
      label: 'LLM Calls',
      value: costs.num_llm_calls.toString(),
    },
    {
      icon: Hash,
      label: 'Tokens',
      value: formatNumber(costs.total_tokens),
    },
    {
      icon: Clock,
      label: 'Duration',
      value: formatDuration(costs.duration_seconds),
    },
  ];

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm">Cost Summary</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {items.map(({ icon: Icon, label, value }) => (
          <div key={label} className="flex items-center justify-between">
            <span className="flex items-center gap-2 text-xs text-text-muted">
              <Icon className="h-3.5 w-3.5" />
              {label}
            </span>
            <span className="text-sm font-medium text-text-primary">{value}</span>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
