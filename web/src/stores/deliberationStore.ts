import { create } from 'zustand';
import type { ConsensusMap, EnergyUpdate, Phase, PhaseSignal, Post, SessionStatus, TriggerEntry } from '@/types/deliberation';

interface DeliberationStore {
  sessionId: string | null;
  hypothesis: string;
  status: SessionStatus;
  phase: Phase;
  posts: Post[];
  energyHistory: EnergyUpdate[];
  phaseHistory: PhaseSignal[];
  triggers: TriggerEntry[];
  consensus: ConsensusMap | null;
  connected: boolean;
  error: string | null;
  thinking: boolean;

  setSession: (sessionId: string, hypothesis: string) => void;
  setStatus: (status: SessionStatus) => void;
  setPhase: (phase: Phase) => void;
  setConnected: (connected: boolean) => void;
  setError: (error: string | null) => void;
  setThinking: (thinking: boolean) => void;
  addPost: (post: Post) => void;
  addEnergyUpdate: (update: EnergyUpdate) => void;
  addPhaseSignal: (signal: PhaseSignal) => void;
  setConsensus: (consensus: ConsensusMap) => void;
  loadHistory: (data: {
    sessionId: string;
    hypothesis: string;
    status: SessionStatus;
    phase: Phase;
    posts: Post[];
    energyHistory: EnergyUpdate[];
    consensus: ConsensusMap | null;
  }) => void;
  reset: () => void;
}

const initialState = {
  sessionId: null as string | null,
  hypothesis: '',
  status: 'pending' as SessionStatus,
  phase: 'explore' as Phase,
  posts: [] as Post[],
  energyHistory: [] as EnergyUpdate[],
  phaseHistory: [] as PhaseSignal[],
  triggers: [] as TriggerEntry[],
  consensus: null as ConsensusMap | null,
  connected: false,
  error: null as string | null,
  thinking: false,
};

export const useDeliberationStore = create<DeliberationStore>((set) => ({
  ...initialState,

  setSession: (sessionId, hypothesis) => set({ sessionId, hypothesis }),
  setStatus: (status) => set({ status }),
  setPhase: (phase) => set({ phase }),
  setConnected: (connected) => set({ connected }),
  setError: (error) => set({ error }),
  setThinking: (thinking) => set({ thinking }),

  addPost: (post) => set((state) => {
    const newPosts = [...state.posts, post];
    const trigger: TriggerEntry = {
      timestamp: post.created_at,
      agentId: post.agent_id,
      agentName: post.agent_id,
      rules: post.triggered_by,
      postIndex: newPosts.length - 1,
    };
    return { posts: newPosts, triggers: [...state.triggers, trigger], thinking: false };
  }),

  addEnergyUpdate: (update) => set((state) => ({
    energyHistory: [...state.energyHistory, update],
    thinking: true,
  })),

  addPhaseSignal: (signal) => set((state) => ({
    phase: signal.current_phase,
    phaseHistory: [...state.phaseHistory, signal],
  })),

  setConsensus: (consensus) => set({ consensus, status: 'completed', thinking: false }),

  loadHistory: (data) => {
    const triggers: TriggerEntry[] = data.posts.map((post, i) => ({
      timestamp: post.created_at,
      agentId: post.agent_id,
      agentName: post.agent_id,
      rules: post.triggered_by,
      postIndex: i,
    }));

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

    set({
      ...data,
      phaseHistory,
      triggers,
      connected: false,
      error: null,
      thinking: false,
    });
  },

  reset: () => set(initialState),
}));
