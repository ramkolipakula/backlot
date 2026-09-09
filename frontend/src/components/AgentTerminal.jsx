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
    </div>
  );
}
