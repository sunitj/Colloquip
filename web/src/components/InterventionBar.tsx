import { useState } from 'react';

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
    <form className="intervention-bar" onSubmit={handleSubmit}>
      <select
        value={type}
        onChange={e => setType(e.target.value)}
        className="intervention-type-select"
      >
        <option value="question">Question</option>
        <option value="data">New Data</option>
        <option value="redirect">Redirect</option>
        <option value="terminate">Terminate</option>
      </select>
      <input
        type="text"
        value={content}
        onChange={e => setContent(e.target.value)}
        placeholder="Inject human input into the deliberation..."
        className="intervention-input"
        maxLength={5000}
      />
      <button type="submit" className="intervention-submit" disabled={!content.trim()}>
        Intervene
      </button>
    </form>
  );
}
