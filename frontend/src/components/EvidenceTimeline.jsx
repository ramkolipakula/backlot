export default function EvidenceTimeline() {
  return (
    <div className="panel evidence-panel">
      <div className="panel-header">
        <h2>EVIDENCE</h2>
      </div>
      <div className="edl-list">
        <div className="edl-row">
          <div className="edl-time">14:15:00</div>
          <div className="edl-desc">
            <div className="edl-title">CAMERA TRACKING SIGNAL DROPPED</div>
            <div className="panel-subtitle">Optical tracking packet loss</div>
            <div className="edl-val">0.184</div>
          </div>
        </div>
        <div className="edl-row">
          <div className="edl-time">14:17:30</div>
          <div className="edl-desc">
            <div className="edl-title">CAMERA POSITION BECAME UNSTABLE</div>
            <div className="panel-subtitle">Unreal Engine tracking jitter</div>
            <div className="edl-val">14.2 ms</div>
          </div>
        </div>
        <div className="edl-row">
          <div className="edl-time">14:18:00</div>
          <div className="edl-desc">
            <div className="edl-title">CAMERA RECORDING STOPPED</div>
            <div className="edl-val">OFF</div>
          </div>
        </div>
        <div className="edl-row">
          <div className="edl-time">14:20:00</div>
          <div className="edl-desc">
            <div className="edl-title">FOOTAGE BACKUP NEARLY FULL</div>
            <div className="panel-subtitle">DIT ingest buffer</div>
            <div className="edl-val">98%</div>
          </div>
        </div>
        <div className="edl-row highlight">
          <div className="edl-time">14:22:00</div>
          <div className="edl-desc">
            <div className="edl-title">PRODUCTION</div>
            <div className="edl-val">HALTED</div>
          </div>
        </div>
      </div>
    </div>
  );
}
