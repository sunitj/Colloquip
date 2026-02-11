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
          energyHistory: [...s.energyHistory, evt.data as EnergyUpdate],
        }));
        break;

      case 'session_complete':
        setState(s => ({
          ...s,
          status: 'completed',
          consensus: evt.data as ConsensusMap,
        }));
        break;

      case 'done':
        setState(s => ({ ...s, status: 'completed' }));
        break;

      case 'error':
        setState(s => ({ ...s, error: (evt.data as { message: string }).message }));
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
      setState(s => ({ ...s, status: 'running' }));

    } catch (err) {
      setState(s => ({ ...s, error: String(err) }));
    }
  }, [connect]);

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

  return { state, createAndStart, intervene };
}
