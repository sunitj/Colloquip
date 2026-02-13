import { useState } from 'react';
import { useNavigate } from '@tanstack/react-router';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { createSubreddit } from '@/lib/api';
import { queryKeys } from '@/lib/queryKeys';
import { Dialog, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/Dialog';
import { Button } from '@/components/ui/Button';

interface CreateCommunityDialogProps {
  open: boolean;
  onClose: () => void;
}

export function CreateCommunityDialog({ open, onClose }: CreateCommunityDialogProps) {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [name, setName] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [description, setDescription] = useState('');
  const [thinkingType, setThinkingType] = useState('assessment');
  const [primaryDomain, setPrimaryDomain] = useState('');

  const mutation = useMutation({
    mutationFn: () =>
      createSubreddit({
        name: name.trim().toLowerCase().replace(/\s+/g, '_'),
        display_name: displayName.trim() || name.trim(),
        description: description.trim(),
        thinking_type: thinkingType,
        primary_domain: primaryDomain.trim() || undefined,
      }),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.subreddits.all });
      onClose();
      resetForm();
      navigate({ to: '/c/$name', params: { name: data.name } });
    },
  });

  const resetForm = () => {
    setName('');
    setDisplayName('');
    setDescription('');
    setThinkingType('assessment');
    setPrimaryDomain('');
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim() || !description.trim()) return;
    mutation.mutate();
  };

  return (
    <Dialog open={open} onClose={onClose}>
      <form onSubmit={handleSubmit}>
        <DialogHeader>
          <DialogTitle>Create Community</DialogTitle>
          <DialogDescription>Set up a new deliberation community with specialized agents.</DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-text-secondary mb-1">Name (slug)</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. drug_discovery"
              className="w-full bg-bg-tertiary text-text-primary text-sm rounded-md border border-border-default px-3 py-2 placeholder:text-text-muted focus:outline-none focus:ring-1 focus:ring-accent"
              required
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-text-secondary mb-1">Display Name</label>
            <input
              type="text"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              placeholder="e.g. Drug Discovery"
              className="w-full bg-bg-tertiary text-text-primary text-sm rounded-md border border-border-default px-3 py-2 placeholder:text-text-muted focus:outline-none focus:ring-1 focus:ring-accent"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-text-secondary mb-1">Description</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="What will this community deliberate about?"
              rows={3}
              className="w-full bg-bg-tertiary text-text-primary text-sm rounded-md border border-border-default px-3 py-2 placeholder:text-text-muted focus:outline-none focus:ring-1 focus:ring-accent resize-none"
              required
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-medium text-text-secondary mb-1">Thinking Type</label>
              <select
                value={thinkingType}
                onChange={(e) => setThinkingType(e.target.value)}
                className="w-full bg-bg-tertiary text-text-secondary text-sm rounded-md border border-border-default px-3 py-2 focus:outline-none focus:ring-1 focus:ring-accent"
              >
                <option value="assessment">Assessment</option>
                <option value="analysis">Analysis</option>
                <option value="review">Review</option>
                <option value="ideation">Ideation</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-text-secondary mb-1">Primary Domain</label>
              <input
                type="text"
                value={primaryDomain}
                onChange={(e) => setPrimaryDomain(e.target.value)}
                placeholder="e.g. pharmacology"
                className="w-full bg-bg-tertiary text-text-primary text-sm rounded-md border border-border-default px-3 py-2 placeholder:text-text-muted focus:outline-none focus:ring-1 focus:ring-accent"
              />
            </div>
          </div>

          {mutation.error && (
            <div className="text-xs text-red-400 bg-red-400/10 rounded p-2">
              {mutation.error instanceof Error ? mutation.error.message : 'Failed to create community'}
            </div>
          )}
        </div>

        <DialogFooter>
          <Button type="button" variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" disabled={!name.trim() || !description.trim() || mutation.isPending}>
            {mutation.isPending ? 'Creating...' : 'Create Community'}
          </Button>
        </DialogFooter>
      </form>
    </Dialog>
  );
}
