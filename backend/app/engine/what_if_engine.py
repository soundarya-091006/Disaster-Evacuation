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

    def evaluate_scenario(self, scenario: WhatIfScenario) -> ScenarioComparisonResult:
        """
        Clone the current digital-twin state, calculate baseline route cost,
        apply the hypothetical intervention, run the counterfactual forward,
        and compare routing impact.
        """

        # ---------------------------------------------------------
        # 1. Current baseline
        # ---------------------------------------------------------
        base_state = self.base_sim.get_current_state()

        base_eet = base_state.estimated_evacuation_time_minutes
        base_bottlenecks = base_state.active_bottlenecks_count

        base_exposure = (
            sum(r.contagion_exposure_score for r in base_state.roads)
            / max(len(base_state.roads), 1)
        )

        baseline_route_cost = self._total_route_cost(self.base_sim)

        # ---------------------------------------------------------
        # 2. Clone CURRENT digital-twin state
        # ---------------------------------------------------------
        forked_sim = EvacuationSimulation()

        forked_sim.graph_mgr = copy.deepcopy(self.base_sim.graph_mgr)
        forked_sim.epidemic_model = copy.deepcopy(self.base_sim.epidemic_model)
        forked_sim.risk_classifier = copy.deepcopy(self.base_sim.risk_classifier)
        forked_sim.traffic_predictor = copy.deepcopy(self.base_sim.traffic_predictor)
        forked_sim.anomaly_detector = copy.deepcopy(self.base_sim.anomaly_detector)

        forked_sim.router = copy.deepcopy(self.base_sim.router)
        forked_sim.router.graph_mgr = forked_sim.graph_mgr

        forked_sim.shelters = copy.deepcopy(self.base_sim.shelters)
        forked_sim.zones = copy.deepcopy(self.base_sim.zones)
        forked_sim.agents = copy.deepcopy(self.base_sim.agents)
        forked_sim.advisories = copy.deepcopy(self.base_sim.advisories)

        forked_sim.tick_count = self.base_sim.tick_count
        forked_sim.elapsed_sim_minutes = self.base_sim.elapsed_sim_minutes
        forked_sim.is_running = False
        forked_sim.speed_multiplier = self.base_sim.speed_multiplier
        forked_sim.baseline_eet_minutes = self.base_sim.baseline_eet_minutes

        # ---------------------------------------------------------
        # 3. Apply intervention
        # ---------------------------------------------------------
        forked_sim.apply_scenario(scenario)

        # Cost immediately after intervention and A* rerouting.
        immediate_route_cost = self._total_route_cost(forked_sim)

        # ---------------------------------------------------------
        # 4. Run counterfactual simulation
        # ---------------------------------------------------------
        for _ in range(12):
            forked_sim.step()

        forked_state = forked_sim.get_current_state()

        whatif_eet = forked_state.estimated_evacuation_time_minutes
        whatif_bottlenecks = forked_state.active_bottlenecks_count

        whatif_exposure = (
            sum(r.contagion_exposure_score for r in forked_state.roads)
            / max(len(forked_state.roads), 1)
        )

        final_route_cost = self._total_route_cost(forked_sim)

        # ---------------------------------------------------------
        # 5. Routing impact
        # ---------------------------------------------------------
        route_delta_min = final_route_cost - baseline_route_cost

        if baseline_route_cost > 0:
            route_delta_pct = (route_delta_min / baseline_route_cost) * 100.0
        else:
            route_delta_pct = 0.0

        # ---------------------------------------------------------
        # 6. Existing EET delta
        # ---------------------------------------------------------
        time_delta_min = round(whatif_eet - base_eet, 1)

        time_delta_pct = round(
            ((whatif_eet - base_eet) / max(base_eet, 0.1)) * 100,
            1,
        )

        # ---------------------------------------------------------
        # 7. Shelter load delta
        # ---------------------------------------------------------
        shelter_delta: Dict[str, float] = {}

        for s_base in base_state.shelters:
            s_fork = next(
                (s for s in forked_state.shelters if s.id == s_base.id),
                None,
            )

            if s_fork:
                shelter_delta[s_base.id] = round(
                    s_fork.occupancy_pct - s_base.occupancy_pct,
                    1,
                )

        # ---------------------------------------------------------
        # 8. Recommendation
        # ---------------------------------------------------------
        if route_delta_min < -0.1:
            rec = (
                f"STRATEGY RECOMMENDED: A* rerouting reduces aggregate "
                f"evacuation route cost by {abs(route_delta_pct):.1f}% "
                f"({abs(route_delta_min):.1f} cost-minutes)."
            )

        elif route_delta_min > 0.1:
            rec = (
                f"WARNING: A* rerouting increases aggregate evacuation "
                f"route cost by {route_delta_pct:.1f}% "
                f"({route_delta_min:.1f} cost-minutes). "
                f"Consider deploying additional express transit or "
                f"opening bypass corridors."
            )

        else:
            rec = (
                "NEUTRAL IMPACT: The intervention does not materially "
                "change aggregate evacuation route cost."
            )

        # Add EET information when it actually changes.
        if time_delta_min != 0:
            rec += (
                f" Total evacuation time changes by "
                f"{time_delta_min:+.1f} minutes ({time_delta_pct:+.1f}%)."
            )

        return ScenarioComparisonResult(
            baseline_eet_minutes=base_eet,
            what_if_eet_minutes=whatif_eet,
            time_delta_minutes=time_delta_min,
            time_delta_pct=time_delta_pct,
            baseline_route_cost=round(baseline_route_cost, 1),
            what_if_route_cost=round(final_route_cost, 1),
            route_cost_delta=round(route_delta_min, 1),
            route_cost_delta_pct=round(route_delta_pct, 1),
            baseline_bottlenecks=base_bottlenecks,
            what_if_bottlenecks=whatif_bottlenecks,
            baseline_exposure_index=round(base_exposure, 3),
            what_if_exposure_index=round(whatif_exposure, 3),
            shelter_load_delta=shelter_delta,
            recommendation=rec,
        )
