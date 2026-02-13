import { useState, useCallback } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
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
import { createWatcher } from "@/lib/api";
import { queryKeys } from "@/lib/queryKeys";

interface CreateWatcherDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  communityName: string;
}

const WATCHER_TYPES = [
  { value: "literature", label: "Literature" },
  { value: "scheduled", label: "Scheduled" },
  { value: "webhook", label: "Webhook" },
] as const;

const POLL_INTERVALS = [
  { value: "5", label: "5 min" },
  { value: "15", label: "15 min" },
  { value: "30", label: "30 min" },
  { value: "60", label: "1 hr" },
  { value: "360", label: "6 hr" },
  { value: "720", label: "12 hr" },
  { value: "1440", label: "24 hr" },
] as const;

const initialFormState = {
  watcherType: "",
  name: "",
  description: "",
  query: "",
  pollInterval: "60",
};

export function CreateWatcherDialog({
  open,
  onOpenChange,
  communityName,
}: CreateWatcherDialogProps) {
  const [form, setForm] = useState(initialFormState);
  const queryClient = useQueryClient();

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
      createWatcher(communityName, {
        watcher_type: form.watcherType,
        name: form.name,
        description: form.description,
        query: form.query,
        poll_interval_seconds: Number(form.pollInterval) * 60,
      }),
    onSuccess: () => {
      toast.success(`Watcher "${form.name}" created`);
      queryClient.invalidateQueries({
        queryKey: queryKeys.subreddits.watchers(communityName),
      });
      handleOpenChange(false);
    },
    onError: (error: Error) => {
      toast.error(error.message || "Failed to create watcher");
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    mutation.mutate();
  };

  const isValid =
    form.watcherType.trim() !== "" &&
    form.name.trim() !== "" &&
    form.query.trim() !== "";

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Create Watcher</DialogTitle>
          <DialogDescription>
            Set up an automated watcher to monitor for new information.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="text-sm font-medium text-text-secondary mb-1.5 block">
              Type
            </label>
            <Select
              value={form.watcherType}
              onValueChange={(value) =>
                setForm((prev) => ({ ...prev, watcherType: value }))
              }
              disabled={mutation.isPending}
            >
              <SelectTrigger>
                <SelectValue placeholder="Select watcher type" />
              </SelectTrigger>
              <SelectContent>
                {WATCHER_TYPES.map((type) => (
                  <SelectItem key={type.value} value={type.value}>
                    {type.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div>
            <label className="text-sm font-medium text-text-secondary mb-1.5 block">
              Name
            </label>
            <Input
              placeholder="Watcher name"
              value={form.name}
              onChange={(e) =>
                setForm((prev) => ({ ...prev, name: e.target.value }))
              }
              disabled={mutation.isPending}
            />
          </div>

          <div>
            <label className="text-sm font-medium text-text-secondary mb-1.5 block">
              Description
            </label>
            <Textarea
              placeholder="Describe what this watcher monitors..."
              value={form.description}
              onChange={(e) =>
                setForm((prev) => ({ ...prev, description: e.target.value }))
              }
              disabled={mutation.isPending}
            />
          </div>

          <div>
            <label className="text-sm font-medium text-text-secondary mb-1.5 block">
              Query
            </label>
            <Input
              placeholder="Search query or webhook URL"
              value={form.query}
              onChange={(e) =>
                setForm((prev) => ({ ...prev, query: e.target.value }))
              }
              disabled={mutation.isPending}
            />
          </div>

          <div>
            <label className="text-sm font-medium text-text-secondary mb-1.5 block">
              Poll Interval
            </label>
            <Select
              value={form.pollInterval}
              onValueChange={(value) =>
                setForm((prev) => ({ ...prev, pollInterval: value }))
              }
              disabled={mutation.isPending}
            >
              <SelectTrigger>
                <SelectValue placeholder="Select interval" />
              </SelectTrigger>
              <SelectContent>
                {POLL_INTERVALS.map((interval) => (
                  <SelectItem key={interval.value} value={interval.value}>
                    {interval.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
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
              {mutation.isPending ? "Creating..." : "Create Watcher"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
