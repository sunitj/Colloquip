import { useState } from 'react';
import { Send } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
} from '@/components/ui/select';

interface InterventionBarProps {
  onIntervene: (content: string, type: string) => void;
  status: string;
}

const INTERVENTION_TYPES = [
  { value: 'question', label: 'Question' },
  { value: 'new_data', label: 'New Data' },
  { value: 'redirect', label: 'Redirect' },
  { value: 'terminate', label: 'Terminate' },
] as const;

export function InterventionBar({ onIntervene, status }: InterventionBarProps) {
  const [content, setContent] = useState('');
  const [type, setType] = useState('question');

  if (status !== 'running') return null;

  const handleSubmit = () => {
    if (!content.trim()) return;
    onIntervene(content.trim(), type);
    setContent('');
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="bg-bg-surface border-t border-border-default p-4">
      <div className="flex items-start gap-3">
        <Select value={type} onValueChange={setType}>
          <SelectTrigger className="w-[140px] shrink-0">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {INTERVENTION_TYPES.map((t) => (
              <SelectItem key={t.value} value={t.value}>
                {t.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Textarea
          value={content}
          onChange={(e) => setContent(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Intervene in the deliberation..."
          className="flex-1 min-h-[40px] max-h-[120px] resize-y"
          rows={1}
        />

        <Button
          onClick={handleSubmit}
          disabled={!content.trim()}
          size="default"
          className="shrink-0"
        >
          <Send className="h-4 w-4 mr-1" />
          Send
        </Button>
      </div>
    </div>
  );
}
