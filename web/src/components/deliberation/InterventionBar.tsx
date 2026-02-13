import { useState } from 'react';
import { cn } from '@/lib/utils';

interface InterventionBarProps {
  onIntervene: (content: string, type?: string) => void;
  status: string;
}

export function InterventionBar({ onIntervene, status }: InterventionBarProps) {
  const [content, setContent] = useState('');
  const [type, setType] = useState('question');

  if (status !== 'running') return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!content.trim()) return;
    onIntervene(content.trim(), type);
    setContent('');
  };

  return (
    <form
      className="flex items-center gap-2 p-3 bg-bg-elevated rounded-lg border border-border-default"
      onSubmit={handleSubmit}
    >
      <select
        value={type}
        onChange={(e) => setType(e.target.value)}
        className="bg-bg-tertiary text-text-secondary text-xs rounded-md border border-border-default px-2 py-1.5 focus:outline-none focus:ring-1 focus:ring-accent"
      >
        <option value="question">Question</option>
        <option value="data">New Data</option>
        <option value="redirect">Redirect</option>
        <option value="terminate">Terminate</option>
      </select>
      <input
        type="text"
        value={content}
        onChange={(e) => setContent(e.target.value)}
        placeholder="Inject human input into the deliberation..."
        className="flex-1 bg-bg-tertiary text-text-primary text-sm rounded-md border border-border-default px-3 py-1.5 placeholder:text-text-muted focus:outline-none focus:ring-1 focus:ring-accent"
        maxLength={5000}
      />
      <button
        type="submit"
        disabled={!content.trim()}
        className={cn(
          'px-4 py-1.5 rounded-md text-sm font-medium transition-colors',
          content.trim()
            ? 'bg-accent text-white hover:bg-accent/90'
            : 'bg-bg-tertiary text-text-muted cursor-not-allowed',
        )}
      >
        Intervene
      </button>
    </form>
  );
}
