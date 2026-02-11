import { useDeliberation } from './hooks/useDeliberation';
import { ControlBar } from './components/ControlBar';
import { AgentRoster } from './components/AgentRoster';
import { ConversationStream } from './components/ConversationStream';
import { EnergyChart } from './components/EnergyChart';
import { PhaseTimeline } from './components/PhaseTimeline';
import { TriggerLog } from './components/TriggerLog';
import { ConsensusView } from './components/ConsensusView';
import './App.css';

function App() {
  const { state, createAndStart } = useDeliberation();

  return (
    <div className="app">
      <ControlBar
        onStart={createAndStart}
        status={state.status}
        hypothesis={state.hypothesis}
      />

      {state.error && (
        <div className="error-banner">
          {state.error}
        </div>
      )}

      <div className="dashboard">
        {/* Left panel: Agent Roster */}
        <aside className="panel-left">
          <AgentRoster
            posts={state.posts}
            triggers={state.triggers}
            status={state.status}
          />
        </aside>

        {/* Center panel: Conversation */}
        <main className="panel-center">
          {state.consensus ? (
            <ConsensusView consensus={state.consensus} />
          ) : (
            <ConversationStream posts={state.posts} />
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
