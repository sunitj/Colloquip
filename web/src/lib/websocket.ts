import type { WSEvent } from '@/types/deliberation';

type EventCallback = (event: WSEvent) => void;
type StatusCallback = (connected: boolean) => void;

class WebSocketService {
  private ws: WebSocket | null = null;
  private sessionId: string | null = null;
  private eventListeners = new Set<EventCallback>();
  private statusListeners = new Set<StatusCallback>();
  private seq = 0;

  connect(sessionId: string) {
    this.disconnect();
    this.sessionId = sessionId;
    this.seq = 0;

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const ws = new WebSocket(`${protocol}//${window.location.host}/ws/deliberations/${sessionId}`);
    this.ws = ws;

    ws.onopen = () => {
      this.notifyStatus(true);
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data) as WSEvent;
        this.seq = Math.max(this.seq, data.seq);
        this.notifyEvent(data);
      } catch (err) {
        console.error('Failed to parse WebSocket message:', err);
      }
    };

    ws.onclose = () => {
      this.notifyStatus(false);
    };

    ws.onerror = () => {
      this.notifyStatus(false);
    };
  }

  disconnect() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.sessionId = null;
  }

  send(message: Record<string, unknown>) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
    }
  }

  startDeliberation() {
    this.send({ type: 'start' });
  }

  intervene(interventionType: string, content: string) {
    this.send({ type: 'intervene', intervention_type: interventionType, content });
  }

  replay(since: number) {
    this.send({ type: 'replay', since });
  }

  onEvent(callback: EventCallback): () => void {
    this.eventListeners.add(callback);
    return () => this.eventListeners.delete(callback);
  }

  onStatus(callback: StatusCallback): () => void {
    this.statusListeners.add(callback);
    return () => this.statusListeners.delete(callback);
  }

  get isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }

  get currentSessionId(): string | null {
    return this.sessionId;
  }

  get lastSeq(): number {
    return this.seq;
  }

  private notifyEvent(event: WSEvent) {
    for (const listener of this.eventListeners) {
      listener(event);
    }
  }

  private notifyStatus(connected: boolean) {
    for (const listener of this.statusListeners) {
      listener(connected);
    }
  }
}

export const wsService = new WebSocketService();
