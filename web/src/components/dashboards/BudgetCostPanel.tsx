import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { useSubredditBudgets } from '@/hooks/dashboards';

interface BudgetCostPanelProps {
  subredditName: string;
}

function fmtUsd(value: number | null | undefined): string {
  if (value == null) return '—';
  return `$${value.toFixed(4)}`;
}

export function BudgetCostPanel({ subredditName }: BudgetCostPanelProps) {
  const { data, isLoading } = useSubredditBudgets(subredditName);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Per-Agent Budgets</CardTitle>
        <CardDescription>
          Token budgets per agent within this subreddit. Agents that exceed their cap on a
          thread are skipped (not crashed) and a budget-override approval is enqueued.
          Default thread cap: {fmtUsd(data?.max_cost_per_thread_usd)}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        {isLoading && <p className="text-sm text-text-muted">Loading…</p>}
        {!isLoading && (data?.members?.length ?? 0) === 0 && (
          <p className="text-sm text-text-muted">No members.</p>
        )}
        {data?.members?.map((m) => {
          const threadCap = m.max_cost_per_thread_usd ?? data.max_cost_per_thread_usd;
          const monthlyCap = m.monthly_budget_usd ?? data.monthly_budget_usd;
          const monthlyUsed = m.current_month_cost_usd ?? 0;
          const monthlyPct =
            monthlyCap && monthlyCap > 0
              ? Math.min(100, (monthlyUsed / monthlyCap) * 100)
              : 0;
          return (
            <div
              key={m.agent_id}
              className="rounded-md border border-border-default p-3"
            >
              <div className="flex items-start justify-between gap-2">
                <div>
                  <p className="text-sm font-semibold text-text-primary">
                    {m.display_name ?? m.agent_type ?? m.agent_id}
                  </p>
                  <p className="text-xs text-text-muted">
                    {m.role ?? 'member'} · thread cap {fmtUsd(threadCap)} · monthly{' '}
                    {fmtUsd(monthlyCap)}
                  </p>
                </div>
                <Badge variant="outline">
                  lifetime {fmtUsd(m.lifetime_cost_usd)}
                </Badge>
              </div>
              {monthlyCap && monthlyCap > 0 ? (
                <div className="mt-2 space-y-1">
                  <Progress value={monthlyPct} />
                  <p className="text-xs text-text-muted">
                    {fmtUsd(monthlyUsed)} / {fmtUsd(monthlyCap)} this month (
                    {monthlyPct.toFixed(0)}%)
                  </p>
                </div>
              ) : null}
            </div>
          );
        })}
      </CardContent>
    </Card>
  );
}
