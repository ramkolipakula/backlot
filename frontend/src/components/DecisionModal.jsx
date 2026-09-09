import { formatMoney, formatTime } from './utils';

export default function DecisionModal({ scenario, onCancel, onConfirm, isConfirming }) {
  const hardOutTime = new Date(scenario.actor_hard_out_utc);
  const wrapTime = new Date(scenario.projected_wrap_utc);
  const deltaMin = Math.round((hardOutTime - wrapTime) / 60000);

  const scenarioLabel =
    scenario.id === 'intervention-a' ? 'REPLACE THE TRACKING HARDWARE' :
    scenario.id === 'intervention-b' ? 'SWITCH TO BACKUP TRACKING' :
    'RESCHEDULE';

  const hardOutStatusLabel = scenario.actor_hard_out_breached
    ? 'BREACHED'
    : `PRESERVED · ${deltaMin} MIN BUFFER`;

  return (
    <div className="modal-overlay cinematic-fade-in" role="dialog" aria-modal="true" aria-labelledby="modal-heading">
      <div className="modal-card">
        <div className="modal-header">
          <div className="modal-title" id="modal-heading">APPROVE THIS DECISION</div>
          <div className="modal-scenario-name">{scenarioLabel}</div>
        </div>

        <div className="modal-table">
          <div className="modal-row">
            <span className="ml">Expected wrap</span>
            <span className="mr">{formatTime(scenario.projected_wrap_utc)}</span>
          </div>
          <div className="modal-row">
            <span className="ml">Actor must leave</span>
            <span className="mr">18:30</span>
          </div>
          <div className="modal-row">
            <span className="ml">Total cost</span>
            <span className="mr warning-val">{formatMoney(scenario.total_usd)}</span>
          </div>
          <div className="modal-row highlight-row">
            <span className="ml">Money saved</span>
            <span className="mr success-val">{formatMoney(scenario.net_savings_usd)}</span>
          </div>
        </div>

        <div className="modal-note">
          This decision will be recorded in Grafana.
        </div>

        <div className="modal-actions">
          <button
            className="modal-cancel-btn"
            onClick={onCancel}
            disabled={isConfirming}
          >
            CANCEL
          </button>
          <button
            className="modal-confirm-btn"
            onClick={onConfirm}
            disabled={isConfirming}
          >
            {isConfirming ? 'COMMITTING...' : 'APPROVE DECISION'}
          </button>
        </div>
      </div>
    </div>
  );
}
