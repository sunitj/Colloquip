/** TypeScript types matching Python Pydantic models */

export type Phase = 'explore' | 'debate' | 'deepen' | 'converge' | 'synthesis';
export type AgentStance = 'supportive' | 'critical' | 'neutral' | 'novel_connection';
export type SessionStatus = 'pending' | 'running' | 'paused' | 'completed';

export interface Citation {
  document_id: string;
  title: string;
  excerpt: string;
  relevance: number;
}

export interface Post {
  id: string;
  session_id: string;
  agent_id: string;
  content: string;
  stance: AgentStance;
  citations: Citation[];
  key_claims: string[];
  questions_raised: string[];
  connections_identified: string[];
  novelty_score: number;
  phase: Phase;
  triggered_by: string[];
  created_at: string;
}

export interface EnergyUpdate {
  turn: number;
  energy: number;
  components: {
    novelty: number;
    disagreement: number;
    questions: number;
    staleness: number;
  };
}

export interface PhaseSignal {
  current_phase: Phase;
  confidence: number;
  metrics: {
    question_rate: number;
    disagreement_rate: number;
    topic_diversity: number;
    citation_density: number;
    novelty_avg: number;
    energy: number;
    posts_since_novel: number;
  };
  observation: string | null;
}

export interface ConsensusMap {
  session_id: string;
  summary: string;
  agreements: string[];
  disagreements: string[];
  minority_positions: string[];
  serendipity_connections: Array<{ agent: string; connection: string }>;
  final_stances: Record<string, AgentStance>;
}

export interface AgentInfo {
  id: string;
  name: string;
  color: string;
  postCount: number;
  lastTrigger: string | null;
  status: 'active' | 'refractory' | 'idle';
}

export interface TriggerEntry {
  timestamp: string;
  agentId: string;
  agentName: string;
  rules: string[];
  postIndex: number;
}

export interface DeliberationState {
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
}

export type WSEvent =
  | { type: 'session_state'; data: { id: string; hypothesis: string; status: string; phase: string }; seq: number }
  | { type: 'post'; data: Post; seq: number }
  | { type: 'phase_change'; data: PhaseSignal; seq: number }
  | { type: 'energy_update'; data: EnergyUpdate; seq: number }
  | { type: 'session_complete'; data: ConsensusMap; seq: number }
  | { type: 'done'; data: null; seq: number }
  | { type: 'error'; data: { message: string }; seq: number }
  | { type: 'ack'; data: { action: string }; seq: number }
  | { type: 'timeout'; data: { message: string }; seq: number };
