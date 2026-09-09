import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.engine.cpm import ProductionCPMEngine
from backend.models.cpm import ManualIncidentRequest, ProductionParameters, ManualObservation

def test_manual_mode():
    params = ProductionParameters(
        stage_idle_cost_per_minute=1000,
        crew_ot_surcharge_per_minute=500,
        actor_hard_out_utc="2026-09-08T18:30:00Z",
        actor_penalty=50000,
        current_delay_minutes=50,
        estimated_recovery_minutes=30
    )
    req = ManualIncidentRequest(
        production_name="Test Prod",
        scene="Test Scene",
        stage="Test Stage",
        incident_time_utc="2026-09-08T14:22:00Z",
        description="Manual test description",
        observations=[ManualObservation(description="Test obs", severity="High", timestamp="14:22")],
        production_parameters=params
    )
    
    engine = ProductionCPMEngine(
        idle_cost=params.stage_idle_cost_per_minute,
        overtime_surcharge=params.crew_ot_surcharge_per_minute,
        actor_penalty=params.actor_penalty
    )
    res = engine.process_manual_incident(req)
    
    # 50 min delay -> baseline total blast radius
    assert res.baseline.delay_minutes == 50
    assert res.baseline.idle_cost_usd == 50 * 1000
    assert res.baseline.overtime_surcharge_usd == 50 * 500
    assert res.baseline.total_blast_radius_usd == 75000
    
    # recovery is 30 mins
    assert len(res.interventions) == 1
    i = res.interventions[0]
    assert i.recovery_minutes == 30
    assert i.remaining_delay_minutes == 30
    assert i.idle_waste_usd == 30 * 1000
    assert i.overtime_surcharge_usd == 30 * 500
    assert i.total_usd == 45000
    assert i.net_savings_usd == 75000 - 45000
    
    print("Manual mode tests passed!")

if __name__ == "__main__":
    test_manual_mode()
