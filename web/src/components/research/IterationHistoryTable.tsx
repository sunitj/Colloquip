import { useState, useEffect } from 'react'
import { cn, formatCost } from '@/lib/utils'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import type { ResearchIteration } from '@/types/platform'
import { getResearchJobResults } from '@/lib/api'

type SortKey = 'iteration' | 'metric' | 'cost_usd'
type SortDir = 'asc' | 'desc'

interface IterationHistoryTableProps {
  jobId: string
  className?: string
}

export function IterationHistoryTable({ jobId, className }: IterationHistoryTableProps) {
  const [iterations, setIterations] = useState<ResearchIteration[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [sortKey, setSortKey] = useState<SortKey>('iteration')
  const [sortDir, setSortDir] = useState<SortDir>('asc')

  useEffect(() => {
    setLoading(true)
    getResearchJobResults(jobId)
      .then((data) => { setIterations(data.iterations); setError(null) })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }, [jobId])

  const handleSort = (key: SortKey) => {
    if (key === sortKey) {
      setSortDir(sortDir === 'asc' ? 'desc' : 'asc')
    } else {
      setSortKey(key)
      setSortDir('asc')
    }
  }

  const sorted = [...iterations].sort((a, b) => {
    const mul = sortDir === 'asc' ? 1 : -1
    return (a[sortKey] - b[sortKey]) * mul
  })

  const arrow = (key: SortKey) => sortKey === key ? (sortDir === 'asc' ? ' \u2191' : ' \u2193') : ''

  return (
    <Card className={cn(className)}>
      <CardHeader className="pb-3">
        <CardTitle className="text-sm font-medium">Iteration History</CardTitle>
      </CardHeader>
      <CardContent>
        {loading ? (
          <Skeleton className="h-40" />
        ) : error ? (
          <p className="text-xs text-red-500">{error}</p>
        ) : iterations.length === 0 ? (
          <p className="text-xs text-muted-foreground">No iterations completed yet.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-border-default text-left text-muted-foreground">
                  <th className="cursor-pointer px-2 py-1.5 font-medium" onClick={() => handleSort('iteration')}>
                    #{arrow('iteration')}
                  </th>
                  <th className="px-2 py-1.5 font-medium">Hypothesis</th>
                  <th className="cursor-pointer px-2 py-1.5 font-medium" onClick={() => handleSort('metric')}>
                    Metric{arrow('metric')}
                  </th>
                  <th className="px-2 py-1.5 font-medium">Status</th>
                  <th className="cursor-pointer px-2 py-1.5 font-medium" onClick={() => handleSort('cost_usd')}>
                    Cost{arrow('cost_usd')}
                  </th>
                </tr>
              </thead>
              <tbody>
                {sorted.map((iter) => (
                  <tr key={iter.iteration} className="border-b border-border-default/50 hover:bg-muted/30">
                    <td className="px-2 py-1.5 tabular-nums">{iter.iteration + 1}</td>
                    <td className="max-w-[300px] truncate px-2 py-1.5" title={iter.hypothesis}>
                      {iter.hypothesis}
                    </td>
                    <td className="px-2 py-1.5 tabular-nums">{iter.metric.toFixed(3)}</td>
                    <td className="px-2 py-1.5">
                      <Badge
                        variant="outline"
                        className={cn(
                          'text-xs',
                          iter.status === 'keep'
                            ? 'bg-green-500/10 text-green-500'
                            : 'bg-red-500/10 text-red-500',
                        )}
                      >
                        {iter.status}
                      </Badge>
                    </td>
                    <td className="px-2 py-1.5 tabular-nums">{formatCost(iter.cost_usd)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
