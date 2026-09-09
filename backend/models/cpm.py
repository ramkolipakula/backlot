from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class Evidence(BaseModel):
    source: str
    datasource_uid: str
    query: str
    timestamp: str
    value: Optional[str] = None
    line: Optional[str] = None

class RootCause(BaseModel):
    entity: str
    fault_type: str
    confidence: str
    evidence: List[Evidence]
    # True  → passed evidence contains the expected tracking/packet-drop pattern.
    # False → passed evidence contradicts the root-cause pattern.
    # None  → no evidence was passed (baseline/demo path); conclusion unchanged.
    evidence_supports_conclusion: Optional[bool] = None

class CausalNode(BaseModel):
    id: str
    description: str
    duration_minutes: int
    is_rejected_hypothesis: bool = False

class CausalEdge(BaseModel):
    source: str
    target: str
    description: Optional[str] = None

class CriticalPathResult(BaseModel):
    nodes: List[CausalNode]
    edges: List[CausalEdge]
    critical_path: List[str]

class FinancialModel(BaseModel):
    delay_minutes: int
    projected_wrap_utc: str
    actor_hard_out_utc: str
    actor_hard_out_breached: bool
    idle_cost_usd: int
    overtime_surcharge_usd: int
    penalty_usd: int
    total_blast_radius_usd: int

class InterventionResult(BaseModel):
    id: str
    name: str
    recovery_minutes: int
    remaining_delay_minutes: int
    projected_wrap_utc: str
    actor_hard_out_utc: str
    actor_hard_out_breached: bool
    idle_waste_usd: int
    overtime_surcharge_usd: int
    direct_implementation_fee_usd: int
    penalty_usd: int
    total_usd: int
    net_savings_usd: int
    rank: int
    recommended: bool

class Recommendation(BaseModel):
    intervention_id: str
    reason: str

class InvestigationResult(BaseModel):
    incident_id: str
    incident_time_utc: str
    root_cause: RootCause
    causal_graph: CriticalPathResult
    baseline: FinancialModel
    interventions: List[InterventionResult]
    recommendation: Recommendation

class ManualObservation(BaseModel):
    description: str
    severity: str
    timestamp: str

class ProductionParameters(BaseModel):
    stage_idle_cost_per_minute: int
    crew_ot_surcharge_per_minute: int
    actor_hard_out_utc: str
    actor_penalty: int
    current_delay_minutes: int
    estimated_recovery_minutes: int

class ManualIncidentRequest(BaseModel):
    production_name: str
    scene: str
    stage: str
    incident_time_utc: str
    description: str
    observations: List[ManualObservation]
    production_parameters: ProductionParameters
