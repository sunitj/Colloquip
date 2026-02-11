import { useCallback, useEffect, useRef, useState } from 'react';
import type {
  ConsensusMap,
  DeliberationState,
  EnergyUpdate,
  Phase,
  PhaseSignal,
  Post,
  SessionStatus,
  TriggerEntry,
  WSEvent,
} from '../types/deliberation';
import { AGENT_META } from '../components/agentMeta';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const WS_BASE = API_BASE.replace(/^http/, 'ws');

/** Shape returned by GET /api/deliberations/{id}/history */
interface HistoryResponse {
  session: { id: string; hypothesis: string; status: string; phase: string };
  posts: Post[];
  energy_history: EnergyUpdate[];
  consensus: ConsensusMap | null;
}

const initialState: DeliberationState = {
  sessionId: null,
  hypothesis: '',
  status: 'pending',
  phase: 'explore',
  posts: [],
  energyHistory: [],
  phaseHistory: [],
  triggers: [],
  consensus: null,
  connected: false,
  error: null,
  thinking: false,
};

export function useDeliberation() {
  const [state, setState] = useState<DeliberationState>(initialState);
  const wsRef = useRef<WebSocket | null>(null);
  const seqRef = useRef(0);

  const handleEvent = useCallback((evt: WSEvent) => {
    seqRef.current = Math.max(seqRef.current, evt.seq);

    switch (evt.type) {
      case 'session_state':
        setState(s => ({
          ...s,
          sessionId: evt.data.id,
          hypothesis: evt.data.hypothesis,
          status: evt.data.status as SessionStatus,
          phase: evt.data.phase as Phase,
        }));
        break;

      case 'post': {
        const post = evt.data as Post;
        const trigger: TriggerEntry = {
          timestamp: post.created_at,
          agentId: post.agent_id,
          agentName: AGENT_META[post.agent_id]?.name ?? post.agent_id,
          rules: post.triggered_by,
          postIndex: -1, // set below
        };
        setState(s => {
          const newPosts = [...s.posts, post];
          trigger.postIndex = newPosts.length - 1;
          return {
            ...s,
            thinking: false,
            posts: newPosts,
            triggers: [...s.triggers, trigger],
          };
        });
        break;
      }

      case 'phase_change':
        setState(s => ({
          ...s,
          phase: (evt.data as PhaseSignal).current_phase,
          phaseHistory: [...s.phaseHistory, evt.data as PhaseSignal],
        }));
        break;

      case 'energy_update':
        setState(s => ({
          ...s,
          thinking: true,
          energyHistory: [...s.energyHistory, evt.data as EnergyUpdate],
        }));
        break;

      case 'session_complete':
        setState(s => ({
          ...s,
          status: 'completed',
          thinking: false,
          consensus: evt.data as ConsensusMap,
        }));
        break;

      case 'done':
        setState(s => ({ ...s, status: 'completed', thinking: false }));
        break;

      case 'error':
        setState(s => ({ ...s, thinking: false, error: (evt.data as { message: string }).message }));
        break;

      case 'timeout':
        setState(s => ({ ...s, error: 'Connection timed out — no events for 120 seconds', connected: false }));
        break;

      case 'ack':
        break;

      default:
        break;
    }
  }, []);

  const connect = useCallback((sessionId: string) => {
    if (wsRef.current) {
      wsRef.current.close();
    }

    const ws = new WebSocket(`${WS_BASE}/ws/deliberations/${sessionId}`);
    wsRef.current = ws;

    ws.onopen = () => {
      setState(s => ({ ...s, connected: true, error: null }));
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data) as WSEvent;
        handleEvent(data);
      } catch (err) {
        console.error('Failed to parse WebSocket message:', err);
      }
    };

    ws.onclose = () => {
      setState(s => ({ ...s, connected: false }));
    };

    ws.onerror = () => {
      setState(s => ({ ...s, error: 'WebSocket connection failed' }));
    };
  }, [handleEvent]);

  const createAndStart = useCallback(async (
    hypothesis: string,
    mode: string = 'mock',
    maxTurns: number = 30,
  ) => {
    setState({ ...initialState, hypothesis });

    try {
      // Create session
      const res = await fetch(`${API_BASE}/api/deliberations`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ hypothesis, mode, max_turns: maxTurns }),
      });

      if (!res.ok) throw new Error('Failed to create session');
      const session = await res.json();
      const sessionId = session.id;

      setState(s => ({ ...s, sessionId, status: 'pending' }));

      // Connect WebSocket
      connect(sessionId);

      // Wait for WebSocket to open, then send start
      const ws = wsRef.current!;
      const waitForOpen = new Promise<void>((resolve, reject) => {
        if (ws.readyState === WebSocket.OPEN) {
          resolve();
          return;
        }
        const timer = setTimeout(() => reject(new Error('WebSocket timeout')), 5000);
        ws.addEventListener('open', () => {
          clearTimeout(timer);
          resolve();
        }, { once: true });
        ws.addEventListener('error', () => {
          clearTimeout(timer);
          reject(new Error('WebSocket connection failed'));
        }, { once: true });
      });

      await waitForOpen;
      ws.send(JSON.stringify({ type: 'start' }));
      setState(s => ({ ...s, status: 'running', thinking: true }));

    } catch (err) {
      setState(s => ({ ...s, error: String(err) }));
    }
  }, [connect]);

  const loadSession = useCallback(async (sessionId: string) => {
    // Close any existing WebSocket — historical view is read-only
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    setState({ ...initialState });

    try {
      const res = await fetch(`${API_BASE}/api/deliberations/${sessionId}/history`);
      if (!res.ok) throw new Error('Failed to load session history');
      const data: HistoryResponse = await res.json();

      // Reconstruct triggers from posts
      const triggers: TriggerEntry[] = data.posts.map((post, i) => ({
        timestamp: post.created_at,
        agentId: post.agent_id,
        agentName: AGENT_META[post.agent_id]?.name ?? post.agent_id,
        rules: post.triggered_by,
        postIndex: i,
      }));

      // Reconstruct phase history by detecting phase changes across posts
      const phaseHistory: PhaseSignal[] = [];
      let prevPhase: Phase | null = null;
      for (const post of data.posts) {
        if (post.phase !== prevPhase) {
          phaseHistory.push({
            current_phase: post.phase,
            confidence: 1.0,
            metrics: {
              question_rate: 0, disagreement_rate: 0, topic_diversity: 0,
              citation_density: 0, novelty_avg: 0, energy: 0, posts_since_novel: 0,
            },
            observation: null,
          });
          prevPhase = post.phase;
        }
      }

      setState({
        sessionId: data.session.id,
        hypothesis: data.session.hypothesis,
        status: data.session.status as SessionStatus,
        phase: data.session.phase as Phase,
        posts: data.posts,
        energyHistory: data.energy_history,
        phaseHistory,
        triggers,
        consensus: data.consensus,
        connected: false,
        error: null,
        thinking: false,
      });
    } catch (err) {
      setState(s => ({ ...s, error: String(err) }));
    }
  }, []);

  const reset = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    setState({ ...initialState });
  }, []);

  const intervene = useCallback((content: string, interventionType: string = 'question') => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: 'intervene',
        intervention_type: interventionType,
        content,
      }));
    }
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      wsRef.current?.close();
    };
  }, []);

  return { state, createAndStart, loadSession, reset, intervene };
}
