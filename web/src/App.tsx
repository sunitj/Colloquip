import { useCallback, useEffect, useState } from 'react';
import { useDeliberation } from './hooks/useDeliberation';
import { ControlBar } from './components/ControlBar';
import { AgentRoster } from './components/AgentRoster';
import { ConversationStream } from './components/ConversationStream';
import { EnergyChart } from './components/EnergyChart';
import { PhaseTimeline } from './components/PhaseTimeline';
import { TriggerLog } from './components/TriggerLog';
import { ConsensusView } from './components/ConsensusView';
import { InterventionBar } from './components/InterventionBar';
import { SessionList } from './components/SessionList';
import './App.css';

type LeftTab = 'agents' | 'history';

function App() {
  const { state, createAndStart, loadSession, reset, intervene } = useDeliberation();
  const [leftTab, setLeftTab] = useState<LeftTab>('agents');

  const handleSelectSession = useCallback((sessionId: string) => {
    loadSession(sessionId);
    setLeftTab('agents');
  }, [loadSession]);

  const handleNewDeliberation = useCallback(() => {
    reset();
    setLeftTab('agents');
  }, [reset]);

  // Keyboard shortcuts
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      const tag = (e.target as HTMLElement).tagName;
      if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return;

      if (e.key === 'Escape') {
        const input = document.querySelector<HTMLInputElement>('.intervention-input');
        if (input) { input.focus(); e.preventDefault(); }
      } else if (e.key === 'h') {
        setLeftTab(t => t === 'history' ? 'agents' : 'history');
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, []);

  const isHistorical = state.status === 'completed' && !state.connected;

  return (
    <div className="app">
      <ControlBar
        onStart={createAndStart}
        status={state.status}
        hypothesis={state.hypothesis}
      />

      {isHistorical && state.sessionId && (
        <div className="history-banner">
          Viewing historical session
          <button className="history-banner-btn" onClick={handleNewDeliberation}>
            New Deliberation
          </button>
        </div>
      )}

      {state.error && (
        <div className="error-banner">
          {state.error}
        </div>
      )}

      <div className="dashboard">
        {/* Left panel: Agent Roster or History */}
        <aside className="panel-left">
          <div className="left-tab-toggle">
            <button
              className={`tab-btn ${leftTab === 'agents' ? 'active' : ''}`}
              onClick={() => setLeftTab('agents')}
            >
              Agents
            </button>
            <button
              className={`tab-btn ${leftTab === 'history' ? 'active' : ''}`}
              onClick={() => setLeftTab('history')}
            >
              History
            </button>
          </div>
          {leftTab === 'agents' ? (
            <AgentRoster
              posts={state.posts}
              triggers={state.triggers}
              status={state.status}
            />
          ) : (
            <SessionList
              onSelect={handleSelectSession}
              onNew={handleNewDeliberation}
              currentSessionId={state.sessionId}
            />
          )}
        </aside>

        {/* Center panel: Conversation */}
        <main className="panel-center">
          {state.consensus ? (
            <ConsensusView consensus={state.consensus} />
          ) : (
            <ConversationStream
              posts={state.posts}
              status={state.status}
              thinking={state.thinking}
            />
          )}
        </main>

        {/* Right panel: Dynamics */}
        <aside className="panel-right">
          <EnergyChart history={state.energyHistory} />
          <PhaseTimeline
            currentPhase={state.phase}
            phaseHistory={state.phaseHistory}
          />
        </aside>
      </div>

      {/* Intervention bar */}
      <InterventionBar onIntervene={intervene} status={state.status} />

      {/* Bottom panel: Trigger Log */}
      <footer className="panel-bottom">
        <TriggerLog triggers={state.triggers} />
      </footer>

      {/* Connection indicator */}
      <div className={`connection-indicator ${state.connected ? 'connected' : ''}`}>
        {state.connected ? '● Connected' : '○ Disconnected'}
      </div>
    </div>
  );
}

export default App;
