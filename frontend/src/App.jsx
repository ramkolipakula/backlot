import { useState, useEffect } from 'react';
import './index.css';

function App() {
  const [query, setQuery] = useState('Investigate Stage 4 tracking packet drop ratio');
  const [events, setEvents] = useState([]);
  const [status, setStatus] = useState('IDLE');
  const [evidence, setEvidence] = useState(null);
  const [error, setError] = useState(null);

  const startInvestigation = () => {
    setEvents([]);
    setEvidence(null);
    setError(null);
    setStatus('INVESTIGATING');

    const eventSource = new EventSource(`http://localhost:8000/api/stream?query=${encodeURIComponent(query)}`);

    eventSource.onmessage = (e) => {
      const data = JSON.parse(e.data);
      setEvents((prev) => [...prev, data]);

      if (data.type === 'ERROR') {
        setStatus('ERROR');
        setError(data);
        eventSource.close();
      } else if (data.type === 'INVESTIGATION_COMPLETE') {
        setStatus('COMPLETE');
        if (data.evidence) {
          setEvidence(data.evidence);
        }
        eventSource.close();
      }
    };

    eventSource.onerror = (e) => {
      setStatus('ERROR');
      setError({ message: 'SSE Connection Failed' });
      eventSource.close();
    };
  };

  return (
    <div className="container">
      <header>
        <h1>BACKLOT</h1>
        <h2>Causal Time Machine for Film & Virtual Production</h2>
      </header>

      <main>
        <div className="trigger-area">
          <input 
            type="text" 
            value={query} 
            onChange={(e) => setQuery(e.target.value)}
            disabled={status === 'INVESTIGATING'}
          />
          <button onClick={startInvestigation} disabled={status === 'INVESTIGATING'}>
            Trigger Investigation
          </button>
        </div>

        <div className="status-indicator">
          Status: <strong>{status}</strong>
        </div>

        {error && (
          <div className="error-box">
            <h3>Investigation Error</h3>
            <pre>{JSON.stringify(error, null, 2)}</pre>
          </div>
        )}

        <div className="investigation-area">
          <div className="terminal">
            <h3>Live Agent Activity</h3>
            <ul>
              {events.map((ev, i) => (
                <li key={i}>
                  <span className="timestamp">[{ev.timestamp ? ev.timestamp.split('T')[1].split('.')[0] : new Date().toISOString().split('T')[1].split('.')[0]}]</span>
                  <span className="event-type">{ev.type}</span>: 
                  <span className="event-msg">{ev.message || ev.tools || (ev.evidence && 'Evidence received')}</span>
                </li>
              ))}
              {status === 'INVESTIGATING' && <li className="blinking-cursor">_</li>}
            </ul>
          </div>

          <div className="evidence-area">
            <h3>Structured Evidence</h3>
            {evidence ? (
              <pre>{JSON.stringify(evidence, null, 2)}</pre>
            ) : (
              <div className="empty-evidence">No evidence yet...</div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}

export default App;
