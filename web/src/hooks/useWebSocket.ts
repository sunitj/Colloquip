import { useEffect } from 'react';
import { wsService } from '@/lib/websocket';
import { useDeliberationStore } from '@/stores/deliberationStore';
import type { ConsensusMap, EnergyUpdate, Phase, PhaseSignal, Post, SessionStatus } from '@/types/deliberation';

export function useWebSocket(sessionId: string | null) {
  const store = useDeliberationStore();

  useEffect(() => {
    if (!sessionId) return;

    wsService.connect(sessionId);

    const unsubEvent = wsService.onEvent((evt) => {
      switch (evt.type) {
        case 'session_state':
          store.setSession(evt.data.id, evt.data.hypothesis);
          store.setStatus(evt.data.status as SessionStatus);
          store.setPhase(evt.data.phase as Phase);
          break;
        case 'post':
          store.addPost(evt.data as Post);
          break;
        case 'phase_change':
          store.addPhaseSignal(evt.data as PhaseSignal);
          break;
        case 'energy_update':
          store.addEnergyUpdate(evt.data as EnergyUpdate);
          break;
        case 'session_complete':
          store.setConsensus(evt.data as ConsensusMap);
          break;
        case 'done':
          store.setStatus('completed');
          store.setThinking(false);
          break;
        case 'error':
          store.setError((evt.data as { message: string }).message);
          store.setThinking(false);
          break;
        case 'timeout':
          store.setError('Connection timed out');
          store.setConnected(false);
          break;
      }
    });

    const unsubStatus = wsService.onStatus((connected) => {
      store.setConnected(connected);
      if (!connected) store.setError(null);
    });

    return () => {
      unsubEvent();
      unsubStatus();
      wsService.disconnect();
    };
  }, [sessionId]); // eslint-disable-line react-hooks/exhaustive-deps

  return {
    startDeliberation: () => wsService.startDeliberation(),
    intervene: (type: string, content: string) => wsService.intervene(type, content),
    isConnected: wsService.isConnected,
  };
}
