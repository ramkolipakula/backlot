import { formatTime, formatMoney } from './utils';

export default function TimeMachine({ 
  incidentData, 
  selectedScenario, 
  setSelectedScenario,
  activeData
}) {
  const { baseline, interventions } = incidentData;
  const DISPLAY_ORDER = ['intervention-a', 'intervention-b', 'intervention-c'];
  const orderedInterventions = DISPLAY_ORDER
    .map(id => interventions.find(i => i.id === id))
    .filter(Boolean);

  const formatScenarioName = (id) => {
    if (id === 'intervention-a') return 'HARDWARE SWAP';
    if (id === 'intervention-b') return 'TRACKING FAILOVER';
    if (id === 'intervention-c') return 'RESCHEDULE';
    return 'BASELINE';
  };

  const getNumber = (scenarioStr) => {
    if (scenarioStr === 'intervention-a') return '01';
    if (scenarioStr === 'intervention-b') return '02';
    if (scenarioStr === 'intervention-c') return '03';
    return '00';
  }

  // Build the cinematic timeline list
  // Wrap times, hard-out, incident
  const wrapItems = [];
  
  // Incident & Hard out
  wrapItems.push({ time: incidentData.incident_time_utc, label: 'INCIDENT', type: 'incident' });
  wrapItems.push({ time: activeData.actor_hard_out_utc, label: 'ACTOR HARD-OUT', type: 'hard-out' });
  
  // Baseline wrap
  wrapItems.push({ time: baseline.projected_wrap_utc, label: 'BASELINE', type: 'wrap', id: 'baseline' });
  
  // Intervention wraps
  orderedInterventions.forEach((inv, idx) => {
    wrapItems.push({ time: inv.projected_wrap_utc, label: `OPTION ${String.fromCharCode(65+idx)}`, type: 'wrap', id: inv.id });
  });

  // Sort by time
  wrapItems.sort((a, b) => new Date(a.time).getTime() - new Date(b.time).getTime());

  return (
    <div className="panel time-machine-panel">
      <div className="tm-header-area">
        <h2>THE TIME MACHINE</h2>
        <div className="tm-subtitle">REWIND THE INCIDENT.<br/>CHANGE ONE DECISION.<br/>SEE WHAT HAPPENS NEXT.</div>
      </div>

      <div className="tm-layout">
        <div className="tm-timeline">
          {wrapItems.map((item, i) => (
            <div key={i} className={`tm-timeline-node ${item.type} ${item.id === selectedScenario ? 'selected-wrap' : ''}`}>
              <div className="tm-node-label">{item.label}</div>
              <div className="tm-node-time">{formatTime(item.time)}</div>
              {i < wrapItems.length - 1 && <div className="tm-node-connector" />}
            </div>
          ))}
        </div>

        <div className="tm-scenarios">
          <div 
            className={`scenario-strip ${selectedScenario === 'baseline' ? 'active' : ''}`}
            onClick={() => setSelectedScenario('baseline')}
          >
            <div className="strip-header">
              <span className="strip-num">00</span>
              <span className="strip-name">BASELINE</span>
            </div>
            <div className="strip-metrics">
              <div className="strip-metric">
                <span className="sml">WRAP</span>
                <span className="smr">{formatTime(baseline.projected_wrap_utc)}</span>
              </div>
              <div className="strip-metric">
                <span className="sml">EXPOSURE</span>
                <span className="smr">{formatMoney(baseline.total_blast_radius_usd || baseline.total_usd)}</span>
              </div>
            </div>
          </div>

          {orderedInterventions.map((inv) => (
            <div 
              key={inv.id}
              className={`scenario-strip ${selectedScenario === inv.id ? 'active' : ''} ${inv.recommended ? 'recommended' : ''}`}
              onClick={() => setSelectedScenario(inv.id)}
            >
              {inv.recommended && <div className="rec-bar">RECOMMENDED</div>}
              <div className="strip-header">
                <span className="strip-num">{getNumber(inv.id)}</span>
                <span className="strip-name">{formatScenarioName(inv.id)}</span>
              </div>
              <div className="strip-metrics">
                <div className="strip-metric">
                  <span className="sml">RECOVERY</span>
                  <span className="smr">{inv.recovery_minutes} MIN</span>
                </div>
                <div className="strip-metric">
                  <span className="sml">PROJECTED WRAP</span>
                  <span className="smr">{formatTime(inv.projected_wrap_utc)}</span>
                </div>
                <div className="strip-metric">
                  <span className="sml">EXPOSURE</span>
                  <span className="smr">{formatMoney(inv.total_usd)}</span>
                </div>
                <div className="strip-metric savings-metric">
                  <span className="sml">SAVINGS</span>
                  <span className="smr">{formatMoney(inv.net_savings_usd)}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
