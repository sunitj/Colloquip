import { useQuery } from '@tanstack/react-query';
import { getThreadCosts } from '@/lib/api';
import { queryKeys } from '@/lib/queryKeys';

interface ThreadCostSummaryProps {
  threadId: string;
}

export function ThreadCostSummary({ threadId }: ThreadCostSummaryProps) {
  const { data: costs } = useQuery({
    queryKey: queryKeys.threads.costs(threadId),
    queryFn: () => getThreadCosts(threadId),
  });

  if (!costs) return null;

  return (
    <div className="space-y-2">
      <div className="text-[10px] font-bold uppercase tracking-widest text-text-muted">
        Costs
      </div>
      <div className="grid grid-cols-2 gap-2 text-xs">
        <div className="bg-bg-tertiary/50 rounded p-2">
          <div className="text-text-muted text-[10px]">Total Cost</div>
          <div className="text-text-primary font-medium">${costs.estimated_cost_usd.toFixed(4)}</div>
        </div>
        <div className="bg-bg-tertiary/50 rounded p-2">
          <div className="text-text-muted text-[10px]">LLM Calls</div>
          <div className="text-text-primary font-medium">{costs.num_llm_calls}</div>
        </div>
        <div className="bg-bg-tertiary/50 rounded p-2">
          <div className="text-text-muted text-[10px]">Input Tokens</div>
          <div className="text-text-primary font-medium">{costs.total_input_tokens.toLocaleString()}</div>
        </div>
        <div className="bg-bg-tertiary/50 rounded p-2">
          <div className="text-text-muted text-[10px]">Output Tokens</div>
          <div className="text-text-primary font-medium">{costs.total_output_tokens.toLocaleString()}</div>
        </div>
      </div>
      {costs.duration_seconds && (
        <div className="text-[10px] text-text-muted text-center">
          Duration: {Math.round(costs.duration_seconds)}s
        </div>
      )}
    </div>
  );
}
