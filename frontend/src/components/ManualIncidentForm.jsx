import { useState } from 'react';

export default function ManualIncidentForm({ onSubmit }) {
  const [formData, setFormData] = useState({
    production_name: '',
    scene: '',
    stage: '',
    incident_time_utc: new Date().toISOString().slice(0, 16) + 'Z',
    description: '',
    observations: [{ description: '', severity: 'High', timestamp: new Date().toISOString().slice(11, 16) }],
    production_parameters: {
      stage_idle_cost_per_minute: 450,
      crew_ot_surcharge_per_minute: 225,
      actor_hard_out_utc: new Date(new Date().getTime() + 4 * 60 * 60 * 1000).toISOString().slice(0, 16) + 'Z',
      actor_penalty: 50000,
      current_delay_minutes: 38,
      estimated_recovery_minutes: 60
    }
  });

  const handleObsChange = (index, field, value) => {
    const newObs = [...formData.observations];
    newObs[index][field] = value;
    setFormData({ ...formData, observations: newObs });
  };

  const addObservation = () => {
    setFormData({
      ...formData,
      observations: [
        ...formData.observations,
        { description: '', severity: 'High', timestamp: new Date().toISOString().slice(11, 16) }
      ]
    });
  };

  const handleParamChange = (field, value) => {
    setFormData({
      ...formData,
      production_parameters: {
        ...formData.production_parameters,
        [field]: value
      }
    });
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    // Format timestamps appropriately
    const payload = { ...formData };
    if (!payload.incident_time_utc.endsWith('Z')) payload.incident_time_utc += 'Z';
    if (!payload.production_parameters.actor_hard_out_utc.endsWith('Z')) {
      payload.production_parameters.actor_hard_out_utc += 'Z';
    }
    
    // Ensure numbers are parsed
    payload.production_parameters.stage_idle_cost_per_minute = parseInt(payload.production_parameters.stage_idle_cost_per_minute, 10);
    payload.production_parameters.crew_ot_surcharge_per_minute = parseInt(payload.production_parameters.crew_ot_surcharge_per_minute, 10);
    payload.production_parameters.actor_penalty = parseInt(payload.production_parameters.actor_penalty, 10);
    payload.production_parameters.current_delay_minutes = parseInt(payload.production_parameters.current_delay_minutes, 10);
    payload.production_parameters.estimated_recovery_minutes = parseInt(payload.production_parameters.estimated_recovery_minutes, 10);
    
    onSubmit(payload);
  };

  return (
    <div className="manual-incident-form">
      <div className="hero-top-bar" style={{ marginBottom: '20px' }}>
        <span className="app-title">NEW INCIDENT</span>
        <span className="app-subtitle">Give BACKLOT the facts. It will reconstruct what happened.</span>
      </div>

      <form onSubmit={handleSubmit}>
        <div className="form-section">
          <h3>INCIDENT</h3>
          <div className="form-grid">
            <label>
              Production Name
              <input required value={formData.production_name} onChange={e => setFormData({...formData, production_name: e.target.value})} placeholder="e.g. The Citadel" />
            </label>
            <label>
              Scene
              <input required value={formData.scene} onChange={e => setFormData({...formData, scene: e.target.value})} placeholder="e.g. Scene 24" />
            </label>
            <label>
              Stage / Location
              <input required value={formData.stage} onChange={e => setFormData({...formData, stage: e.target.value})} placeholder="e.g. Stage 04" />
            </label>
            <label>
              Incident Date & Time (UTC)
              <input type="datetime-local" required value={formData.incident_time_utc.slice(0, 16)} onChange={e => setFormData({...formData, incident_time_utc: e.target.value})} />
            </label>
            <label style={{ gridColumn: '1 / -1' }}>
              Description
              <textarea required value={formData.description} onChange={e => setFormData({...formData, description: e.target.value})} rows="3" placeholder="Describe what happened..."></textarea>
            </label>
          </div>
        </div>

        <div className="form-section">
          <h3>SIGNALS / OBSERVATIONS</h3>
          {formData.observations.map((obs, idx) => (
            <div key={idx} className="observation-row">
              <input required value={obs.description} onChange={e => handleObsChange(idx, 'description', e.target.value)} placeholder="Observation (e.g. Camera tracking signal dropped)" />
              <select value={obs.severity} onChange={e => handleObsChange(idx, 'severity', e.target.value)}>
                <option>High</option>
                <option>Medium</option>
                <option>Low</option>
              </select>
              <input type="time" required value={obs.timestamp} onChange={e => handleObsChange(idx, 'timestamp', e.target.value)} />
            </div>
          ))}
          <button type="button" onClick={addObservation} className="add-btn">+ ADD OBSERVATION</button>
        </div>

        <div className="form-section">
          <h3>PRODUCTION IMPACT</h3>
          <div className="form-grid">
            <label>
              Stage idle cost / min ($)
              <input type="number" required value={formData.production_parameters.stage_idle_cost_per_minute} onChange={e => handleParamChange('stage_idle_cost_per_minute', e.target.value)} />
            </label>
            <label>
              Crew OT surcharge / min ($)
              <input type="number" required value={formData.production_parameters.crew_ot_surcharge_per_minute} onChange={e => handleParamChange('crew_ot_surcharge_per_minute', e.target.value)} />
            </label>
            <label>
              Actor Penalty ($)
              <input type="number" required value={formData.production_parameters.actor_penalty} onChange={e => handleParamChange('actor_penalty', e.target.value)} />
            </label>
            <label>
              Actor Hard-out (UTC)
              <input type="datetime-local" required value={formData.production_parameters.actor_hard_out_utc.slice(0, 16)} onChange={e => handleParamChange('actor_hard_out_utc', e.target.value)} />
            </label>
            <label>
              Current Delay (minutes)
              <input type="number" required value={formData.production_parameters.current_delay_minutes} onChange={e => handleParamChange('current_delay_minutes', e.target.value)} />
            </label>
            <label>
              Estimated Recovery (minutes)
              <input type="number" required value={formData.production_parameters.estimated_recovery_minutes} onChange={e => handleParamChange('estimated_recovery_minutes', e.target.value)} />
            </label>
          </div>
        </div>

        <button type="submit" className="submit-btn">START INVESTIGATION</button>
      </form>
      <style dangerouslySetInnerHTML={{__html: `
        .manual-incident-form { padding: 20px; color: var(--text-primary); max-width: 800px; margin: 0 auto; }
        .form-section { background: rgba(0,0,0,0.4); border: 1px solid var(--border-color); padding: 20px; margin-bottom: 20px; }
        .form-section h3 { margin-top: 0; color: var(--brand-red); font-size: 0.9rem; letter-spacing: 2px; }
        .form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 15px; }
        label { display: flex; flex-direction: column; font-size: 0.8rem; font-family: var(--font-mono); color: var(--text-secondary); }
        input, select, textarea { margin-top: 5px; padding: 10px; background: rgba(20,20,20,0.8); border: 1px solid var(--border-color); color: var(--text-primary); font-family: var(--font-mono); }
        input:focus, select:focus, textarea:focus { outline: 1px solid var(--brand-red); border-color: var(--brand-red); }
        .observation-row { display: grid; grid-template-columns: 1fr auto auto; gap: 10px; margin-bottom: 10px; }
        .add-btn { background: transparent; border: 1px solid var(--brand-red); color: var(--brand-red); padding: 5px 10px; font-family: var(--font-mono); cursor: pointer; font-size: 0.8rem; margin-top: 5px;}
        .add-btn:hover { background: rgba(255, 60, 60, 0.1); }
        .submit-btn { width: 100%; background: var(--brand-red); color: #fff; border: none; padding: 15px; font-family: var(--font-header); font-size: 1.2rem; cursor: pointer; letter-spacing: 2px; }
        .submit-btn:hover { background: #ff5555; }
      `}} />
    </div>
  );
}
