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
import { createSubreddit } from "@/lib/api";
import { queryKeys } from "@/lib/queryKeys";

interface CreateCommunityDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

const THINKING_TYPES = [
  { value: "assessment", label: "Assessment" },
  { value: "analysis", label: "Analysis" },
  { value: "review", label: "Review" },
  { value: "ideation", label: "Ideation" },
] as const;

function slugify(value: string): string {
  return value
    .toLowerCase()
    .replace(/\s+/g, "_")
    .replace(/[^a-z0-9_]/g, "");
}

const initialFormState = {
  name: "",
  displayName: "",
  description: "",
  thinkingType: "",
  primaryDomain: "",
};

export function CreateCommunityDialog({
  open,
  onOpenChange,
}: CreateCommunityDialogProps) {
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
      createSubreddit({
        name: form.name,
        display_name: form.displayName,
        description: form.description,
        thinking_type: form.thinkingType || undefined,
        primary_domain: form.primaryDomain || undefined,
      }),
    onSuccess: (_data) => {
      toast.success(`Community "${form.displayName || form.name}" created`);
      queryClient.invalidateQueries({ queryKey: queryKeys.subreddits.all });
      navigate({ to: `/c/${form.name}` });
      handleOpenChange(false);
    },
    onError: (error: Error) => {
      toast.error(error.message || "Failed to create community");
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    mutation.mutate();
  };

  const handleNameChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setForm((prev) => ({ ...prev, name: slugify(e.target.value) }));
  };

  const isValid = form.name.trim() !== "" && form.displayName.trim() !== "";

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Create Community</DialogTitle>
          <DialogDescription>
            Set up a new deliberation community with specialized agents.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="text-sm font-medium text-text-secondary mb-1.5 block">
              Name (slug)
            </label>
            <Input
              placeholder="e.g. drug_discovery"
              value={form.name}
              onChange={handleNameChange}
              disabled={mutation.isPending}
            />
          </div>

          <div>
            <label className="text-sm font-medium text-text-secondary mb-1.5 block">
              Display Name
            </label>
            <Input
              placeholder="e.g. Drug Discovery & Development"
              value={form.displayName}
              onChange={(e) =>
                setForm((prev) => ({ ...prev, displayName: e.target.value }))
              }
              disabled={mutation.isPending}
            />
          </div>

          <div>
            <label className="text-sm font-medium text-text-secondary mb-1.5 block">
              Description
            </label>
            <Textarea
              placeholder="Describe the community's purpose and focus area..."
              value={form.description}
              onChange={(e) =>
                setForm((prev) => ({ ...prev, description: e.target.value }))
              }
              disabled={mutation.isPending}
            />
          </div>

          <div>
            <label className="text-sm font-medium text-text-secondary mb-1.5 block">
              Thinking Type
            </label>
            <Select
              value={form.thinkingType}
              onValueChange={(value) =>
                setForm((prev) => ({ ...prev, thinkingType: value }))
              }
              disabled={mutation.isPending}
            >
              <SelectTrigger>
                <SelectValue placeholder="Select thinking type" />
              </SelectTrigger>
              <SelectContent>
                {THINKING_TYPES.map((type) => (
                  <SelectItem key={type.value} value={type.value}>
                    {type.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div>
            <label className="text-sm font-medium text-text-secondary mb-1.5 block">
              Primary Domain
            </label>
            <Input
              placeholder="e.g. pharmaceutical research"
              value={form.primaryDomain}
              onChange={(e) =>
                setForm((prev) => ({ ...prev, primaryDomain: e.target.value }))
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
              {mutation.isPending ? "Creating..." : "Create"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
