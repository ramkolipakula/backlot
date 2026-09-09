import { formatMoney } from './utils';
import ApprovalPanel from './ApprovalPanel';

export default function FinancialBlastRadius({ activeData, selectedScenario, incidentData }) {
  const isBaseline = selectedScenario === 'baseline';
  
  return (
    <div className="panel financial-panel">
      <div className="panel-header">
        <h2>COST OF THE DELAY</h2>
      </div>
      
      <div className="fin-blast-total">
        {formatMoney(activeData.total_usd || activeData.total_blast_radius_usd)}
      </div>

      <div className="fin-line-items">
        <div className="fin-row">
          <span className="fin-label">STAGE DELAY</span>
          <span className="fin-value">{formatMoney(activeData.idle_waste_usd ?? activeData.idle_cost_usd)}</span>
        </div>
        <div className="fin-row">
          <span className="fin-label">OVERTIME</span>
          <span className="fin-value">{formatMoney(activeData.overtime_surcharge_usd)}</span>
        </div>
        <div className="fin-row">
          <span className="fin-label">IMPLEMENTATION</span>
          <span className="fin-value">{formatMoney(activeData.direct_implementation_fee_usd || 0)}</span>
        </div>
        <div className="fin-row">
          <span className="fin-label">PENALTY</span>
          <span className="fin-value">{formatMoney(activeData.penalty_usd)}</span>
        </div>
      </div>

      <div className="fin-savings-row">
        <span className="fin-label">SAVED VS. DOING NOTHING</span>
        <span className="fin-value-large savings-val">
          {isBaseline ? '$0' : `+${formatMoney(activeData.net_savings_usd)}`}
        </span>
      </div>

      <div className="approval-wrapper">
        <ApprovalPanel scenario={activeData} incidentData={incidentData} />
      </div>
    </div>
  );
}
