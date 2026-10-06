"""
TwinEvac - Predictive Analytics & What-If Endpoints
Provides forward horizon predictions (15/30/60m) and What-If counterfactual evaluations.
"""

from typing import Dict, List, Any
from fastapi import APIRouter
from app.engine.rolling_optimizer import rolling_optimizer
from app.schemas.models import (
    PredictionHorizonData, WhatIfScenario, ScenarioComparisonResult, SimulationStepState
)

router = APIRouter(prefix="/analytics", tags=["Analytics & What-If"])


@router.get("/predictions", response_model=Dict[str, PredictionHorizonData])
def get_forward_predictions():
    """Returns predictive congestion and shelter forecasts for 15, 30, and 60-minute horizons."""
    state = rolling_optimizer.sim.get_current_state()
    return state.predictions


@router.get("/predefined-scenarios", response_model=List[WhatIfScenario])
def get_predefined_scenarios():
    """Returns library of pre-built disaster and epidemic scenarios for one-click testing."""
    return [
        WhatIfScenario(
            scenario_id="SCENARIO_SHEVAPET_LOCKDOWN",
            title="Shevapet Red-Zone Contagion Lockdown & River Flood",
            description="Strict containment cordon placed around Shevapet bazaar. Closes 4-Roads to Shevapet arterial and diverts all evacuees toward Steel Plant bypass.",
            closed_road_ids=["EDGE_4ROADS_SHEVAPET", "EDGE_SHEVAPET_GUGAI"],
            shelter_capacity_multipliers={"SHELTER_GMKMC": 1.0, "SHELTER_STEEL_PLANT": 1.25},
            hazard_radius_multiplier=1.35,
            evacuation_speed_multiplier=1.0,
            quarantine_lockdown_zone_ids=["ZONE_SHEVAPET"]
        ),
        WhatIfScenario(
            scenario_id="SCENARIO_GMKMC_OVERFLOW",
            title="GMKMC Hospital 100% Saturation (Triage Redirect)",
            description="GMKMC Hospital reaches maximum quarantine & ICU capacity. All subsequent ambulances and symptomatic evacuees are rerouted to Steel Plant mega refuge.",
            closed_road_ids=[],
            shelter_capacity_multipliers={"SHELTER_GMKMC": 0.4},
            hazard_radius_multiplier=1.0,
            evacuation_speed_multiplier=1.0,
            quarantine_lockdown_zone_ids=[]
        ),
        WhatIfScenario(
            scenario_id="SCENARIO_FOUR_ROADS_CHOKE",
            title="Salem 4-Roads Arterial Gridlock & Inundation",
            description="Simulates sudden flash waterlogging at central 4-Roads junction, forcing traffic rerouting across peripheral ring roads.",
            closed_road_ids=["EDGE_MEYYANUR_4ROADS", "EDGE_4ROADS_COLLECT"],
            shelter_capacity_multipliers={},
            hazard_radius_multiplier=1.2,
            evacuation_speed_multiplier=0.85,
            quarantine_lockdown_zone_ids=[]
        ),
        WhatIfScenario(
            scenario_id="SCENARIO_EXPRESS_TRANSIT",
            title="Deployment of Express Transit Bus Corridor",
            description="Deploys high-capacity emergency transit convoys on National Highway bypass corridors, expanding evacuation clearance speed.",
            closed_road_ids=[],
            shelter_capacity_multipliers={"SHELTER_STEEL_PLANT": 1.3, "SHELTER_AYODHYA": 1.2},
            hazard_radius_multiplier=0.9,
            evacuation_speed_multiplier=1.5,
            quarantine_lockdown_zone_ids=[]
        )
    ]


@router.post("/what-if/evaluate", response_model=ScenarioComparisonResult)
def evaluate_what_if_scenario(scenario: WhatIfScenario):
    """
    Evaluates a What-If scenario in an isolated clone of the digital twin
    and returns comparative metrics (EET Delta, Bottlenecks, Shelter shift).
    """
    result = rolling_optimizer.what_if_engine.evaluate_scenario(scenario)
    return result


@router.post("/what-if/apply", response_model=SimulationStepState)
def apply_what_if_to_live_twin(scenario: WhatIfScenario):
    """Applies the scenario directly into the active digital twin simulation."""
    return rolling_optimizer.apply_scenario(scenario)


@router.post("/what-if/clear", response_model=SimulationStepState)
def clear_what_if_scenario():
    """Clears any active scenario interventions and restores normal baseline state."""
    rolling_optimizer.sim.active_scenario = None
    rolling_optimizer.sim.graph_mgr.load_network()
    rolling_optimizer.sim.epidemic_model.update_road_hazard_exposure(
        list(rolling_optimizer.sim.graph_mgr.edges_dict.values()),
        rolling_optimizer.sim.zones,
        rolling_optimizer.sim.graph_mgr.nodes_dict
    )
    rolling_optimizer.sim.graph_mgr.recompute_all_edge_metrics()
    rolling_optimizer.sim.reroute_all_agents()
    return rolling_optimizer.sim.get_current_state()
