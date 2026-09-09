import { useState, useEffect, useMemo, useRef } from 'react';
import './index.css';

import BacklotShell from './components/BacklotShell';
import IncidentHeader from './components/IncidentHeader';
import CausalReconstruction from './components/CausalReconstruction';
import EvidenceTimeline from './components/EvidenceTimeline';
import TimeMachine from './components/TimeMachine';
import FinancialBlastRadius from './components/FinancialBlastRadius';
import AgentTerminal from './components/AgentTerminal';
import ManualIncidentForm from './components/ManualIncidentForm';

export default function App() {
  const [appMode, setAppMode] = useState('demo'); // 'demo' or 'manual'
  const [incidentData, setIncidentData] = useState(null);
  const [selectedScenario, setSelectedScenario] = useState('baseline');
  const [events, setEvents] = useState([]);
  const [investigating, setInvestigating] = useState(false);
  const [manualRequest, setManualRequest] = useState(null);
  const hasStartedAgent = useRef(false);

  useEffect(() => {
    if (appMode === 'demo') {
      fetch(`${import.meta.env.VITE_API_URL}/api/incident`)
        .then(res => res.json())
        .then(data => setIncidentData(data))
        .catch(console.error);
    } else {
      setIncidentData(null);
      setEvents([]);
      hasStartedAgent.current = false;
      setManualRequest(null);
    }
  }, [appMode]);

  const runAgent = () => {
    setEvents([]);
    setInvestigating(true);
    const eventSource = new EventSource(`${import.meta.env.VITE_API_URL}/api/stream?query=${encodeURIComponent("Investigate Stage 4 tracking packet drop ratio")}`);
    eventSource.onmessage = (e) => {
      const data = JSON.parse(e.data);
      setEvents(prev => [...prev, data]);
      if (data.type === 'CPM_RESULT') {
        setIncidentData(data.result);
      }
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

  const runManualAgent = async (payload) => {
    setEvents([]);
    setInvestigating(true);
    setManualRequest(payload);
    hasStartedAgent.current = true;
    
    // First get the baseline incident data
    try {
      const res = await fetch(`${import.meta.env.VITE_API_URL}/api/incident/manual`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      setIncidentData(data);
    } catch (e) {
      console.error(e);
    }

    // Then start streaming
    try {
      const res = await fetch(`${import.meta.env.VITE_API_URL}/api/stream/manual`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        
        const lines = buffer.split('\n');
        buffer = lines.pop(); // Keep incomplete line in buffer
        
        let eventData = '';
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            eventData = line.substring(6);
            try {
              const parsed = JSON.parse(eventData);
              setEvents(prev => [...prev, parsed]);
              if (parsed.type === 'CPM_RESULT') {
                setIncidentData(parsed.result);
              }
              if (parsed.type === 'ERROR' || parsed.type === 'INVESTIGATION_COMPLETE') {
                setInvestigating(false);
              }
            } catch (e) {
              console.error('Parse error', e);
            }
          }
        }
      }
    } catch (e) {
      console.error(e);
      setInvestigating(false);
    }
  };

  useEffect(() => {
    if (appMode === 'demo' && incidentData && !hasStartedAgent.current) {
      hasStartedAgent.current = true;
      runAgent();
    }
  }, [incidentData, appMode]);

  const activeData = useMemo(() => {
    if (!incidentData) return null;
    if (selectedScenario === 'baseline') return incidentData.baseline;
    return incidentData.interventions.find(i => i.id === selectedScenario);
  }, [incidentData, selectedScenario]);

  if (appMode === 'manual' && !manualRequest) {
    return (
      <BacklotShell appMode={appMode} setAppMode={setAppMode}>
        <ManualIncidentForm onSubmit={runManualAgent} />
      </BacklotShell>
    );
  }

  if (!incidentData) return (
    <BacklotShell appMode={appMode} setAppMode={setAppMode}>
      <div className="loading-screen">
        <div className="loading-text">INITIALIZING SECURE CONNECTION...</div>
      </div>
    </BacklotShell>
  );

  return (
    <BacklotShell appMode={appMode} setAppMode={setAppMode}>
      <div className="control-room">
        <IncidentHeader 
          incidentTimeStr={incidentData.incident_time_utc} 
          sceneOverride={appMode === 'manual' ? manualRequest?.scene : null}
          productionOverride={appMode === 'manual' ? manualRequest?.production_name : null}
          stageOverride={appMode === 'manual' ? manualRequest?.stage : null}
        />
        
        <div className="main-layout">
          {/* Left Column: Causal & Terminal & Evidence */}
          <div className="col-left">
            <EvidenceTimeline events={events} />
            <CausalReconstruction 
              causal_graph={incidentData.causal_graph} 
              selectedScenario={selectedScenario} 
            />
            <AgentTerminal 
              events={events} 
              investigating={investigating} 
              runAgent={appMode === 'manual' ? () => runManualAgent(manualRequest) : runAgent} 
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