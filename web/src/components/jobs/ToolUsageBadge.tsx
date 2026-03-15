import { cn } from '@/lib/utils'
import type { ToolInvocation } from '@/types/deliberation'
import { Badge } from '@/components/ui/badge'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip'

const toolIcons: Record<string, string> = {
  pubmed_search: 'PubMed',
  pdb_search: 'PDB',
  uniprot_search: 'UniProt',
  database_query: 'DB Query',
  nf_process_library: 'NF Library',
  job_status: 'Job Status',
  web_search: 'Web',
  company_docs: 'Docs',
}

interface ToolUsageBadgeProps {
  invocations: ToolInvocation[]
  className?: string
}

export function ToolUsageBadge({ invocations, className }: ToolUsageBadgeProps) {
  if (!invocations || invocations.length === 0) return null

  return (
    <TooltipProvider>
      <div className={cn('flex flex-wrap gap-1', className)}>
        {invocations.map((inv, i) => (
          <Tooltip key={i}>
            <TooltipTrigger>
              <Badge variant="outline" className="text-[10px] text-muted-foreground">
                {toolIcons[inv.tool_name] ?? inv.tool_name}
                {inv.duration_ms > 0 && ` (${Math.round(inv.duration_ms)}ms)`}
              </Badge>
            </TooltipTrigger>
            <TooltipContent side="top" className="max-w-xs">
              <div className="space-y-1 text-xs">
                <p className="font-medium">{inv.tool_name}</p>
                <p className="text-muted-foreground">
                  Input: {JSON.stringify(inv.tool_input, null, 0).slice(0, 100)}
                </p>
                {inv.tool_result?.error && (
                  <p className="text-red-500">Error: {String(inv.tool_result.error)}</p>
                )}
              </div>
            </TooltipContent>
          </Tooltip>
        ))}
      </div>
    </TooltipProvider>
  )
}
