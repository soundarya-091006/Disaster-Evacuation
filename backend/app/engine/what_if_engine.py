"""
TwinEvac - What-If Counterfactual Simulation Engine
Runs hypothetical interventions from the CURRENT digital-twin state
inside an isolated simulation fork.
"""

from typing import Dict
import copy

from app.engine.simulation import EvacuationSimulation
from app.schemas.models import WhatIfScenario, ScenarioComparisonResult


class WhatIfEngine:
    def __init__(self, base_simulation: EvacuationSimulation):
        self.base_sim = base_simulation

    @staticmethod
    def _route_cost(sim: EvacuationSimulation, agent) -> float:
        """Calculate TwinEvac routing cost for an agent's current route."""
        total_cost = 0.0

        for edge_id in agent.route_edge_ids:
            edge = sim.graph_mgr.edges_dict.get(edge_id)

            if not edge:
                continue

            speed = max(edge.current_speed_kmh, 4.0)
            travel_time_min = (edge.distance_km / speed) * 60.0

            if edge.is_closed:
                # An agent already on a segment that has just been closed is allowed to
                # drive out of it; count plain travel time instead of the 999999 "blocked" cost.
                total_cost += travel_time_min
                continue

            total_cost += sim.graph_mgr.calculate_edge_cost(
                edge,
                travel_time_min,
            )

        return total_cost

    @classmethod
    def _total_route_cost(cls, sim: EvacuationSimulation) -> float:
        """Calculate aggregate evacuation route cost across in-transit agents."""
        return sum(
            cls._route_cost(sim, agent)
            for agent in sim.agents
            if agent.status == "in_transit"
        )

    HORIZON_STEPS = 12  # simulation ticks (= 6 minutes at 1x) both forks are advanced

    def _fork(self) -> EvacuationSimulation:
        """Isolated deep copy of the CURRENT digital-twin state (live twin is never touched)."""
        fork = copy.deepcopy(self.base_sim)
        fork.is_running = False
        return fork

    @staticmethod
    def _exposure(state) -> float:
        return sum(r.contagion_exposure_score for r in state.roads) / max(len(state.roads), 1)

    def evaluate_scenario(self, scenario: WhatIfScenario) -> ScenarioComparisonResult:
        """
        Forks the live twin TWICE from its current state:
          * a baseline fork that keeps the live twin's current interventions, and
          * a what-if fork with the scenario applied on top.
        Both forks are advanced the same number of ticks so every metric compares like
        with like (same elapsed time, same departures), then the deltas are reported.
        """
        baseline_fork = self._fork()
        whatif_fork = self._fork()

        whatif_fork.apply_scenario(scenario)

        for _ in range(self.HORIZON_STEPS):
            baseline_fork.step()
            whatif_fork.step()

        base_state = baseline_fork.get_current_state()
        forked_state = whatif_fork.get_current_state()

        base_eet = base_state.estimated_evacuation_time_minutes
        whatif_eet = forked_state.estimated_evacuation_time_minutes

        baseline_route_cost = self._total_route_cost(baseline_fork)
        final_route_cost = self._total_route_cost(whatif_fork)
        route_delta_min = final_route_cost - baseline_route_cost
        route_delta_pct = (route_delta_min / baseline_route_cost * 100.0) if baseline_route_cost > 0 else 0.0

        time_delta_min = round(whatif_eet - base_eet, 1)
        time_delta_pct = round(((whatif_eet - base_eet) / max(base_eet, 0.1)) * 100, 1)

        shelter_delta: Dict[str, float] = {}
        for s_base in base_state.shelters:
            s_fork = next((s for s in forked_state.shelters if s.id == s_base.id), None)
            if s_fork:
                shelter_delta[s_base.id] = round(s_fork.occupancy_pct - s_base.occupancy_pct, 1)

        # Recommendation text driven mainly by evacuation time, then route cost
        parts = []
        if time_delta_min <= -0.5:
            parts.append(f"STRATEGY RECOMMENDED: estimated evacuation time drops by {abs(time_delta_min):.1f} min ({abs(time_delta_pct):.1f}%).")
        elif time_delta_min >= 0.5:
            parts.append(f"WARNING: estimated evacuation time rises by {time_delta_min:.1f} min ({time_delta_pct:.1f}%). Consider express transit or opening bypass corridors.")
        else:
            parts.append("NEUTRAL IMPACT: the intervention does not materially change the estimated evacuation time.")
        if route_delta_min < -0.1:
            parts.append(f"Aggregate route cost is {abs(route_delta_pct):.1f}% lower.")
        elif route_delta_min > 0.1:
            parts.append(f"Aggregate route cost is {route_delta_pct:.1f}% higher (longer or riskier detours).")
        if whatif_eet >= 999.9:
            parts.append("CRITICAL: the scenario leaves the population with no open route or shelter.")

        return ScenarioComparisonResult(
            baseline_eet_minutes=base_eet,
            what_if_eet_minutes=whatif_eet,
            time_delta_minutes=time_delta_min,
            time_delta_pct=time_delta_pct,
            baseline_route_cost=round(baseline_route_cost, 1),
            what_if_route_cost=round(final_route_cost, 1),
            route_cost_delta=round(route_delta_min, 1),
            route_cost_delta_pct=round(route_delta_pct, 1),
            baseline_bottlenecks=base_state.active_bottlenecks_count,
            what_if_bottlenecks=forked_state.active_bottlenecks_count,
            baseline_exposure_index=round(self._exposure(base_state), 3),
            what_if_exposure_index=round(self._exposure(forked_state), 3),
            shelter_load_delta=shelter_delta,
            recommendation=" ".join(parts),
        )
