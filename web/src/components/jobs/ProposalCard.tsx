import { cn } from '@/lib/utils'
import type { ActionProposal } from '@/types/jobs'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'

interface ProposalCardProps {
  proposal: ActionProposal
  className?: string
  onApprove?: (proposalId: string) => void
  onReject?: (proposalId: string) => void
}

export function ProposalCard({ proposal, className, onApprove, onReject }: ProposalCardProps) {
  const isPending = proposal.status === 'pending'

  return (
    <Card className={cn('border-l-4 border-l-yellow-500', className)}>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-medium">{proposal.description}</CardTitle>
          <Badge
            variant="outline"
            className={cn(
              'text-xs',
              isPending
                ? 'bg-yellow-500/10 text-yellow-500'
                : proposal.status === 'approved'
                  ? 'bg-green-500/10 text-green-500'
                  : 'bg-red-500/10 text-red-500',
            )}
          >
            {proposal.status}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-2 text-xs text-muted-foreground">
        <p>
          <span className="font-medium text-foreground">Agent:</span> {proposal.agent_id}
        </p>
        <p>
          <span className="font-medium text-foreground">Rationale:</span> {proposal.rationale}
        </p>
        {proposal.proposed_pipeline && (
          <div>
            <span className="font-medium text-foreground">Pipeline:</span>{' '}
            {proposal.proposed_pipeline.name}
            {proposal.proposed_pipeline.steps.length > 0 && (
              <p className="ml-2">
                Steps: {proposal.proposed_pipeline.steps.map((s) => s.process_id).join(' → ')}
              </p>
            )}
          </div>
        )}
        {proposal.review_note && (
          <p>
            <span className="font-medium text-foreground">Review note:</span>{' '}
            {proposal.review_note}
          </p>
        )}
      </CardContent>
      {isPending && (onApprove || onReject) && (
        <CardFooter className="gap-2 pt-0">
          {onApprove && (
            <Button size="sm" variant="default" onClick={() => onApprove(proposal.id)}>
              Approve
            </Button>
          )}
          {onReject && (
            <Button size="sm" variant="outline" onClick={() => onReject(proposal.id)}>
              Reject
            </Button>
          )}
        </CardFooter>
      )}
    </Card>
  )
}
