import { MissionEditor } from './MissionEditor';
import { GoalProgressTracker } from './GoalProgressTracker';
import { BudgetCostPanel } from './BudgetCostPanel';
import { AgentOrgChart } from './AgentOrgChart';
import { ApprovalQueuePanel } from './ApprovalQueuePanel';

interface CommunityDashboardProps {
  subredditName: string;
}

/**
 * Paperclip + autoresearch-inspired community dashboard.
 * Four panels plus the mission directive editor.
 */
export function CommunityDashboard({ subredditName }: CommunityDashboardProps) {
  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
      <div className="lg:col-span-2">
        <MissionEditor subredditName={subredditName} />
      </div>
      <GoalProgressTracker subredditName={subredditName} />
      <BudgetCostPanel subredditName={subredditName} />
      <AgentOrgChart subredditName={subredditName} />
      <ApprovalQueuePanel subredditName={subredditName} />
    </div>
  );
}
