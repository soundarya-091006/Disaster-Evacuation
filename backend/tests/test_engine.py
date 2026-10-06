"""
TwinEvac - Verification & Engine Test Suite
Tests graph loading, BPR travel time, simulation steps, What-If evaluation, and predictive horizons.
"""

import os
import sys
from pathlib import Path

# Ensure backend directory is in python path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.core.graph_manager import GraphManager
from app.engine.simulation import EvacuationSimulation
from app.engine.what_if_engine import WhatIfEngine
from app.schemas.models import WhatIfScenario


def test_graph_manager():
    print("Testing GraphManager initialization...")
    gm = GraphManager()
    assert len(gm.nodes_dict) > 10, f"Expected >10 nodes, got {len(gm.nodes_dict)}"
    assert len(gm.edges_dict) > 15, f"Expected >15 edges, got {len(gm.edges_dict)}"

    # Test BPR travel time
    t_time, speed, cong = gm.calculate_bpr_travel_time(
        distance_km=2.0, free_flow_speed_kmh=40.0, volume=100.0, capacity=1000.0
    )
    assert t_time >= 3.0, f"Expected valid travel time, got {t_time}"
    assert speed > 0, "Expected positive speed"
    print(f"[OK] GraphManager: {len(gm.nodes_dict)} nodes, {len(gm.edges_dict)} edges loaded successfully.")


def test_simulation_engine():
    print("Testing EvacuationSimulation engine...")
    sim = EvacuationSimulation()
    assert len(sim.shelters) >= 4, f"Expected at least 4 shelters, got {len(sim.shelters)}"
    assert len(sim.zones) >= 5, f"Expected at least 5 zones, got {len(sim.zones)}"
    assert len(sim.agents) > 0, f"Expected initial agents, got {len(sim.agents)}"

    initial_state = sim.get_current_state()
    assert initial_state.total_at_risk_population > 0
    assert initial_state.estimated_evacuation_time_minutes > 0
    assert "15m" in initial_state.predictions
    assert "30m" in initial_state.predictions
    assert "60m" in initial_state.predictions

    print("Stepping simulation forward 5 ticks...")
    for _ in range(5):
        state = sim.step()

    assert state.tick == 5
    assert state.elapsed_sim_minutes > 0
    print(f"[OK] Simulation stepped successfully: {state.elapsed_sim_minutes} sim mins elapsed, {state.total_evacuated} evacuated.")


def test_what_if_engine():
    print("Testing What-If Counterfactual simulation engine...")
    sim = EvacuationSimulation()
    what_if = WhatIfEngine(sim)

    # Test scenario: Closure of Shevapet Bazaar access road
    scenario = WhatIfScenario(
        scenario_id="TEST_SHEVAPET_CLOSURE",
        title="Test Shevapet Road Closure",
        closed_road_ids=["EDGE_4ROADS_SHEVAPET"],
        shelter_capacity_multipliers={"SHELTER_GMKMC": 0.8},
        hazard_radius_multiplier=1.2,
        evacuation_speed_multiplier=1.0
    )

    result = what_if.evaluate_scenario(scenario)
    assert result.baseline_eet_minutes > 0
    assert result.what_if_eet_minutes > 0
    assert result.recommendation != ""
    print(f"[OK] What-If Scenario Evaluated: Baseline EET={result.baseline_eet_minutes}m, What-If EET={result.what_if_eet_minutes}m (Delta: {result.time_delta_pct}%)")
    print(f"  Recommendation: {result.recommendation[:80]}...")


if __name__ == "__main__":
    test_graph_manager()
    test_simulation_engine()
    test_what_if_engine()
    print("\nALL BACKEND UNIT TESTS PASSED SUCCESSFULLY! [OK]")
