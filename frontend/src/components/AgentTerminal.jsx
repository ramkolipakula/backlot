import { formatTime } from './utils';

export default function AgentTerminal({ events, investigating, runAgent }) {
  return (
    <div className="panel terminal-panel">
      <div className="terminal-header">
        <div className="terminal-title">BACKLOT INVESTIGATOR</div>
        <div className="terminal-status">
          <span className="status-label">GEMINI / ADK</span>
          <span className={`status-indicator ${investigating ? 'active' : ''}`}>
            {investigating ? 'INVESTIGATION ACTIVE' : 'STANDBY'}
          </span>
          {!investigating && (
             <button className="re-run-btn" onClick={runAgent}>RE-RUN</button>
          )}
        </div>
      </div>
      
      <div className="terminal-window">
        <ul>
          {events.map((ev, i) => {
            // Filter out excessive internal thinking or raw outputs if possible.
            // Just display concise operational steps as requested.
            let msg = ev.message || ev.tools || (ev.evidence && `Evidence: ${ev.evidence.source} - ${ev.evidence.value}`);
            if (ev.type === 'EVIDENCE' && ev.evidence) {
                msg = `EVIDENCE SUPPORTED: ${ev.evidence.source} [${ev.evidence.value}]`;
            } else if (ev.type === 'HYPOTHESIS') {
                msg = `TESTING HYPOTHESIS: ${ev.message}`;
            } else if (ev.type === 'PLAN') {
                msg = `INGESTING INCIDENT`;
            } else if (ev.type === 'TOOL_CALL') {
                msg = `QUERYING GRAFANA TELEMETRY: ${ev.tools}`;
            }

            // Map technical backend agent outputs to cinematic plain English
            if (msg.includes('Investigating: Investigate Stage 4 tracking packet drop ratio')) {
              msg = 'Investigating the camera tracking problem';
            } else if (msg.includes('Querying Grafana for available datasources')) {
              msg = 'Checking production data in Grafana...';
            } else if (msg.includes('Discovered 13 datasource(s)')) {
              msg = 'Production data sources found';
            } else if (msg.includes('Testing hypothesis H1:') && msg.includes('DIT storage failure')) {
              msg = 'Testing possibility: FOOTAGE STORAGE FAILURE';
            } else if (msg === 'H1 rejected') {
              msg = 'STORAGE FAILURE NOT SUPPORTED BY THE DATA';
            } else if (msg.includes('Testing hypothesis H2:') && msg.includes('optical tracking disruption')) {
              msg = 'Testing possibility: CAMERA TRACKING FAILURE';
            } else if (msg === 'H2 supported by telemetry') {
              msg = 'TRACKING FAILURE SUPPORTED BY THE DATA';
            }
            
            return (
              <li key={i} className={`term-line ${ev.type.toLowerCase()}`}>
                <span className="term-time">{ev.timestamp ? formatTime(ev.timestamp) : 'SYS'}</span>
                <span className="term-msg">{msg}</span>
              </li>
            );
          })}
          {investigating && <li className="blinking-cursor">_</li>}
        </ul>
      </div>

      <div className="provenance-area" style={{ display: 'flex', justifyContent: 'space-between', marginTop: '1rem', paddingTop: '1rem', borderTop: '1px solid var(--border-subtle)', fontFamily: 'var(--font-mono)', fontSize: '0.65rem' }}>
        <div>
          <div style={{ color: 'var(--text-muted)' }}>DATA SOURCE</div>
          <div style={{ color: 'var(--text-secondary)' }}>Grafana Cloud</div>
        </div>
        <div>
          <div style={{ color: 'var(--text-muted)' }}>TELEMETRY</div>
          <div style={{ color: 'var(--text-secondary)' }}>Prometheus</div>
        </div>
        <div>
          <div style={{ color: 'var(--text-muted)' }}>LOGS</div>
          <div style={{ color: 'var(--text-secondary)' }}>Loki</div>
        </div>
        <div>
          <div style={{ color: 'var(--text-muted)' }}>AI INVESTIGATION</div>
          <div style={{ color: 'var(--text-secondary)' }}>Gemini + Google ADK</div>
        </div>
        <div>
          <div style={{ color: 'var(--text-muted)' }}>DECISION WRITEBACK</div>
          <div style={{ color: 'var(--text-secondary)' }}>Grafana MCP</div>
        </div>
      </div>
    </div>
  );
}
