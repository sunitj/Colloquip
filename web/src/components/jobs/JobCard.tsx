import { cn } from '@/lib/utils'
import type { Job, JobStatus } from '@/types/jobs'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

const statusColors: Record<JobStatus, string> = {
  pending: 'bg-yellow-500/10 text-yellow-500',
  approved: 'bg-blue-500/10 text-blue-500',
  submitted: 'bg-blue-500/10 text-blue-500',
  running: 'bg-purple-500/10 text-purple-500',
  completed: 'bg-green-500/10 text-green-500',
  failed: 'bg-red-500/10 text-red-500',
  cancelled: 'bg-gray-500/10 text-gray-500',
}

const statusLabels: Record<JobStatus, string> = {
  pending: 'Pending',
  approved: 'Approved',
  submitted: 'Submitted',
  running: 'Running',
  completed: 'Completed',
  failed: 'Failed',
  cancelled: 'Cancelled',
}

interface JobCardProps {
  job: Job
  className?: string
  onClick?: () => void
}

export function JobCard({ job, className, onClick }: JobCardProps) {
  const statusColor = statusColors[job.status]
  const isActive = job.status === 'running' || job.status === 'submitted'

  return (
    <Card
      className={cn('cursor-pointer transition-colors hover:bg-muted/50', className)}
      onClick={onClick}
    >
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-medium">{job.pipeline.name}</CardTitle>
          <Badge className={cn('text-xs', statusColor)} variant="outline">
            {isActive && <span className="mr-1 inline-block h-2 w-2 animate-pulse rounded-full bg-current" />}
            {statusLabels[job.status]}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-1 text-xs text-muted-foreground">
        <p>Agent: {job.agent_id}</p>
        <p>Backend: {job.compute_backend} / {job.compute_profile}</p>
        {job.pipeline.steps.length > 0 && (
          <p>Steps: {job.pipeline.steps.map((s) => s.process_id).join(' → ')}</p>
        )}
        {job.result_summary && (
          <p className="mt-2 text-foreground">{job.result_summary}</p>
        )}
        {job.error_message && (
          <p className="mt-2 text-red-500">{job.error_message}</p>
        )}
        {job.result_artifacts.length > 0 && (
          <div className="mt-2">
            <p className="font-medium text-foreground">Artifacts:</p>
            <ul className="ml-2 list-disc">
              {job.result_artifacts.map((a) => (
                <li key={a.name}>
                  {a.name} ({a.artifact_type}) - {a.description}
                </li>
              ))}
            </ul>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
