import { formatTime } from './utils';

/**
 * AgentTerminal — displays the live investigation event stream.
 *
 * Event types actually emitted by backlot_agent.py (_evt calls):
 *   INVESTIGATION_STARTED, DISCOVERING_GRAFANA_CAPABILITIES, GRAFANA_MCP_CONNECTED,
 *   DATASOURCES_DISCOVERED, QUERYING_TELEMETRY, TOOL_CALL_STARTED, TOOL_CALL_SUCCEEDED,
 *   TOOL_CALL_FAILED, TELEMETRY_RECEIVED, EVALUATING_EVIDENCE, RUNNING_CPM_ENGINE,
 *   CPM_RESULT, INVESTIGATION_COMPLETE, INVESTIGATION_INCOMPLETE, ERROR
 *
 * Previously dead branches checked 'EVIDENCE', 'HYPOTHESIS', 'PLAN', 'TOOL_CALL' —
 * none of which are ever emitted. These have been replaced with the real event types above.
 */

function formatEventMessage(ev) {
  const raw = ev.message || '';

  // INVESTIGATION_STARTED
  if (ev.type === 'INVESTIGATION_STARTED') {
    if (raw.includes('Investigate Stage 4 tracking packet drop ratio')) {
      return 'Investigating the camera tracking problem';
    }
    return raw || 'Investigation started';
  }

  // DISCOVERING_GRAFANA_CAPABILITIES
  if (ev.type === 'DISCOVERING_GRAFANA_CAPABILITIES') {
    if (raw.includes('Querying Grafana for available datasources')) {
      return 'Checking production data in Grafana...';
    }
    return raw || 'Discovering Grafana capabilities...';
  }

  // GRAFANA_MCP_CONNECTED
  if (ev.type === 'GRAFANA_MCP_CONNECTED') {
    return 'Grafana MCP session established';
  }

  // DATASOURCES_DISCOVERED
  if (ev.type === 'DATASOURCES_DISCOVERED') {
    const count = ev.datasources ? ev.datasources.length : '';
    return count ? `Production data sources found (${count})` : raw || 'Datasources discovered';
  }

  // QUERYING_TELEMETRY
  if (ev.type === 'QUERYING_TELEMETRY') {
    return 'ADK agent launching Gemini-driven investigation...';
  }

  // TOOL_CALL_STARTED
  if (ev.type === 'TOOL_CALL_STARTED') {
    const tool = ev.tool || '';
    if (tool.includes('query_prometheus')) return `Querying Prometheus telemetry: ${ev.args?.expr || tool}`;
    if (tool.includes('query_loki')) return `Querying Loki logs`;
    if (tool.includes('list_datasources')) return 'Listing Grafana datasources';
    return raw || `Calling ${tool}`;
  }

  // TOOL_CALL_SUCCEEDED
  if (ev.type === 'TOOL_CALL_SUCCEEDED') {
    const tool = ev.tool || '';
    if (tool.includes('query_prometheus')) return `Prometheus data received`;
    if (tool.includes('query_loki')) return `Loki logs received`;
    return raw || `${tool} succeeded`;
  }

  // TOOL_CALL_FAILED
  if (ev.type === 'TOOL_CALL_FAILED') {
    const tool = ev.tool || '';
    return `${tool || 'Tool'} returned no data: ${ev.detail || ''}`;
  }

  // TELEMETRY_RECEIVED
  if (ev.type === 'TELEMETRY_RECEIVED') {
    const tool = ev.tool || ev.source || 'grafana_mcp';
    if (tool.includes('prometheus')) return 'Prometheus telemetry evidence captured';
    if (tool.includes('loki')) return 'Loki log evidence captured';
    return `Evidence captured from ${tool}`;
  }

  // EVALUATING_EVIDENCE
  if (ev.type === 'EVALUATING_EVIDENCE') {
    return 'Agent completed tool execution — evaluating evidence';
  }

  // RUNNING_CPM_ENGINE
  if (ev.type === 'RUNNING_CPM_ENGINE') {
    return 'Running deterministic Causal Path + financial model...';
  }

  // CPM_RESULT
  if (ev.type === 'CPM_RESULT') {
    return 'Causal graph and financial blast radius calculated';
  }

  // INVESTIGATION_COMPLETE
  if (ev.type === 'INVESTIGATION_COMPLETE') {
    return 'Phase 1 investigation complete';
  }

  // INVESTIGATION_INCOMPLETE (tool limit reached)
  if (ev.type === 'INVESTIGATION_INCOMPLETE') {
    return `Investigation stopped: tool limit reached (${ev.tool_calls_made || '?'}/${ev.limit || 5} calls)`;
  }

  // ERROR
  if (ev.type === 'ERROR') {
    const code = ev.code || 'ERROR';
    const msg = ev.message || '';
    if (code === 'MCP_UNAVAILABLE') return `Grafana MCP unavailable: ${msg}`;
    if (code === 'MCP_AUTH_ERROR') return `Grafana auth failed: ${msg}`;
    if (code === 'MCP_TIMEOUT') return 'Grafana MCP timed out';
    return `Error [${code}]: ${msg}`;
  }

  // Fallback for any future event types
  return raw || ev.type;
}

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
            const msg = formatEventMessage(ev);
            return (
              <li key={i} className={`term-line ${(ev.type || '').toLowerCase()}`}>
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
