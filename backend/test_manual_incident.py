import sys
import os

# Add parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.engine.cpm import ProductionCPMEngine

def test_demo_mode():
    engine = ProductionCPMEngine()
    res = engine.process_incident()
    assert res.baseline.total_blast_radius_usd == 181625, f"Baseline changed: {res.baseline.total_blast_radius_usd}"
    
    a = next(i for i in res.interventions if i.id == "intervention-a")
    assert a.total_usd == 103125, "A total changed"
    assert a.net_savings_usd == 78500, "A savings changed"
    
    b = next(i for i in res.interventions if i.id == "intervention-b")
    assert b.total_usd == 14700, "B total changed"
    assert b.net_savings_usd == 166925, "B savings changed"
    
    c = next(i for i in res.interventions if i.id == "intervention-c")
    assert c.total_usd == 87100, "C total changed"
    assert c.net_savings_usd == 94525, "C savings changed"
    
    assert res.incident_time_utc == "2026-09-08T14:22:00Z"
    
    print("Demo mode tests passed!")

if __name__ == "__main__":
    test_demo_mode()
