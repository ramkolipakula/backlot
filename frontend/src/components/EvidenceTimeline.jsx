/**
 * EvidenceTimeline — derives evidence rows from live SSE events.
 *
 * Props:
 *   events: array of SSE event objects received from the investigation stream.
 *           Each event has: { type, timestamp, tool?, source?, evidence?, message?, ... }
 *
 * Rendered rows are sourced exclusively from TELEMETRY_RECEIVED and
 * TOOL_CALL_SUCCEEDED events passed in from App.jsx — no literal demo
 * values exist in this component.
 */
import { formatTime } from './utils';

function buildEvidenceRows(events) {
  const rows = [];

  for (const ev of events) {
    if (ev.type === 'TELEMETRY_RECEIVED') {
      // TELEMETRY_RECEIVED carries: { source, tool, evidence: { data: [...], ... } }
      const tool = ev.tool || ev.source || 'grafana_mcp';
      const timestamp = ev.timestamp;

      // Summarize the evidence payload
      let summary = '';
      let detail = '';

      const evidence = ev.evidence;
      if (evidence && typeof evidence === 'object') {
        // MCP Prometheus response: { data: [ { metric: {...}, values: [[ts, val], ...] } ] }
        const data = evidence.data;
        if (Array.isArray(data) && data.length > 0) {
          const series = data[0];
          const metricName =
            series.metric?.__name__ ||
            Object.entries(series.metric || {})
              .filter(([k]) => k !== '__name__')
              .map(([k, v]) => `${k}="${v}"`)
              .join(', ') ||
            'metric';

          const values = series.values || series.value;
          let latestVal = '';
          if (Array.isArray(values) && values.length > 0) {
            const last = values[values.length - 1];
            latestVal = Array.isArray(last) ? last[1] : String(last);
          }

          summary = metricName.toUpperCase().replace(/_/g, ' ');
          detail = latestVal ? `Latest value: ${latestVal}` : `${data.length} series returned`;
        } else if (Array.isArray(evidence)) {
          // Loki log lines
          summary = 'LOG LINES RECEIVED';
          detail = `${evidence.length} log entr${evidence.length === 1 ? 'y' : 'ies'}`;
        } else {
          summary = tool.replace(/_/g, ' ').toUpperCase();
          detail = 'Evidence captured';
        }
      } else {
        summary = tool.replace(/_/g, ' ').toUpperCase();
        detail = 'Evidence captured';
      }

      rows.push({
        id: `telemetry-${rows.length}`,
        timestamp,
        title: summary,
        subtitle: tool,
        value: detail,
        highlight: false,
      });
    } else if (ev.type === 'TOOL_CALL_SUCCEEDED') {
      // Emit a lighter row for successful non-telemetry tools
      rows.push({
        id: `tool-${rows.length}`,
        timestamp: ev.timestamp,
        title: (ev.tool || 'TOOL').replace(/_/g, ' ').toUpperCase(),
        subtitle: ev.message || 'Tool call succeeded',
        value: '✓',
        highlight: false,
      });
    } else if (ev.type === 'INVESTIGATION_COMPLETE') {
      rows.push({
        id: `complete-${rows.length}`,
        timestamp: ev.timestamp,
        title: 'INVESTIGATION COMPLETE',
        subtitle: 'All evidence collected',
        value: 'DONE',
        highlight: true,
      });
    }
  }

  return rows;
}

export default function EvidenceTimeline({ events = [] }) {
  const rows = buildEvidenceRows(events);

  return (
    <div className="panel evidence-panel">
      <div className="panel-header">
        <h2>EVIDENCE</h2>
      </div>
      <div className="edl-list">
        {rows.length === 0 ? (
          <div className="edl-empty">
            <div className="edl-empty-icon">◌</div>
            <div className="edl-empty-label">
              {events.length === 0
                ? 'AWAITING INVESTIGATION...'
                : 'COLLECTING TELEMETRY...'}
            </div>
          </div>
        ) : (
          rows.map((row) => (
            <div key={row.id} className={`edl-row${row.highlight ? ' highlight' : ''}`}>
              <div className="edl-time">
                {row.timestamp ? formatTime(row.timestamp) : 'SYS'}
              </div>
              <div className="edl-desc">
                <div className="edl-title">{row.title}</div>
                {row.subtitle && (
                  <div className="panel-subtitle">{row.subtitle}</div>
                )}
                {row.value && (
                  <div className="edl-val">{row.value}</div>
                )}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
