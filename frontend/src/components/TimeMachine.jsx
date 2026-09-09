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
    if (id === 'intervention-a') return 'REPLACE THE TRACKING HARDWARE';
    if (id === 'intervention-b') return 'SWITCH TO BACKUP TRACKING';
    if (id === 'intervention-c') return 'RESCHEDULE';
    return 'CURRENT COURSE';
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
  wrapItems.push({ time: incidentData.incident_time_utc, label: 'FILMING STOPS', type: 'incident' });
  wrapItems.push({ time: activeData.actor_hard_out_utc, label: 'ACTOR MUST LEAVE', type: 'hard-out' });
  
  // Baseline wrap
  wrapItems.push({ time: baseline.projected_wrap_utc, label: 'CURRENT COURSE WRAP', type: 'wrap', id: 'baseline' });
  
  // Intervention wraps
  orderedInterventions.forEach((inv, idx) => {
    let label = 'WRAP';
    if (inv.id === 'intervention-a') label = 'HARDWARE SWAP WRAP';
    if (inv.id === 'intervention-b') label = 'BACKUP TRACKING WRAP';
    if (inv.id === 'intervention-c') label = 'RESCHEDULE WRAP';
    wrapItems.push({ time: inv.projected_wrap_utc, label: label, type: 'wrap', id: inv.id });
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
              <div>
                <div className="strip-name">CURRENT COURSE</div>
                <div className="panel-subtitle" style={{marginTop: '4px', opacity: 0.8}}>Continue without intervention</div>
              </div>
            </div>
            <div className="strip-metrics">
              <div className="strip-metric">
                <span className="sml">NEW WRAP TIME</span>
                <span className="smr">{formatTime(baseline.projected_wrap_utc)}</span>
              </div>
              <div className="strip-metric">
                <span className="sml">TOTAL COST</span>
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
              {inv.recommended && <div className="rec-bar">RECOMMENDED &middot; BEST OUTCOME</div>}
              <div className="strip-header">
                <span className="strip-num">{getNumber(inv.id)}</span>
                <div>
                  <div className="strip-name">{formatScenarioName(inv.id)}</div>
                  {inv.id === 'intervention-a' && <div className="panel-subtitle" style={{marginTop: '4px', opacity: 0.8}}>Swap the affected tracking equipment</div>}
                  {inv.id === 'intervention-b' && <div className="panel-subtitle" style={{marginTop: '4px', opacity: 0.8}}>Move the camera to the backup tracking channel</div>}
                </div>
              </div>
              <div className="strip-metrics">
                <div className="strip-metric">
                  <span className="sml">TIME TO RECOVER</span>
                  <span className="smr">{inv.recovery_minutes} MIN</span>
                </div>
                <div className="strip-metric">
                  <span className="sml">NEW WRAP TIME</span>
                  <span className="smr">{formatTime(inv.projected_wrap_utc)}</span>
                </div>
                <div className="strip-metric">
                  <span className="sml">TOTAL COST</span>
                  <span className="smr">{formatMoney(inv.total_usd)}</span>
                </div>
                <div className="strip-metric savings-metric">
                  <span className="sml">MONEY SAVED</span>
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
