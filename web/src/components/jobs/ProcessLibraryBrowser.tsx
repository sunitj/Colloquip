import { useState } from 'react'
import { cn } from '@/lib/utils'
import type { NextflowProcess } from '@/types/jobs'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'

const categoryColors: Record<string, string> = {
  structure_prediction: 'bg-blue-500/10 text-blue-500',
  sequence_alignment: 'bg-green-500/10 text-green-500',
  structure_search: 'bg-purple-500/10 text-purple-500',
  protein_design: 'bg-orange-500/10 text-orange-500',
  structure_refinement: 'bg-cyan-500/10 text-cyan-500',
  simulation: 'bg-red-500/10 text-red-500',
  analysis: 'bg-yellow-500/10 text-yellow-500',
}

interface ProcessLibraryBrowserProps {
  processes: NextflowProcess[]
  className?: string
  onSelect?: (process: NextflowProcess) => void
}

export function ProcessLibraryBrowser({
  processes,
  className,
  onSelect,
}: ProcessLibraryBrowserProps) {
  const [search, setSearch] = useState('')
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null)

  const categories = [...new Set(processes.map((p) => p.category))]

  const filtered = processes.filter((p) => {
    const matchesSearch =
      !search ||
      p.name.toLowerCase().includes(search.toLowerCase()) ||
      p.description.toLowerCase().includes(search.toLowerCase()) ||
      p.process_id.toLowerCase().includes(search.toLowerCase())
    const matchesCategory = !selectedCategory || p.category === selectedCategory
    return matchesSearch && matchesCategory
  })

  return (
    <div className={cn('space-y-4', className)}>
      <div className="space-y-2">
        <Input
          placeholder="Search processes..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <div className="flex flex-wrap gap-1">
          <Badge
            variant={selectedCategory === null ? 'default' : 'outline'}
            className="cursor-pointer text-xs"
            onClick={() => setSelectedCategory(null)}
          >
            All
          </Badge>
          {categories.map((cat) => (
            <Badge
              key={cat}
              variant={selectedCategory === cat ? 'default' : 'outline'}
              className={cn('cursor-pointer text-xs', categoryColors[cat])}
              onClick={() => setSelectedCategory(cat === selectedCategory ? null : cat)}
            >
              {cat.replace(/_/g, ' ')}
            </Badge>
          ))}
        </div>
      </div>

      <div className="space-y-2">
        {filtered.map((process) => (
          <Card
            key={process.process_id}
            className="cursor-pointer transition-colors hover:bg-muted/50"
            onClick={() => onSelect?.(process)}
          >
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <CardTitle className="text-sm font-medium">{process.name}</CardTitle>
                <Badge
                  variant="outline"
                  className={cn('text-xs', categoryColors[process.category])}
                >
                  {process.category.replace(/_/g, ' ')}
                </Badge>
              </div>
            </CardHeader>
            <CardContent className="space-y-2 text-xs text-muted-foreground">
              <p>{process.description}</p>
              <div className="flex gap-4">
                <span>
                  In: {process.input_channels.map((c) => `${c.name}(${c.data_type})`).join(', ')}
                </span>
                <span>
                  Out: {process.output_channels.map((c) => `${c.name}(${c.data_type})`).join(', ')}
                </span>
              </div>
              <div className="flex gap-3">
                <span>CPUs: {process.resource_requirements.cpus}</span>
                <span>RAM: {process.resource_requirements.memory_gb}GB</span>
                {process.resource_requirements.gpu && <span>GPU</span>}
                <span>~{process.resource_requirements.estimated_runtime_minutes}min</span>
              </div>
            </CardContent>
          </Card>
        ))}
        {filtered.length === 0 && (
          <p className="py-4 text-center text-sm text-muted-foreground">No processes found</p>
        )}
      </div>
    </div>
  )
}
