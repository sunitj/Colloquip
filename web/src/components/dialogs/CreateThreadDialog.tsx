import { useState, useCallback } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "@tanstack/react-router";
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
import { createThread } from "@/lib/api";
import { queryKeys } from "@/lib/queryKeys";

interface CreateThreadDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  communityName: string;
}

const MODES = [
  { value: "mock", label: "Mock" },
  { value: "live", label: "Live" },
] as const;

const initialFormState = {
  title: "",
  hypothesis: "",
  mode: "mock",
  maxTurns: "30",
};

export function CreateThreadDialog({
  open,
  onOpenChange,
  communityName,
}: CreateThreadDialogProps) {
  const [form, setForm] = useState(initialFormState);
  const queryClient = useQueryClient();
  const navigate = useNavigate();

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
      createThread(communityName, {
        title: form.title,
        hypothesis: form.hypothesis,
        mode: form.mode || undefined,
        max_turns: form.maxTurns ? Number(form.maxTurns) : undefined,
      }),
    onSuccess: (result) => {
      toast.success(`Deliberation "${form.title}" started`);
      queryClient.invalidateQueries({
        queryKey: queryKeys.subreddits.threads(communityName),
      });
      navigate({ to: `/c/${communityName}/thread/${result.id}` });
      handleOpenChange(false);
    },
    onError: (error: Error) => {
      toast.error(error.message || "Failed to create thread");
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    mutation.mutate();
  };

  const isValid =
    form.title.trim() !== "" && form.hypothesis.trim() !== "";

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="max-w-xl">
        <DialogHeader>
          <DialogTitle>Start Deliberation</DialogTitle>
          <DialogDescription>
            Create a new deliberation thread in this community.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="text-sm font-medium text-text-secondary mb-1.5 block">
              Title
            </label>
            <Input
              placeholder="Deliberation title"
              value={form.title}
              onChange={(e) =>
                setForm((prev) => ({ ...prev, title: e.target.value }))
              }
              disabled={mutation.isPending}
            />
          </div>

          <div>
            <label className="text-sm font-medium text-text-secondary mb-1.5 block">
              Hypothesis
            </label>
            <Textarea
              className="min-h-[120px]"
              placeholder="Enter the hypothesis to deliberate..."
              value={form.hypothesis}
              onChange={(e) =>
                setForm((prev) => ({ ...prev, hypothesis: e.target.value }))
              }
              disabled={mutation.isPending}
            />
          </div>

          <div>
            <label className="text-sm font-medium text-text-secondary mb-1.5 block">
              Mode
            </label>
            <Select
              value={form.mode}
              onValueChange={(value) =>
                setForm((prev) => ({ ...prev, mode: value }))
              }
              disabled={mutation.isPending}
            >
              <SelectTrigger>
                <SelectValue placeholder="Select mode" />
              </SelectTrigger>
              <SelectContent>
                {MODES.map((mode) => (
                  <SelectItem key={mode.value} value={mode.value}>
                    {mode.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div>
            <label className="text-sm font-medium text-text-secondary mb-1.5 block">
              Max Turns
            </label>
            <Input
              type="number"
              min={1}
              max={200}
              placeholder="30"
              value={form.maxTurns}
              onChange={(e) =>
                setForm((prev) => ({ ...prev, maxTurns: e.target.value }))
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
              {mutation.isPending ? "Creating..." : "Start Deliberation"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
