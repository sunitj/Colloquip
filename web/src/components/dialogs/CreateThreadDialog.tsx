import { useState } from 'react';
import { useNavigate } from '@tanstack/react-router';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { createThread } from '@/lib/api';
import { queryKeys } from '@/lib/queryKeys';
import { Dialog, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/Dialog';
import { Button } from '@/components/ui/Button';

interface CreateThreadDialogProps {
  open: boolean;
  onClose: () => void;
  subredditName: string;
}

export function CreateThreadDialog({ open, onClose, subredditName }: CreateThreadDialogProps) {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [title, setTitle] = useState('');
  const [hypothesis, setHypothesis] = useState('');
  const [mode, setMode] = useState('mock');
  const [maxTurns, setMaxTurns] = useState(30);

  const mutation = useMutation({
    mutationFn: () =>
      createThread(subredditName, {
        title: title.trim(),
        hypothesis: hypothesis.trim(),
        mode,
        max_turns: maxTurns,
      }),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.subreddits.threads(subredditName) });
      onClose();
      resetForm();
      navigate({ to: '/c/$name/thread/$threadId', params: { name: subredditName, threadId: data.id } });
    },
  });

  const resetForm = () => {
    setTitle('');
    setHypothesis('');
    setMode('mock');
    setMaxTurns(30);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim() || !hypothesis.trim()) return;
    mutation.mutate();
  };

  return (
    <Dialog open={open} onClose={onClose}>
      <form onSubmit={handleSubmit}>
        <DialogHeader>
          <DialogTitle>New Thread in c/{subredditName}</DialogTitle>
          <DialogDescription>Start a new multi-agent deliberation on a hypothesis.</DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-text-secondary mb-1">Title</label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Brief title for the deliberation"
              className="w-full bg-bg-tertiary text-text-primary text-sm rounded-md border border-border-default px-3 py-2 placeholder:text-text-muted focus:outline-none focus:ring-1 focus:ring-accent"
              required
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-text-secondary mb-1">Hypothesis</label>
            <textarea
              value={hypothesis}
              onChange={(e) => setHypothesis(e.target.value)}
              placeholder="The hypothesis or question for agents to deliberate..."
              rows={4}
              className="w-full bg-bg-tertiary text-text-primary text-sm rounded-md border border-border-default px-3 py-2 placeholder:text-text-muted focus:outline-none focus:ring-1 focus:ring-accent resize-none"
              required
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-medium text-text-secondary mb-1">Mode</label>
              <select
                value={mode}
                onChange={(e) => setMode(e.target.value)}
                className="w-full bg-bg-tertiary text-text-secondary text-sm rounded-md border border-border-default px-3 py-2 focus:outline-none focus:ring-1 focus:ring-accent"
              >
                <option value="mock">Mock (fast, no LLM)</option>
                <option value="live">Live (real LLM calls)</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-text-secondary mb-1">Max Turns</label>
              <input
                type="number"
                value={maxTurns}
                onChange={(e) => setMaxTurns(parseInt(e.target.value) || 30)}
                min={5}
                max={200}
                className="w-full bg-bg-tertiary text-text-primary text-sm rounded-md border border-border-default px-3 py-2 focus:outline-none focus:ring-1 focus:ring-accent"
              />
            </div>
          </div>

          {mutation.error && (
            <div className="text-xs text-red-400 bg-red-400/10 rounded p-2">
              {mutation.error instanceof Error ? mutation.error.message : 'Failed to create thread'}
            </div>
          )}
        </div>

        <DialogFooter>
          <Button type="button" variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" disabled={!title.trim() || !hypothesis.trim() || mutation.isPending}>
            {mutation.isPending ? 'Creating...' : 'Start Deliberation'}
          </Button>
        </DialogFooter>
      </form>
    </Dialog>
  );
}
