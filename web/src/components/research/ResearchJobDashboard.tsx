import { useState, useEffect, useCallback } from 'react'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import type { ResearchJob, ResearchJobStatus } from '@/types/platform'
import {
  getResearchJobs,
  createResearchJob,
  pauseResearchJob,
  resumeResearchJob,
  stopResearchJob,
} from '@/lib/api'

const statusColors: Record<ResearchJobStatus, string> = {
  pending: 'bg-yellow-500/10 text-yellow-500',
  running: 'bg-purple-500/10 text-purple-500',
  paused: 'bg-blue-500/10 text-blue-500',
  completed: 'bg-green-500/10 text-green-500',
  failed: 'bg-red-500/10 text-red-500',
  stopped: 'bg-gray-500/10 text-gray-500',
}

interface ResearchJobDashboardProps {
  subredditName: string
  className?: string
  onSelectJob?: (job: ResearchJob) => void
}

export function ResearchJobDashboard({ subredditName, className, onSelectJob }: ResearchJobDashboardProps) {
  const [jobs, setJobs] = useState<ResearchJob[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [creating, setCreating] = useState(false)

  const refresh = useCallback(() => {
    setLoading(true)
    getResearchJobs(subredditName)
      .then((data) => { setJobs(data.jobs); setError(null) })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }, [subredditName])

  useEffect(() => { refresh() }, [refresh])

  const handleCreate = async () => {
    setCreating(true)
    try {
      await createResearchJob(subredditName, { max_iterations: 50, max_cost_usd: 25.0 })
      refresh()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Create failed')
    } finally {
      setCreating(false)
    }
  }

  const handleAction = async (jobId: string, action: 'pause' | 'resume' | 'stop') => {
    try {
      if (action === 'pause') await pauseResearchJob(jobId)
      else if (action === 'resume') await resumeResearchJob(jobId)
      else await stopResearchJob(jobId)
      refresh()
    } catch (e) {
      setError(e instanceof Error ? e.message : `${action} failed`)
    }
  }

  const hasActiveJob = jobs.some((j) => j.status === 'running' || j.status === 'pending' || j.status === 'paused')

  return (
    <Card className={cn(className)}>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-medium">Research Jobs</CardTitle>
          <Button size="sm" onClick={handleCreate} disabled={creating || hasActiveJob}>
            {creating ? 'Creating...' : 'New Job'}
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        {loading ? (
          <div className="space-y-2">
            {[0, 1].map((i) => <div key={i} className="h-20 animate-pulse rounded-md bg-muted" />)}
          </div>
        ) : error ? (
          <p className="text-xs text-red-500">{error}</p>
        ) : jobs.length === 0 ? (
          <p className="text-xs text-muted-foreground">No research jobs yet. Create one to start autonomous research.</p>
        ) : (
          <div className="space-y-3">
            {jobs.map((job) => (
              <JobRow key={job.id} job={job} onAction={handleAction} onClick={() => onSelectJob?.(job)} />
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}

function JobRow({
  job,
  onAction,
  onClick,
}: {
  job: ResearchJob
  onAction: (id: string, action: 'pause' | 'resume' | 'stop') => void
  onClick?: () => void
}) {
  const progress = job.max_iterations > 0
    ? (job.current_iteration / job.max_iterations) * 100
    : 0
  const isActive = job.status === 'running' || job.status === 'paused'

  return (
    <div
      className="rounded-md border border-border-default p-3 space-y-2 cursor-pointer hover:bg-muted/50 transition-colors"
      onClick={onClick}
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Badge className={cn('text-xs', statusColors[job.status])} variant="outline">
            {job.status === 'running' && (
              <span className="mr-1 inline-block h-2 w-2 animate-pulse rounded-full bg-current" />
            )}
            {job.status}
          </Badge>
          <span className="text-xs text-muted-foreground">
            {job.current_iteration}/{job.max_iterations} iterations
          </span>
        </div>
        <div className="flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
          {job.status === 'running' && (
            <Button size="sm" variant="ghost" onClick={() => onAction(job.id, 'pause')}>
              Pause
            </Button>
          )}
          {job.status === 'paused' && (
            <Button size="sm" variant="ghost" onClick={() => onAction(job.id, 'resume')}>
              Resume
            </Button>
          )}
          {isActive && (
            <Button size="sm" variant="ghost" className="text-red-500" onClick={() => onAction(job.id, 'stop')}>
              Stop
            </Button>
          )}
        </div>
      </div>
      <Progress value={progress} className="h-1.5" />
      <div className="flex gap-4 text-xs text-muted-foreground">
        <span>${job.total_cost_usd.toFixed(2)} / ${job.max_cost_usd.toFixed(2)}</span>
        {job.best_metric !== null && <span>Best: {job.best_metric.toFixed(3)}</span>}
        <span>{job.threads_completed.length} kept, {job.threads_discarded.length} discarded</span>
      </div>
    </div>
  )
}
