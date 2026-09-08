import { useState, useEffect, useMemo, useRef } from 'react';
import './index.css';

const formatMoney = (amount) => new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(amount);
const formatTime = (isoString) => {
  if (!isoString) return '';
  const d = new Date(isoString);
  return d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: false, timeZone: 'UTC' });
};

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

  // Optional: Auto-start the agent stream once
  useEffect(() => {
    if (incidentData && !hasStartedAgent.current) {
      hasStartedAgent.current = true;
      runAgent();
    }
  }, [incidentData]);

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

  const activeData = useMemo(() => {
    if (!incidentData) return null;
    if (selectedScenario === 'baseline') return incidentData.baseline;
    return incidentData.interventions.find(i => i.id === selectedScenario);
  }, [incidentData, selectedScenario]);

  if (!incidentData) return <div className="loading">INITIALIZING SECURE CONNECTION...</div>;

  const { baseline, interventions, causal_graph, recommendation } = incidentData;

  // Display order is always A → B → C, regardless of engine rank sort.
  const DISPLAY_ORDER = ['intervention-a', 'intervention-b', 'intervention-c'];
  const orderedInterventions = DISPLAY_ORDER
    .map(id => interventions.find(i => i.id === id))
    .filter(Boolean);

  // Timeline computation — values come from backend only.
  const baseTimeStr = "2026-09-08T14:22:00Z";
  const baseTime = new Date(baseTimeStr).getTime();
  const wrapTime = new Date(activeData.projected_wrap_utc).getTime();
  const hardOutTime = new Date(activeData.actor_hard_out_utc).getTime();
  const maxTime = new Date("2026-09-08T22:00:00Z").getTime();

  const getPercent = (time) => {
    const p = ((time - baseTime) / (maxTime - baseTime)) * 100;
    return Math.min(Math.max(p, 0), 100);
  };

  const wrapPercent = getPercent(wrapTime);
  const hardOutPercent = getPercent(hardOutTime);

  // Hard-out delta: positive = breach (wrap is past hard-out), negative = buffer remaining.
  // Computed purely from the two UTC strings the backend already returned — no new math.
  const hardOutDeltaMinutes = Math.round((wrapTime - hardOutTime) / 60000);

  return (
    <div className="control-room">
      <div className="header-panel">
        <div className="header-left">
          <h1>BACKLOT MISSION CONTROL</h1>
          <div className="incident-meta">
            <span className="meta-item">STAGE 4</span>
            <span className="meta-item">SCENE 24 — THE CITADEL INFILTRATION</span>
            <span className="meta-item">DAY 18 / 45</span>
          </div>
        </div>
        <div className="header-right">
          <div className="status-badge halted">STATUS: HALTED</div>
          <div className="incident-time">14:22 SYSTEM TIME</div>
        </div>
      </div>

      <div className="time-machine-controls">
        <button 
          className={`tm-btn ${selectedScenario === 'baseline' ? 'active' : ''}`}
          onClick={() => setSelectedScenario('baseline')}
        >
          BASELINE
        </button>
        {orderedInterventions.map(inv => (
          <button
            key={inv.id}
            className={`tm-btn ${selectedScenario === inv.id ? 'active' : ''} ${inv.recommended ? 'recommended' : ''}`}
            onClick={() => setSelectedScenario(inv.id)}
          >
            {inv.id === 'intervention-a' ? 'A — HARDWARE SWAP' :
             inv.id === 'intervention-b' ? 'B — BAND B + BUFFER BYPASS' :
             'C — ABANDON / RESCHEDULE'}
            {inv.recommended && <span className="rec-badge">RANK #1 · RECOMMENDED</span>}
          </button>
        ))}
      </div>

      <div className="main-grid">
        
        {/* Left Column: Causal & Terminal */}
        <div className="left-col">
          <div className="panel causal-panel">
            <h2>CAUSAL DEPENDENCY GRAPH</h2>
            <div className="dag-container">
              {causal_graph.critical_path.map((nodeId, idx) => {
                const node = causal_graph.nodes.find(n => n.id === nodeId);
                if (!node) return null;
                // Highlight intervention node if applicable
                let isHighlighted = false;
                if (selectedScenario === 'intervention-a' && nodeId === 'IR_STROBE') isHighlighted = true;
                if (selectedScenario === 'intervention-b' && nodeId === 'PACKET_LOSS') isHighlighted = true;

                return (
                  <div key={nodeId} className="dag-node-wrapper">
                    <div className={`dag-node ${isHighlighted ? 'intervened' : ''}`}>
                      {node.description}
                    </div>
                    {idx < causal_graph.critical_path.length - 1 && <div className="dag-arrow">↓</div>}
                  </div>
                );
              })}
            </div>
          </div>

          <div className="panel terminal-panel">
            <div className="panel-header">
              <h2>AGENT TERMINAL</h2>
              <button className="re-run-btn" onClick={runAgent} disabled={investigating}>
                {investigating ? 'INVESTIGATING...' : 'RE-RUN AGENT'}
              </button>
            </div>
            <div className="terminal-window">
              <ul>
                {events.map((ev, i) => (
                  <li key={i} className={ev.type === 'EVIDENCE' ? 'evidence-line' : ''}>
                    <span className="term-time">[{ev.timestamp ? formatTime(ev.timestamp) : 'SYS'}]</span>
                    <span className="term-type">{ev.type}</span> 
                    <span className="term-msg">
                      {ev.message || ev.tools || (ev.evidence && `Evidence: ${ev.evidence.source} - ${ev.evidence.value}`)}
                    </span>
                  </li>
                ))}
                {investigating && <li className="blinking-cursor">_</li>}
              </ul>
            </div>
          </div>
        </div>

        {/* Right Column: Financials, Gantt, Evidence */}
        <div className="right-col">
          
          <div className="panel financial-panel">
            <div className="fin-grid">
              <div className="fin-box total-exposure">
                <h3>TOTAL EXPOSURE</h3>
                <div className="big-money">{formatMoney(activeData.total_usd || activeData.total_blast_radius_usd)}</div>
              </div>
              <div className="fin-box savings">
                <h3>SAVINGS</h3>
                <div className="big-money savings-val">
                  {selectedScenario === 'baseline' ? '$0' : formatMoney(activeData.net_savings_usd)}
                </div>
              </div>
              <div className="fin-box delay-box">
                <h3>REMAINING DELAY</h3>
                <div className="big-time">{activeData.remaining_delay_minutes ?? activeData.delay_minutes} MIN</div>
              </div>
              <div className="fin-box hard-out-box">
                <h3>ACTOR HARD-OUT</h3>
                <div className={`hard-out-status ${activeData.actor_hard_out_breached ? 'breached' : 'preserved'}`}>
                  {activeData.actor_hard_out_breached ? 'BREACHED' : 'PRESERVED'}
                </div>
              </div>
            </div>
            <div className="cost-breakdown">
              <div className="cost-item">
                <span className="label">Stage Idle Cost ($450/min):</span>
                <span className="value">{formatMoney(activeData.idle_waste_usd ?? activeData.idle_cost_usd)}</span>
              </div>
              <div className="cost-item">
                <span className="label">OT Surcharge (+$225/min):</span>
                <span className="value">{formatMoney(activeData.overtime_surcharge_usd)}</span>
              </div>
              {activeData.direct_implementation_fee_usd > 0 && (
                <div className="cost-item">
                  <span className="label">Direct Implementation Fee:</span>
                  <span className="value">{formatMoney(activeData.direct_implementation_fee_usd)}</span>
                </div>
              )}
              <div className="cost-item">
                <span className="label">Actor Penalty:</span>
                <span className="value">{formatMoney(activeData.penalty_usd)}</span>
              </div>
            </div>
          </div>

          <div className="panel gantt-panel">
            <h2>PROJECTED TIMELINE</h2>
            <div className="gantt-three-lane">

              {/* Lane 1 — incident bar */}
              <div className="gantt-lane lane-incident">
                <div className="lane-label-left">14:22</div>
                <div className="gantt-track">
                  <div className="gantt-bar" style={{ width: `${wrapPercent}%` }} />
                </div>
                <div className="lane-label-right">22:00</div>
              </div>

              {/* Lane 2 — Actor Hard-Out */}
              <div className="gantt-lane lane-hardout">
                <div className="lane-spacer" />
                <div className="lane-track">
                  <div
                    className="lane-marker hard-out-lane-marker"
                    style={{ left: `${hardOutPercent}%` }}
                  >
                    <div className="lane-tick" />
                    <div className="lane-tick-label">
                      ACTOR HARD-OUT · 18:30
                      <span className={activeData.actor_hard_out_breached ? 'breach-pill' : 'preserve-pill'}>
                        {activeData.actor_hard_out_breached
                          ? `BREACH +${hardOutDeltaMinutes} MIN`
                          : `PRESERVED · ${Math.abs(hardOutDeltaMinutes)} MIN BUFFER`}
                      </span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Lane 3 — Projected Wrap */}
              <div className="gantt-lane lane-wrap">
                <div className="lane-spacer" />
                <div className="lane-track">
                  <div
                    className="lane-marker wrap-lane-marker"
                    style={{ left: `${wrapPercent}%` }}
                  >
                    <div className="lane-tick" />
                    <div className="lane-tick-label">
                      PROJECTED WRAP · {formatTime(activeData.projected_wrap_utc)}
                    </div>
                  </div>
                </div>
              </div>

            </div>
          </div>

          <div className="panel evidence-panel">
            <h2>TELEMETRY EVIDENCE</h2>
            <div className="evidence-items">
              <div className="ev-item prometheus">
                <div className="ev-source">PROMETHEUS</div>
                <div className="ev-query">backlot_tracking_packet_drop_ratio</div>
                <div className="ev-val">PEAK ≈ 0.184</div>
              </div>
              <div className="ev-item prometheus">
                <div className="ev-source">PROMETHEUS</div>
                <div className="ev-query">backlot_dit_ingest_buffer_percent</div>
                <div className="ev-val">PEAK ≈ 98%</div>
              </div>
              <div className="ev-item loki">
                <div className="ev-source">LOKI</div>
                <div className="ev-query">Camera Recording State</div>
                <div className="ev-val">TRANSITION TO OFF</div>
              </div>
            </div>
          </div>

        </div>
      </div>
    </div>
  );
}
