import { useState } from 'react';

interface ControlBarProps {
  onStart: (hypothesis: string, mode: string, maxTurns: number) => void;
  status: string;
  hypothesis: string;
}

export function ControlBar({ onStart, status, hypothesis }: ControlBarProps) {
  const [input, setInput] = useState(
    hypothesis || 'GLP-1 agonists may improve cognitive function in Alzheimer\'s patients'
  );
  const [mode, setMode] = useState('mock');
  const [maxTurns, setMaxTurns] = useState(15);

  const isRunning = status === 'running';
  const isCompleted = status === 'completed';

  return (
    <div className="control-bar">
      <div className="control-bar-brand">
        <h1>COLLOQUIP</h1>
        <span className="subtitle">Emergent Multi-Agent Deliberation</span>
      </div>
      <div className="control-bar-inputs">
        <input
          className="hypothesis-input"
          type="text"
          placeholder="Enter hypothesis to evaluate..."
          value={input}
          onChange={e => setInput(e.target.value)}
          disabled={isRunning}
        />
        <select
          className="mode-select"
          value={mode}
          onChange={e => setMode(e.target.value)}
          disabled={isRunning}
        >
          <option value="mock">Mock LLM</option>
          <option value="real">Claude API</option>
        </select>
        <input
          className="turns-input"
          type="number"
          min={3}
          max={50}
          value={maxTurns}
          onChange={e => setMaxTurns(Number(e.target.value))}
          disabled={isRunning}
          title="Max turns"
        />
        <button
          className={`start-btn ${isRunning ? 'running' : ''} ${isCompleted ? 'completed' : ''}`}
          onClick={() => onStart(input, mode, maxTurns)}
          disabled={isRunning || !input.trim()}
        >
          {isRunning ? '● Running...' : isCompleted ? '↻ Restart' : '▶ Start'}
        </button>
      </div>
    </div>
  );
}
