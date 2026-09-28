"""
TwinEvac - What-If Counterfactual Simulation Engine
Simulates hypothetical operational interventions in an isolated clone of the digital twin
to calculate side-by-side comparative deltas against baseline operations.
"""

from typing import Dict, List, Optional
import copy

from app.engine.simulation import EvacuationSimulation
from app.schemas.models import WhatIfScenario, ScenarioComparisonResult


class WhatIfEngine:
    def __init__(self, base_simulation: EvacuationSimulation):
        self.base_sim = base_simulation

    def evaluate_scenario(self, scenario: WhatIfScenario) -> ScenarioComparisonResult:
        """
        Runs an isolated simulation fork with the hypothetical interventions applied,
        steps forward 30 simulated minutes, and computes comparative performance deltas.
        """
        # Baseline snapshot
        base_state = self.base_sim.get_current_state()
        base_eet = base_state.estimated_evacuation_time_minutes
        base_bottlenecks = base_state.active_bottlenecks_count
        base_exposure = sum(r.contagion_exposure_score for r in base_state.roads) / max(len(base_state.roads), 1)

        # Create cloned simulation fork
        forked_sim = EvacuationSimulation()
        # Synchronize elapsed state
        forked_sim.elapsed_sim_minutes = self.base_sim.elapsed_sim_minutes
        forked_sim.tick_count = self.base_sim.tick_count
        
        # Apply the scenario interventions
        forked_sim.apply_scenario(scenario)

        # Run forward simulation steps (e.g. 15 ticks = ~7.5 sim minutes forward)
        for _ in range(12):
            forked_sim.step()

        forked_state = forked_sim.get_current_state()
        whatif_eet = forked_state.estimated_evacuation_time_minutes
        whatif_bottlenecks = forked_state.active_bottlenecks_count
        whatif_exposure = sum(r.contagion_exposure_score for r in forked_state.roads) / max(len(forked_state.roads), 1)

        # Compute Deltas
        time_delta_min = round(whatif_eet - base_eet, 1)
        time_delta_pct = round(((whatif_eet - base_eet) / max(base_eet, 0.1)) * 100, 1)

        # Shelter load delta
        shelter_delta: Dict[str, float] = {}
        for s_base in base_state.shelters:
            s_fork = next((s for s in forked_state.shelters if s.id == s_base.id), None)
            if s_fork:
                shelter_delta[s_base.id] = round(s_fork.occupancy_pct - s_base.occupancy_pct, 1)

        # Generate intelligent recommendation
        if time_delta_min < 0:
            rec = f"STRATEGY RECOMMENDED: Implementing this intervention reduces Total Evacuation Time by {abs(time_delta_pct):.1f}% ({abs(time_delta_min):.1f} mins) and eases bottleneck pressure."
        elif time_delta_min == 0:
            rec = "NEUTRAL IMPACT: Intervention maintains current evacuation timeline with minor traffic redistributions."
        else:
            rec = f"WARNING: This intervention increases evacuation completion time by +{time_delta_pct:.1f}% (+{time_delta_min:.1f} mins). Consider deploying additional express transit or opening bypass corridors."

        return ScenarioComparisonResult(
            baseline_eet_minutes=base_eet,
            what_if_eet_minutes=whatif_eet,
            time_delta_minutes=time_delta_min,
            time_delta_pct=time_delta_pct,
            baseline_bottlenecks=base_bottlenecks,
            what_if_bottlenecks=whatif_bottlenecks,
            baseline_exposure_index=round(base_exposure, 3),
            what_if_exposure_index=round(whatif_exposure, 3),
            shelter_load_delta=shelter_delta,
            recommendation=rec
        )
