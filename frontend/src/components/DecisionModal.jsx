import { formatMoney, formatTime } from './utils';

export default function DecisionModal({ scenario, onCancel, onConfirm, isConfirming }) {
  const hardOutTime = new Date(scenario.actor_hard_out_utc);
  const wrapTime = new Date(scenario.projected_wrap_utc);
  const deltaMin = Math.round((hardOutTime - wrapTime) / 60000);

  const scenarioLabel =
    scenario.id === 'intervention-a' ? 'HARDWARE SWAP' :
    scenario.id === 'intervention-b' ? 'TRACKING FAILOVER' :
    'ABANDON / RESCHEDULE';

  const hardOutStatusLabel = scenario.actor_hard_out_breached
    ? 'BREACHED'
    : `PRESERVED · ${deltaMin} MIN BUFFER`;

  return (
    <div className="modal-overlay cinematic-fade-in" role="dialog" aria-modal="true" aria-labelledby="modal-heading">
      <div className="modal-card">
        <div className="modal-header">
          <div className="modal-title" id="modal-heading">COMMIT COUNTERFACTUAL</div>
          <div className="modal-scenario-name">{scenarioLabel}</div>
        </div>

        <div className="modal-table">
          <div className="modal-row">
            <span className="ml">Projected wrap</span>
            <span className="mr">{formatTime(scenario.projected_wrap_utc)}</span>
          </div>
          <div className="modal-row">
            <span className="ml">Actor hard-out</span>
            <span className="mr">18:30</span>
          </div>
          <div className="modal-row">
            <span className="ml">Financial exposure</span>
            <span className="mr warning-val">{formatMoney(scenario.total_usd)}</span>
          </div>
          <div className="modal-row highlight-row">
            <span className="ml">Expected savings</span>
            <span className="mr success-val">{formatMoney(scenario.net_savings_usd)}</span>
          </div>
        </div>

        <div className="modal-note">
          This action will write an approval annotation to Grafana.
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
