import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { reportOutcome } from '@/lib/api';
import { Dialog, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/Dialog';
import { Button } from '@/components/ui/Button';

interface ReportOutcomeDialogProps {
  open: boolean;
  onClose: () => void;
  threadId: string;
}

const OUTCOME_OPTIONS = [
  { value: 'confirmed', label: 'Confirmed' },
  { value: 'partially_confirmed', label: 'Partially Confirmed' },
  { value: 'refuted', label: 'Refuted' },
  { value: 'inconclusive', label: 'Inconclusive' },
] as const;

export function ReportOutcomeDialog({ open, onClose, threadId }: ReportOutcomeDialogProps) {
  const [outcomeType, setOutcomeType] = useState('confirmed');
  const [summary, setSummary] = useState('');
  const [evidence, setEvidence] = useState('');
  const [reportedBy, setReportedBy] = useState('human');

  const mutation = useMutation({
    mutationFn: () =>
      reportOutcome(threadId, {
        outcome_type: outcomeType,
        summary: summary.trim(),
        evidence: evidence.trim(),
        conclusions_evaluated: {},
        agent_assessments: {},
        reported_by: reportedBy.trim() || 'human',
      }),
    onSuccess: () => {
      onClose();
      resetForm();
    },
  });

  const resetForm = () => {
    setOutcomeType('confirmed');
    setSummary('');
    setEvidence('');
    setReportedBy('human');
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!summary.trim()) return;
    mutation.mutate();
  };

  return (
    <Dialog open={open} onClose={onClose}>
      <form onSubmit={handleSubmit}>
        <DialogHeader>
          <DialogTitle>Report Outcome</DialogTitle>
          <DialogDescription>
            Record the real-world outcome for this thread to calibrate agent accuracy.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-text-secondary mb-1">
              Outcome Type
            </label>
            <select
              value={outcomeType}
              onChange={(e) => setOutcomeType(e.target.value)}
              className="w-full bg-bg-tertiary text-text-primary text-sm rounded-md border border-border-default px-3 py-2 placeholder:text-text-muted focus:outline-none focus:ring-1 focus:ring-accent"
            >
              {OUTCOME_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-xs font-medium text-text-secondary mb-1">
              Summary
            </label>
            <textarea
              value={summary}
              onChange={(e) => setSummary(e.target.value)}
              placeholder="Summarize the real-world outcome..."
              rows={3}
              className="w-full bg-bg-tertiary text-text-primary text-sm rounded-md border border-border-default px-3 py-2 placeholder:text-text-muted focus:outline-none focus:ring-1 focus:ring-accent resize-none"
              required
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-text-secondary mb-1">
              Evidence
            </label>
            <textarea
              value={evidence}
              onChange={(e) => setEvidence(e.target.value)}
              placeholder="Describe the supporting evidence (links, references, observations)..."
              rows={3}
              className="w-full bg-bg-tertiary text-text-primary text-sm rounded-md border border-border-default px-3 py-2 placeholder:text-text-muted focus:outline-none focus:ring-1 focus:ring-accent resize-none"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-text-secondary mb-1">
              Reported By
            </label>
            <input
              type="text"
              value={reportedBy}
              onChange={(e) => setReportedBy(e.target.value)}
              placeholder="human"
              className="w-full bg-bg-tertiary text-text-primary text-sm rounded-md border border-border-default px-3 py-2 placeholder:text-text-muted focus:outline-none focus:ring-1 focus:ring-accent"
            />
          </div>

          {mutation.error && (
            <div className="text-xs text-red-400 bg-red-400/10 rounded p-2">
              {mutation.error instanceof Error ? mutation.error.message : 'Failed to report outcome'}
            </div>
          )}
        </div>

        <DialogFooter>
          <Button type="button" variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" disabled={!summary.trim() || mutation.isPending}>
            {mutation.isPending ? 'Submitting...' : 'Report Outcome'}
          </Button>
        </DialogFooter>
      </form>
    </Dialog>
  );
}
