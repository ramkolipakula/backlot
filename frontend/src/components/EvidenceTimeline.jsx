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
            <div className="edl-title">TRACKING PACKET DROP</div>
            <div className="edl-val">0.184</div>
          </div>
        </div>
        <div className="edl-row">
          <div className="edl-time">14:17:30</div>
          <div className="edl-desc">
            <div className="edl-title">UE5 FRUSTUM JITTER</div>
            <div className="edl-val">14.2 ms</div>
          </div>
        </div>
        <div className="edl-row">
          <div className="edl-time">14:18:00</div>
          <div className="edl-desc">
            <div className="edl-title">CAMERA RECORDING</div>
            <div className="edl-val">OFF</div>
          </div>
        </div>
        <div className="edl-row">
          <div className="edl-time">14:20:00</div>
          <div className="edl-desc">
            <div className="edl-title">DIT INGEST BUFFER</div>
            <div className="edl-val">98%</div>
          </div>
        </div>
        <div className="edl-row highlight">
          <div className="edl-time">14:22:00</div>
          <div className="edl-desc">
            <div className="edl-title">STAGE</div>
            <div className="edl-val">HALTED</div>
          </div>
        </div>
      </div>
    </div>
  );
}
