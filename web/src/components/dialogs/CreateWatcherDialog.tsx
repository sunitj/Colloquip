import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { createWatcher } from '@/lib/api';
import { queryKeys } from '@/lib/queryKeys';
import { Dialog, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/Dialog';
import { Button } from '@/components/ui/Button';

interface CreateWatcherDialogProps {
  open: boolean;
  onClose: () => void;
  subredditName: string;
}

export function CreateWatcherDialog({ open, onClose, subredditName }: CreateWatcherDialogProps) {
  const queryClient = useQueryClient();

  const [watcherType, setWatcherType] = useState('literature');
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [query, setQuery] = useState('');
  const [pollInterval, setPollInterval] = useState(3600);

  const mutation = useMutation({
    mutationFn: () =>
      createWatcher(subredditName, {
        watcher_type: watcherType,
        name: name.trim(),
        description: description.trim(),
        query: query.trim(),
        poll_interval_seconds: pollInterval,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.subreddits.watchers(subredditName) });
      onClose();
      resetForm();
    },
  });

  const resetForm = () => {
    setWatcherType('literature');
    setName('');
    setDescription('');
    setQuery('');
    setPollInterval(3600);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim() || !query.trim()) return;
    mutation.mutate();
  };

  return (
    <Dialog open={open} onClose={onClose}>
      <form onSubmit={handleSubmit}>
        <DialogHeader>
          <DialogTitle>Add Watcher to c/{subredditName}</DialogTitle>
          <DialogDescription>Set up automated monitoring to detect events that may need deliberation.</DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-text-secondary mb-1">Type</label>
            <select
              value={watcherType}
              onChange={(e) => setWatcherType(e.target.value)}
              className="w-full bg-bg-tertiary text-text-secondary text-sm rounded-md border border-border-default px-3 py-2 focus:outline-none focus:ring-1 focus:ring-accent"
            >
              <option value="literature">Literature</option>
              <option value="scheduled">Scheduled</option>
              <option value="webhook">Webhook</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-medium text-text-secondary mb-1">Name</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. PubMed SGLT2 monitor"
              className="w-full bg-bg-tertiary text-text-primary text-sm rounded-md border border-border-default px-3 py-2 placeholder:text-text-muted focus:outline-none focus:ring-1 focus:ring-accent"
              required
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-text-secondary mb-1">Description</label>
            <input
              type="text"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="What does this watcher monitor?"
              className="w-full bg-bg-tertiary text-text-primary text-sm rounded-md border border-border-default px-3 py-2 placeholder:text-text-muted focus:outline-none focus:ring-1 focus:ring-accent"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-text-secondary mb-1">Query</label>
            <textarea
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search query or monitoring expression..."
              rows={2}
              className="w-full bg-bg-tertiary text-text-primary text-sm rounded-md border border-border-default px-3 py-2 placeholder:text-text-muted focus:outline-none focus:ring-1 focus:ring-accent resize-none"
              required
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-text-secondary mb-1">
              Poll Interval ({Math.round(pollInterval / 60)} min)
            </label>
            <input
              type="range"
              value={pollInterval}
              onChange={(e) => setPollInterval(parseInt(e.target.value))}
              min={300}
              max={86400}
              step={300}
              className="w-full accent-accent"
            />
            <div className="flex justify-between text-[10px] text-text-muted mt-0.5">
              <span>5 min</span>
              <span>24 hr</span>
            </div>
          </div>

          {mutation.error && (
            <div className="text-xs text-red-400 bg-red-400/10 rounded p-2">
              {mutation.error instanceof Error ? mutation.error.message : 'Failed to create watcher'}
            </div>
          )}
        </div>

        <DialogFooter>
          <Button type="button" variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" disabled={!name.trim() || !query.trim() || mutation.isPending}>
            {mutation.isPending ? 'Creating...' : 'Create Watcher'}
          </Button>
        </DialogFooter>
      </form>
    </Dialog>
  );
}
