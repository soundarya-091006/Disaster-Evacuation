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


def test_every_shelter_is_reachable():
    """Regression: access_node_id used to be dropped by the schema, hiding GMKMC and Ayodhya."""
    print("Testing shelter access nodes...")
    sim = EvacuationSimulation()
    for shelter in sim.shelters:
        node = sim.router.access_node(shelter)
        assert sim.graph_mgr.graph.has_node(node), f"{shelter.id} access node {node} missing from road graph"
    destinations = {a.destination_shelter_id for a in sim.agents}
    assert "SHELTER_GMKMC" in destinations, "no agent is routed to the GMKMC hospital"
    print("[OK] All shelters reachable; GMKMC receives evacuees.")


def test_scenario_apply_is_idempotent_and_reversible():
    print("Testing scenario apply / reopen / clear...")
    sim = EvacuationSimulation()
    base_caps = {s.id: s.total_capacity for s in sim.shelters}
    sc = WhatIfScenario(
        scenario_id="T", closed_road_ids=["EDGE_4ROADS_SHEVAPET", "EDGE_SHEVAPET_GUGAI"],
        shelter_capacity_multipliers={"SHELTER_STEEL_PLANT": 1.25}, evacuation_speed_multiplier=1.5,
    )
    sim.apply_scenario(sc)
    sim.apply_scenario(sc)  # applying twice must not compound
    caps = {s.id: s.total_capacity for s in sim.shelters}
    assert caps["SHELTER_STEEL_PLANT"] == int(base_caps["SHELTER_STEEL_PLANT"] * 1.25)

    # Reopen one road by removing it from the scenario
    sc2 = sc.model_copy(update={"closed_road_ids": ["EDGE_4ROADS_SHEVAPET"]})
    sim.apply_scenario(sc2)
    closed = {e.id for e in sim.graph_mgr.edges_dict.values() if e.is_closed}
    assert closed == {"EDGE_4ROADS_SHEVAPET", "EDGE_4ROADS_SHEVAPET_REV"}, closed

    sim.clear_scenario()
    assert not any(e.is_closed for e in sim.graph_mgr.edges_dict.values())
    assert {s.id: s.total_capacity for s in sim.shelters} == base_caps
    assert sim.scenario_flow_multiplier == 1.0 and sim.speed_multiplier == 1.0
    assert sim.active_scenario is None
    print("[OK] Apply is idempotent, roads reopen, clear restores capacities and speed.")


def test_rerouting_keeps_agents_in_place_and_avoids_closed_roads():
    print("Testing mid-route rerouting...")
    sim = EvacuationSimulation()
    for _ in range(15):
        sim.step()
    before = {a.id: (a.current_lat, a.current_lng) for a in sim.agents if a.status == "in_transit"}
    sim.apply_scenario(WhatIfScenario(scenario_id="T", closed_road_ids=["EDGE_4ROADS_SHEVAPET", "EDGE_SHEVAPET_GUGAI"]))
    sim.step()
    for a in sim.agents:
        if a.id in before and a.status == "in_transit":
            d = abs(a.current_lat - before[a.id][0]) + abs(a.current_lng - before[a.id][1])
            assert d < 0.02, f"{a.id} jumped {d:.3f} degrees after rerouting"
        # only the segment an agent is already on may be closed
        assert not any(sim.graph_mgr.edges_dict[e].is_closed for e in a.route_edge_ids[1:]), f"{a.id} routed through a closed road"
    print("[OK] Agents keep their position and new routes avoid closed roads.")


def test_evacuation_continues_and_respects_capacity():
    print("Testing long run (spawning + shelter capacity)...")
    sim = EvacuationSimulation()
    start_evac = sim.get_current_state().total_evacuated
    for _ in range(120):
        sim.step()
    state = sim.get_current_state()
    assert state.total_evacuated > start_evac + 1000, "evacuation stalled early"
    for s in state.shelters:
        assert s.occupied <= s.total_capacity, f"{s.id} over capacity"
    ids = [a.id for a in sim.agents]
    assert len(ids) == len(set(ids)), "duplicate agent ids"
    print(f"[OK] {state.total_evacuated - start_evac} people evacuated, no shelter over capacity.")


def test_what_if_time_reacts_to_intervention():
    print("Testing What-If time response...")
    sim = EvacuationSimulation()
    engine = WhatIfEngine(sim)
    worse = engine.evaluate_scenario(WhatIfScenario(scenario_id="W", closed_road_ids=["EDGE_4ROADS_SHEVAPET", "EDGE_SHEVAPET_GUGAI"], hazard_radius_multiplier=1.35))
    better = engine.evaluate_scenario(WhatIfScenario(scenario_id="B", evacuation_speed_multiplier=1.5, shelter_capacity_multipliers={"SHELTER_STEEL_PLANT": 1.3}))
    assert worse.time_delta_minutes > 0, "closing roads should lengthen evacuation"
    assert better.time_delta_minutes < 0, "express transit should shorten evacuation"
    assert sim.active_scenario is None, "evaluate must not modify the live twin"
    print(f"[OK] closures {worse.time_delta_minutes:+.1f} min, express transit {better.time_delta_minutes:+.1f} min.")


def test_reset_clears_everything():
    print("Testing reset...")
    sim = EvacuationSimulation()
    for _ in range(60):
        sim.step()
    sim.apply_scenario(WhatIfScenario(scenario_id="T", closed_road_ids=["EDGE_4ROADS_SHEVAPET"]))
    sim.reset()
    assert sim.tick_count == 0 and sim.advisories == [] and sim.active_scenario is None
    assert not any(e.is_closed for e in sim.graph_mgr.edges_dict.values())
    print("[OK] Reset restores the initial baseline.")


if __name__ == "__main__":
    test_graph_manager()
    test_simulation_engine()
    test_what_if_engine()
    test_every_shelter_is_reachable()
    test_scenario_apply_is_idempotent_and_reversible()
    test_rerouting_keeps_agents_in_place_and_avoids_closed_roads()
    test_evacuation_continues_and_respects_capacity()
    test_what_if_time_reacts_to_intervention()
    test_reset_clears_everything()
    print("\nALL BACKEND UNIT TESTS PASSED SUCCESSFULLY! [OK]")
