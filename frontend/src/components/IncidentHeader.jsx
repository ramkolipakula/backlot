import { formatTime } from './utils';

export default function IncidentHeader({ incidentTimeStr, sceneOverride, productionOverride, stageOverride }) {
  return (
    <div className="incident-hero">
      <div className="hero-top-bar">
        <span className="app-title">BACKLOT</span>
        <span className="app-subtitle">LIVE INVESTIGATION</span>
      </div>
      
      <div className="hero-main">
        <div className="scene-info">
          <div className="scene-number">{sceneOverride ? sceneOverride.toUpperCase() : "SCENE 24"}</div>
          <div className="scene-name">{productionOverride ? productionOverride.toUpperCase() : "THE CITADEL INFILTRATION"}</div>
        </div>
        
        <div className="stage-info">
          {stageOverride ? stageOverride.toUpperCase() : "STAGE 04"} &middot; VIRTUAL PRODUCTION
        </div>
        
        <div className="incident-status-banner">
          <span className="time">{formatTime(incidentTimeStr)} UTC</span>
          <span className="status-badge alert">PRODUCTION HALTED</span>
        </div>
      </div>
    </div>
  );
}
