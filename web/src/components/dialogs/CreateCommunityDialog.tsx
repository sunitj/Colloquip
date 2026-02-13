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

        <div className="space-y-6">
          <div>
            <label className="block text-xs font-semibold text-text-primary mb-2">Name (slug)</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. drug_discovery"
              className="w-full bg-white text-text-primary text-sm rounded-xl border border-border-default px-3 py-2 h-11 placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-accent/20 focus:border-accent focus:bg-bg-secondary transition-all duration-200"
              required
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-text-primary mb-2">Display Name</label>
            <input
              type="text"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              placeholder="e.g. Drug Discovery"
              className="w-full bg-white text-text-primary text-sm rounded-xl border border-border-default px-3 py-2 h-11 placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-accent/20 focus:border-accent focus:bg-bg-secondary transition-all duration-200"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-text-primary mb-2">Description</label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="What will this community deliberate about?"
              rows={3}
              className="w-full bg-white text-text-primary text-sm rounded-xl border border-border-default px-3 py-2 placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-accent/20 focus:border-accent focus:bg-bg-secondary resize-none transition-all duration-200"
              required
            />
          </div>

          <div className="grid grid-cols-2 gap-6">
            <div>
              <label className="block text-xs font-semibold text-text-primary mb-2">Thinking Type</label>
              <select
                value={thinkingType}
                onChange={(e) => setThinkingType(e.target.value)}
                className="w-full bg-white text-text-secondary text-sm rounded-xl border border-border-default px-3 py-2 h-11 focus:outline-none focus:ring-2 focus:ring-accent/20 focus:border-accent focus:bg-bg-secondary transition-all duration-200"
              >
                <option value="assessment">Assessment</option>
                <option value="analysis">Analysis</option>
                <option value="review">Review</option>
                <option value="ideation">Ideation</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-semibold text-text-primary mb-2">Primary Domain</label>
              <input
                type="text"
                value={primaryDomain}
                onChange={(e) => setPrimaryDomain(e.target.value)}
                placeholder="e.g. pharmacology"
                className="w-full bg-white text-text-primary text-sm rounded-xl border border-border-default px-3 py-2 h-11 placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-accent/20 focus:border-accent focus:bg-bg-secondary transition-all duration-200"
              />
            </div>
          </div>

          {mutation.error && (
            <div className="text-xs text-[#C95A6B] bg-pastel-rose-bg border border-pastel-rose/30 rounded-xl p-2">
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
