import { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Textarea } from '@/components/ui/textarea';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { useSubredditMission, useUpdateMission } from '@/hooks/dashboards';

interface MissionEditorProps {
  subredditName: string;
}

const PLACEHOLDER = `# Mission

What is this community trying to achieve?

## Objective: Reduce false positive claims
Cut hallucinated citations in synthesis.
- metric: citation_verification_rate
- target: 0.85

## Objective: Surface novel mechanisms
- metric: novelty_avg
- target: 0.5
`;

export function MissionEditor({ subredditName }: MissionEditorProps) {
  const { data, isLoading } = useSubredditMission(subredditName);
  const updateMutation = useUpdateMission(subredditName);
  const remoteMarkdown = data?.mission_md ?? '';
  const [lastSeenRemote, setLastSeenRemote] = useState<string>(remoteMarkdown);
  const [draftOverride, setDraftOverride] = useState<string | null>(null);

  // Derive the textarea value: user edits take priority; otherwise reflect
  // whatever the server last returned. When the server value changes while
  // the user has no unsaved edits, fold it in automatically.
  if (lastSeenRemote !== remoteMarkdown) {
    setLastSeenRemote(remoteMarkdown);
    if (draftOverride === null || draftOverride === lastSeenRemote) {
      setDraftOverride(null);
    }
  }
  const draft = draftOverride !== null ? draftOverride : remoteMarkdown;

  const handleChange = (value: string) => {
    setDraftOverride(value);
  };

  const handleSave = () => {
    updateMutation.mutate(
      {
        mission_md: draft || null,
        regenerate_objectives: true,
      },
      {
        onSuccess: () => setDraftOverride(null),
      },
    );
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Subreddit Mission</CardTitle>
        <CardDescription>
          Karpathy-style <code>program.md</code> directive. <code>## Objective:</code> headings
          with <code>- metric:</code> / <code>- target:</code> bullets are auto-extracted as
          trackable goals. Mission text is injected into every agent's system prompt.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <Textarea
          value={draft}
          onChange={(e) => handleChange(e.target.value)}
          placeholder={PLACEHOLDER}
          rows={16}
          className="font-mono text-sm"
          disabled={isLoading}
        />
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex flex-wrap gap-1.5">
            {(data?.objectives ?? []).map((obj) => (
              <Badge key={obj.id} variant="outline">
                {obj.title}
                {obj.metric ? (
                  <span className="ml-1 text-text-muted">· {obj.metric}</span>
                ) : null}
              </Badge>
            ))}
            {data?.version ? (
              <span className="text-xs text-text-muted">v{data.version}</span>
            ) : null}
          </div>
          <Button
            onClick={handleSave}
            disabled={updateMutation.isPending || isLoading}
          >
            {updateMutation.isPending ? 'Saving…' : 'Save mission'}
          </Button>
        </div>
        {updateMutation.error ? (
          <p className="text-sm text-state-danger">
            {(updateMutation.error as Error).message}
          </p>
        ) : null}
      </CardContent>
    </Card>
  );
}
