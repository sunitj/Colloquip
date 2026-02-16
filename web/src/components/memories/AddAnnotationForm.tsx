import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Send } from 'lucide-react';
import { annotateMemory } from '@/lib/api';
import { queryKeys } from '@/lib/queryKeys';
import type { AnnotationType } from '@/types/platform';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
} from '@/components/ui/select';

interface AddAnnotationFormProps {
  memoryId: string;
  onSuccess: () => void;
}

const ANNOTATION_TYPES: { value: AnnotationType; label: string }[] = [
  { value: 'confirmed', label: 'Confirmed' },
  { value: 'correction', label: 'Correction' },
  { value: 'outdated', label: 'Outdated' },
  { value: 'context', label: 'Context' },
];

export function AddAnnotationForm({ memoryId, onSuccess }: AddAnnotationFormProps) {
  const queryClient = useQueryClient();
  const [annotationType, setAnnotationType] = useState<AnnotationType>('confirmed');
  const [content, setContent] = useState('');
  const [createdBy, setCreatedBy] = useState('');

  const mutation = useMutation({
    mutationFn: () =>
      annotateMemory(memoryId, {
        annotation_type: annotationType,
        content,
        created_by: createdBy,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.memories.detail(memoryId) });
      queryClient.invalidateQueries({ queryKey: queryKeys.memories.all() });
      setContent('');
      setCreatedBy('');
      setAnnotationType('confirmed');
      onSuccess();
    },
  });

  const canSubmit = content.trim().length > 0 && createdBy.trim().length > 0;

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        if (canSubmit) mutation.mutate();
      }}
      className="space-y-4"
    >
      <div>
        <label className="mb-1.5 block text-sm font-medium text-text-secondary">
          Annotation Type
        </label>
        <Select
          value={annotationType}
          onValueChange={(v) => setAnnotationType(v as AnnotationType)}
        >
          <SelectTrigger className="w-full">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {ANNOTATION_TYPES.map((type) => (
              <SelectItem key={type.value} value={type.value}>
                {type.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div>
        <label className="mb-1.5 block text-sm font-medium text-text-secondary">
          Content
        </label>
        <Textarea
          value={content}
          onChange={(e) => setContent(e.target.value)}
          placeholder="Describe the annotation..."
          rows={3}
        />
      </div>

      <div>
        <label className="mb-1.5 block text-sm font-medium text-text-secondary">
          Your Name
        </label>
        <Input
          value={createdBy}
          onChange={(e) => setCreatedBy(e.target.value)}
          placeholder="Who is adding this annotation?"
        />
      </div>

      <Button
        type="submit"
        disabled={!canSubmit || mutation.isPending}
        className="w-full"
      >
        <Send className="h-4 w-4" />
        {mutation.isPending ? 'Submitting...' : 'Add Annotation'}
      </Button>

      {mutation.isError && (
        <p className="text-sm text-destructive">
          Failed to add annotation. Please try again.
        </p>
      )}
    </form>
  );
}
