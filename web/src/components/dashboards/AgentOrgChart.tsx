import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { useOrgChart } from '@/hooks/dashboards';
import type { OrgChartNode } from '@/types/dashboards';

interface AgentOrgChartProps {
  subredditName: string;
}

function roleBadge(node: OrgChartNode) {
  if (node.is_red_team || node.role === 'red_team') {
    return <Badge className="bg-state-danger text-white">Red team</Badge>;
  }
  if (node.role === 'moderator') {
    return <Badge className="bg-state-info text-white">Moderator</Badge>;
  }
  return <Badge variant="outline">Member</Badge>;
}

function groupByRole(nodes: OrgChartNode[]): Record<string, OrgChartNode[]> {
  const groups: Record<string, OrgChartNode[]> = {
    moderator: [],
    member: [],
    red_team: [],
  };
  for (const node of nodes) {
    const key =
      node.is_red_team || node.role === 'red_team'
        ? 'red_team'
        : node.role === 'moderator'
          ? 'moderator'
          : 'member';
    groups[key].push(node);
  }
  return groups;
}

export function AgentOrgChart({ subredditName }: AgentOrgChartProps) {
  const { data, isLoading } = useOrgChart(subredditName);
  const nodes = data?.nodes ?? [];
  const edges = data?.edges ?? [];
  const groups = groupByRole(nodes);
  const interactionEdges = edges.filter((e) => e.edge_type === 'triggered');

  return (
    <Card>
      <CardHeader>
        <CardTitle>Agent Org Chart</CardTitle>
        <CardDescription>
          Paperclip-style view of the subreddit's agent roster. Red-team agents sit
          adjacent to the main contributors; interaction edges are aggregated from
          posts' <code>triggered_by</code> signals.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {isLoading && <p className="text-sm text-text-muted">Loading…</p>}
        {!isLoading && nodes.length === 0 && (
          <p className="text-sm text-text-muted">No members yet.</p>
        )}
        {(['moderator', 'member', 'red_team'] as const).map((group) =>
          groups[group].length > 0 ? (
            <div key={group}>
              <p className="mb-2 text-xs font-medium uppercase tracking-wide text-text-muted">
                {group.replace('_', ' ')}
              </p>
              <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
                {groups[group].map((node) => (
                  <div
                    key={node.agent_id}
                    className="rounded-md border border-border-default bg-bg-surface p-3"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <p className="text-sm font-semibold text-text-primary">
                        {node.display_name}
                      </p>
                      {roleBadge(node)}
                    </div>
                    <p className="text-xs text-text-muted">
                      {node.post_count} posts · ${node.lifetime_cost_usd.toFixed(4)} lifetime
                      {node.reports_to && <> · reports to {node.reports_to}</>}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          ) : null,
        )}
        {interactionEdges.length > 0 && (
          <div>
            <p className="mb-2 text-xs font-medium uppercase tracking-wide text-text-muted">
              Recent interactions
            </p>
            <ul className="space-y-1 text-xs text-text-secondary">
              {interactionEdges.slice(0, 12).map((edge, i) => (
                <li key={i}>
                  {edge.from_agent_id} → {edge.to_agent_id}{' '}
                  <span className="text-text-muted">×{edge.weight.toFixed(0)}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
