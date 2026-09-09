import { useState, useEffect, useMemo, useRef } from 'react';
import './index.css';

import BacklotShell from './components/BacklotShell';
import IncidentHeader from './components/IncidentHeader';
import CausalReconstruction from './components/CausalReconstruction';
import EvidenceTimeline from './components/EvidenceTimeline';
import TimeMachine from './components/TimeMachine';
import FinancialBlastRadius from './components/FinancialBlastRadius';
import AgentTerminal from './components/AgentTerminal';

export default function App() {
  const [incidentData, setIncidentData] = useState(null);
  const [selectedScenario, setSelectedScenario] = useState('baseline');
  const [events, setEvents] = useState([]);
  const [investigating, setInvestigating] = useState(false);
  const hasStartedAgent = useRef(false);

  useEffect(() => {
    fetch('http://localhost:8000/api/incident')
      .then(res => res.json())
      .then(data => setIncidentData(data))
      .catch(console.error);
  }, []);

  const runAgent = () => {
    setEvents([]);
    setInvestigating(true);
    const eventSource = new EventSource(`http://localhost:8000/api/stream?query=${encodeURIComponent("Investigate Stage 4 tracking packet drop ratio")}`);
    eventSource.onmessage = (e) => {
      const data = JSON.parse(e.data);
      setEvents(prev => [...prev, data]);
      if (data.type === 'ERROR' || data.type === 'INVESTIGATION_COMPLETE') {
        setInvestigating(false);
        eventSource.close();
      }
    };
    eventSource.onerror = () => {
      setInvestigating(false);
      eventSource.close();
    };
  };

  useEffect(() => {
    if (incidentData && !hasStartedAgent.current) {
      hasStartedAgent.current = true;
      runAgent();
    }
  }, [incidentData]);

  const activeData = useMemo(() => {
    if (!incidentData) return null;
    if (selectedScenario === 'baseline') return incidentData.baseline;
    return incidentData.interventions.find(i => i.id === selectedScenario);
  }, [incidentData, selectedScenario]);

  if (!incidentData) return (
    <BacklotShell>
      <div className="loading-screen">
        <div className="loading-text">INITIALIZING SECURE CONNECTION...</div>
      </div>
    </BacklotShell>
  );

  return (
    <BacklotShell>
      <div className="control-room">
        <IncidentHeader incidentTimeStr={incidentData.incident_time_utc} />
        
        <div className="main-layout">
          {/* Left Column: Causal & Terminal & Evidence */}
          <div className="col-left">
            <EvidenceTimeline />
            <CausalReconstruction 
              causal_graph={incidentData.causal_graph} 
              selectedScenario={selectedScenario} 
            />
            <AgentTerminal 
              events={events} 
              investigating={investigating} 
              runAgent={runAgent} 
            />
          </div>

          {/* Right Column: Time Machine & Financial */}
          <div className="col-right">
            <TimeMachine 
              incidentData={incidentData} 
              selectedScenario={selectedScenario} 
              setSelectedScenario={setSelectedScenario}
              activeData={activeData}
            />
            <FinancialBlastRadius 
              activeData={activeData}
              selectedScenario={selectedScenario}
              incidentData={incidentData}
            />
          </div>
        </div>
      </div>
    </BacklotShell>
  );
}