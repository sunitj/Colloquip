import { useState, useCallback } from "react";
import { useMutation } from "@tanstack/react-query";
import { toast } from "sonner";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
} from "@/components/ui/select";
import { reportOutcome } from "@/lib/api";

interface ReportOutcomeDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  threadId: string;
}

const OUTCOME_TYPES = [
  { value: "confirmed", label: "Confirmed" },
  { value: "partially_confirmed", label: "Partially Confirmed" },
  { value: "refuted", label: "Refuted" },
  { value: "inconclusive", label: "Inconclusive" },
] as const;

const initialFormState = {
  outcomeType: "",
  summary: "",
  evidence: "",
  reporterName: "",
};

export function ReportOutcomeDialog({
  open,
  onOpenChange,
  threadId,
}: ReportOutcomeDialogProps) {
  const [form, setForm] = useState(initialFormState);

  const resetForm = useCallback(() => {
    setForm(initialFormState);
  }, []);

  const handleOpenChange = useCallback(
    (nextOpen: boolean) => {
      if (!nextOpen) {
        resetForm();
      }
      onOpenChange(nextOpen);
    },
    [onOpenChange, resetForm]
  );

  const mutation = useMutation({
    mutationFn: () =>
      reportOutcome(threadId, {
        outcome_type: form.outcomeType,
        summary: form.summary,
        evidence: form.evidence,
        conclusions_evaluated: {},
        agent_assessments: {},
        reported_by: form.reporterName,
      }),
    onSuccess: () => {
      toast.success("Outcome report submitted");
      handleOpenChange(false);
    },
    onError: (error: Error) => {
      toast.error(error.message || "Failed to submit outcome report");
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    mutation.mutate();
  };

  const isValid =
    form.outcomeType.trim() !== "" &&
    form.summary.trim() !== "" &&
    form.reporterName.trim() !== "";

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Report Outcome</DialogTitle>
          <DialogDescription>
            Submit a real-world outcome report to calibrate agent accuracy.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="text-sm font-medium text-text-secondary mb-1.5 block">
              Outcome Type
            </label>
            <Select
              value={form.outcomeType}
              onValueChange={(value) =>
                setForm((prev) => ({ ...prev, outcomeType: value }))
              }
              disabled={mutation.isPending}
            >
              <SelectTrigger>
                <SelectValue placeholder="Select outcome type" />
              </SelectTrigger>
              <SelectContent>
                {OUTCOME_TYPES.map((type) => (
                  <SelectItem key={type.value} value={type.value}>
                    {type.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div>
            <label className="text-sm font-medium text-text-secondary mb-1.5 block">
              Summary
            </label>
            <Textarea
              placeholder="Summarize the real-world outcome..."
              value={form.summary}
              onChange={(e) =>
                setForm((prev) => ({ ...prev, summary: e.target.value }))
              }
              disabled={mutation.isPending}
            />
          </div>

          <div>
            <label className="text-sm font-medium text-text-secondary mb-1.5 block">
              Evidence{" "}
              <span className="text-text-muted font-normal">(optional)</span>
            </label>
            <Textarea
              placeholder="Provide supporting evidence, links, or references..."
              value={form.evidence}
              onChange={(e) =>
                setForm((prev) => ({ ...prev, evidence: e.target.value }))
              }
              disabled={mutation.isPending}
            />
          </div>

          <div>
            <label className="text-sm font-medium text-text-secondary mb-1.5 block">
              Reporter Name
            </label>
            <Input
              placeholder="Your name"
              value={form.reporterName}
              onChange={(e) =>
                setForm((prev) => ({ ...prev, reporterName: e.target.value }))
              }
              disabled={mutation.isPending}
            />
          </div>

          <DialogFooter>
            <Button
              type="button"
              variant="ghost"
              onClick={() => handleOpenChange(false)}
              disabled={mutation.isPending}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              disabled={!isValid || mutation.isPending}
            >
              {mutation.isPending ? "Submitting..." : "Submit Report"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
