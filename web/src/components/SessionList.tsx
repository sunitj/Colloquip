import { useCallback, useEffect, useState } from 'react';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

interface SessionSummary {
  id: string;
  hypothesis: string;
  status: string;
  phase: string;
  created_at: string;
}

interface SessionListProps {
  onSelect: (sessionId: string) => void;
  onNew: () => void;
  currentSessionId: string | null;
}

export function SessionList({ onSelect, onNew, currentSessionId }: SessionListProps) {
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchSessions = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/api/deliberations?limit=50`);
      if (!res.ok) throw new Error('Failed to load sessions');
      const data = await res.json();
      setSessions(data.sessions || []);
    } catch (err) {
      setError(String(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchSessions();
  }, [fetchSessions]);

  const statusColor = (status: string) => {
    switch (status) {
      case 'completed': return '#22c55e';
      case 'running': return '#3b82f6';
      case 'paused': return '#f59e0b';
      default: return '#64748b';
    }
  };

  const timeAgo = (iso: string) => {
    const diff = Date.now() - new Date(iso).getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 1) return 'just now';
    if (mins < 60) return `${mins}m ago`;
    const hrs = Math.floor(mins / 60);
    if (hrs < 24) return `${hrs}h ago`;
    return `${Math.floor(hrs / 24)}d ago`;
  };

  return (
    <div className="session-list">
      <h2 className="panel-title">History</h2>

      <button className="session-new-btn" onClick={onNew}>
        + New Deliberation
      </button>

      {loading && <div className="session-loading">Loading...</div>}
      {error && <div className="session-error">{error}</div>}

      {!loading && sessions.length === 0 && (
        <div className="session-empty">No past sessions</div>
      )}

      {sessions.map(s => (
        <button
          key={s.id}
          className={`session-item ${s.id === currentSessionId ? 'active' : ''}`}
          style={{ borderLeftColor: statusColor(s.status) }}
          onClick={() => onSelect(s.id)}
        >
          <div className="session-hypothesis">
            {s.hypothesis.length > 60 ? s.hypothesis.slice(0, 60) + '...' : s.hypothesis}
          </div>
          <div className="session-meta">
            <span className="session-status" style={{ color: statusColor(s.status) }}>
              {s.status}
            </span>
            <span className="session-phase">{s.phase}</span>
            <span className="session-time">{timeAgo(s.created_at)}</span>
          </div>
        </button>
      ))}

      {sessions.length > 0 && (
        <button className="session-refresh-btn" onClick={fetchSessions}>
          Refresh
        </button>
      )}
    </div>
  );
}
