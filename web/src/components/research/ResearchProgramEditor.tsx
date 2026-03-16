import { useState, useEffect } from 'react'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { getResearchProgram, updateResearchProgram } from '@/lib/api'

interface ResearchProgramEditorProps {
  subredditName: string
  className?: string
}

export function ResearchProgramEditor({ subredditName, className }: ResearchProgramEditorProps) {
  const [program, setProgram] = useState('')
  const [version, setVersion] = useState(0)
  const [saving, setSaving] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [dirty, setDirty] = useState(false)

  useEffect(() => {
    setLoading(true)
    setError(null)
    getResearchProgram(subredditName)
      .then((data) => {
        setProgram(data.content || '')
        setVersion(data.version)
        setDirty(false)
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }, [subredditName])

  const handleSave = async () => {
    setSaving(true)
    setError(null)
    try {
      const data = await updateResearchProgram(subredditName, program)
      setVersion(data.version)
      setDirty(false)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Save failed')
    } finally {
      setSaving(false)
    }
  }

  return (
    <Card className={cn(className)}>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-medium">Research Program</CardTitle>
          <div className="flex items-center gap-2">
            <Badge variant="outline" className="text-xs text-muted-foreground">
              v{version}
            </Badge>
            {dirty && (
              <Badge variant="outline" className="text-xs text-yellow-500 bg-yellow-500/10">
                Unsaved
              </Badge>
            )}
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        {loading ? (
          <Skeleton className="h-40" />
        ) : (
          <>
            <Textarea
              value={program}
              onChange={(e) => { setProgram(e.target.value); setDirty(true) }}
              placeholder="# Research Program&#10;&#10;Define objectives, hypotheses to explore, and constraints for autonomous research..."
              className="min-h-[200px] font-mono text-xs"
            />
            {error && <p className="text-xs text-red-500">{error}</p>}
            <div className="flex justify-end">
              <Button size="sm" onClick={handleSave} disabled={saving || !dirty}>
                {saving ? 'Saving...' : 'Save Program'}
              </Button>
            </div>
          </>
        )}
      </CardContent>
    </Card>
  )
}
