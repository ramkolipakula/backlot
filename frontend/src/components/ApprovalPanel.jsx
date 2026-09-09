import { useState, useRef, useEffect, useCallback } from 'react';
import DecisionModal from './DecisionModal';
import { formatTime } from './utils';

export default function ApprovalPanel({ scenario, incidentData }) {
  const [approvalState, setApprovalState] = useState('idle');
  const [showModal, setShowModal] = useState(false);
  const [isConfirming, setIsConfirming] = useState(false);
  const [successData, setSuccessData] = useState(null);
  const [errorMessage, setErrorMessage] = useState('');
  const inFlight = useRef(false);

  useEffect(() => {
    setApprovalState('idle');
    setShowModal(false);
    setSuccessData(null);
    setErrorMessage('');
    inFlight.current = false;
  }, [scenario?.id]);

  const isIntervention = scenario && scenario.id && scenario.id.startsWith('intervention-');

  const handleApproveClick = () => {
    if (!isIntervention || approvalState === 'recording') return;
    setShowModal(true);
  };

  const handleCancel = () => {
    setShowModal(false);
  };

  const handleConfirm = useCallback(async () => {
    if (inFlight.current) return;
    inFlight.current = true;
    setIsConfirming(true);
    setShowModal(false);
    setApprovalState('recording');

    try {
      const res = await fetch('http://localhost:8000/api/approve', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ scenario_id: scenario.id }),
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.detail || `HTTP ${res.status}`);
      }

      setSuccessData(data);
      setApprovalState('success');
    } catch (err) {
      setErrorMessage(err.message || 'Unknown error');
      setApprovalState('failure');
    } finally {
      setIsConfirming(false);
      inFlight.current = false;
    }
  }, [scenario]);

  const handleRetry = () => {
    setApprovalState('idle');
    setErrorMessage('');
  };

  if (!isIntervention) return null;

  return (
    <>
      {showModal && (
        <DecisionModal
          scenario={scenario}
          onCancel={handleCancel}
          onConfirm={handleConfirm}
          isConfirming={isConfirming}
        />
      )}

      {approvalState === 'idle' && (
        <button className="approve-action-btn cinematic-btn" onClick={handleApproveClick}>
          APPROVE
        </button>
      )}

      {approvalState === 'recording' && (
        <div className="approval-status recording">
          <div className="spinner"></div>
          WRITING ANNOTATION...
        </div>
      )}

      {approvalState === 'success' && successData && (
        <div className="approval-status success cinematic-fade-in">
          <div className="status-header">DECISION COMMITTED</div>
          <div className="status-sub">GRAFANA ANNOTATION WRITTEN</div>
          <div className="status-time">{formatTime(new Date().toISOString())} UTC</div>
        </div>
      )}

      {approvalState === 'failure' && (
        <div className="approval-status failure">
          <div className="status-header">RECORDING FAILED</div>
          <div className="status-sub">{errorMessage}</div>
          <button className="retry-btn" onClick={handleRetry}>RETRY</button>
        </div>
      )}
    </>
  );
}
