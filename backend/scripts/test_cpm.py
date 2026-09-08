import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from backend.engine.cpm import ProductionCPMEngine
from backend.models.cpm import CausalNode, CausalEdge

def test_deterministic_cpm():
    engine = ProductionCPMEngine()

    print("Running CPM Engine Tests...")

    # 1. DAG validation succeeds
    # 3. Canonical incident produces 195 minute baseline delay
    # 4. Baseline total is exactly $181,625
    # 5. Intervention A total is exactly $103,125
    # 6. Intervention B total is exactly $14,700
    # 7. Intervention C total is exactly $87,100
    # 8. Intervention B ranks #1
    # 9. Intervention B savings are exactly $166,925
    # 10. Actor hard-out is breached in baseline
    # 11. Actor hard-out is breached in A
    # 12. Actor hard-out is preserved in B
    # 13. Actor hard-out is preserved in C
    # 14. Same input produces identical output across repeated runs

    result1 = engine.process_incident()
    result2 = engine.process_incident()

    assert result1.model_dump() == result2.model_dump(), "Test 14 Failed: Outputs are not identical across runs"
    print("Test 14 (Determinism): PASS")

    # Baseline tests
    assert result1.baseline.delay_minutes == 195, f"Expected baseline delay 195, got {result1.baseline.delay_minutes}"
    print("Test 3 (Baseline Delay): PASS")

    assert result1.baseline.total_blast_radius_usd == 181625, f"Expected baseline cost 181625, got {result1.baseline.total_blast_radius_usd}"
    print("Test 4 (Baseline Cost): PASS")

    assert result1.baseline.actor_hard_out_breached is True, "Expected actor hard-out breached in baseline"
    print("Test 10 (Baseline Breach): PASS")

    # Interventions tests
    inv_a = next(i for i in result1.interventions if i.id == "intervention-a")
    inv_b = next(i for i in result1.interventions if i.id == "intervention-b")
    inv_c = next(i for i in result1.interventions if i.id == "intervention-c")

    assert inv_a.total_usd == 103125, f"Expected A total 103125, got {inv_a.total_usd}"
    print("Test 5 (Intervention A Cost): PASS")
    assert inv_a.actor_hard_out_breached is True, "Expected actor hard-out breached in A"
    print("Test 11 (Intervention A Breach): PASS")

    assert inv_b.total_usd == 14700, f"Expected B total 14700, got {inv_b.total_usd}"
    print("Test 6 (Intervention B Cost): PASS")
    assert inv_b.actor_hard_out_breached is False, "Expected actor hard-out preserved in B"
    print("Test 12 (Intervention B Preserve): PASS")
    assert inv_b.rank == 1, f"Expected B to be rank 1, got {inv_b.rank}"
    print("Test 8 (Intervention B Rank): PASS")
    assert inv_b.net_savings_usd == 166925, f"Expected B savings 166925, got {inv_b.net_savings_usd}"
    print("Test 9 (Intervention B Savings): PASS")

    assert inv_c.total_usd == 87100, f"Expected C total 87100, got {inv_c.total_usd}"
    print("Test 7 (Intervention C Cost): PASS")
    assert inv_c.actor_hard_out_breached is False, "Expected actor hard-out preserved in C"
    print("Test 13 (Intervention C Preserve): PASS")

    # 1. DAG validation
    # 2. Cyclic graph is rejected
    cyclic_nodes = [CausalNode(id="A", description="A", duration_minutes=0), CausalNode(id="B", description="B", duration_minutes=0)]
    cyclic_edges = [CausalEdge(source="A", target="B"), CausalEdge(source="B", target="A")]
    
    try:
        engine.validate_graph(cyclic_nodes, cyclic_edges)
        assert False, "Test 2 Failed: Cyclic graph was not rejected"
    except ValueError:
        print("Test 1 (DAG Validations) & Test 2 (Cyclic Graph Rejection): PASS")

    print("ALL TESTS PASSED.")

if __name__ == "__main__":
    test_deterministic_cpm()
