"""
TwinEvac - Pydantic Data Models & Schemas
Defines core schemas for Digital Twin state, road graph, shelters, agents,
what-if scenarios, and AI predictions.
"""

from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field, computed_field


class Coordinate(BaseModel):
    lat: float
    lng: float


class RoadNode(BaseModel):
    id: str
    name: str
    lat: float
    lng: float
    type: str = "intersection"  # intersection, landmark, hospital_access, shelter_access


class RoadSegment(BaseModel):
    id: str
    source: str
    target: str
    name: str
    distance_km: float
    lanes: int = 2
    free_flow_speed_kmh: float = 45.0
    capacity_pcu_per_hour: float = 1800.0
    current_volume: float = 0.0
    current_speed_kmh: float = 45.0
    congestion_index: float = 0.0  # 0.0 (free) to 1.0 (gridlock)
    risk_level: str = "LOW"  # LOW, MEDIUM, HIGH, CRITICAL
    flood_depth_cm: float = 0.0
    contagion_exposure_score: float = 0.0  # 0.0 to 1.0 (airborne/fomite corridor hazard)
    is_closed: bool = False
    is_one_way: bool = False
    bottleneck_severity: float = 0.0  # 0.0 to 1.0


class ShelterHospital(BaseModel):
    id: str
    name: str
    type: str = "hospital_quarantine"  # hospital_quarantine, relief_shelter, community_safe_zone
    lat: float
    lng: float
    total_capacity: int
    occupied: int = 0
    quarantine_beds_total: int = 200
    quarantine_beds_occupied: int = 0
    intake_rate_per_min: float = 25.0
    status: str = "OPEN"  # OPEN, NEAR_CAPACITY, FULL, ISOLATED
    assigned_zone_ids: List[str] = Field(default_factory=list)

    @computed_field
    @property
    def occupancy_pct(self) -> float:
        if self.total_capacity <= 0:
            return 100.0
        return min(100.0, round((self.occupied / self.total_capacity) * 100, 1))

    @computed_field
    @property
    def quarantine_occupancy_pct(self) -> float:
        if self.quarantine_beds_total <= 0:
            return 100.0
        return min(100.0, round((self.quarantine_beds_occupied / self.quarantine_beds_total) * 100, 1))


class EvacuationZone(BaseModel):
    id: str
    name: str
    center: Coordinate
    boundary_coords: List[Coordinate] = Field(default_factory=list)
    total_population: int
    evacuated_population: int = 0
    active_infections: int = 0
    hazard_type: str = "flood_and_contagion"  # flood_and_contagion, disease_hotspot, safe_buffer
    risk_score: float = 0.5  # 0.0 to 1.0
    clearance_percentage: float = 0.0


class EvacuationAgent(BaseModel):
    id: str
    origin_zone_id: str
    destination_shelter_id: str
    agent_type: str = "pedestrian_group"  # pedestrian_group, private_vehicle, emergency_bus, ambulance
    size: int = 10  # number of individuals
    current_edge_id: str
    progress_on_edge: float = 0.0  # 0.0 to 1.0
    current_lat: float
    current_lng: float
    route: List[str] = Field(default_factory=list)  # node IDs
    route_edge_ids: List[str] = Field(default_factory=list)
    status: str = "in_transit"  # waiting, in_transit, arrived, detoured
    infection_exposure_accumulated: float = 0.0


class PredictionHorizonData(BaseModel):
    horizon_minutes: int  # 15, 30, 60
    predicted_congested_road_count: int
    predicted_average_speed_kmh: float
    predicted_network_congestion_pct: float
    high_risk_road_ids: List[str] = Field(default_factory=list)
    shelter_predicted_occupancy: Dict[str, float] = Field(default_factory=dict)
    predicted_bottlenecks: List[Dict[str, Any]] = Field(default_factory=list)
    confidence_pct: float = 92.5


class WhatIfScenario(BaseModel):
    scenario_id: str = "custom"
    title: str = "Custom What-If Scenario"
    description: str = ""
    closed_road_ids: List[str] = Field(default_factory=list)
    shelter_capacity_multipliers: Dict[str, float] = Field(default_factory=dict)
    hazard_radius_multiplier: float = 1.0
    evacuation_speed_multiplier: float = 1.0
    quarantine_lockdown_zone_ids: List[str] = Field(default_factory=list)


class TacticalAdvisory(BaseModel):
    id: str
    timestamp_sim_min: float
    severity: str = "WARNING"  # INFO, WARNING, CRITICAL
    category: str = "ROUTING"  # ROUTING, QUARANTINE, SHELTER_CAPACITY, BOTTLENECK
    title: str
    message: str
    recommended_action: str
    affected_elements: List[str] = Field(default_factory=list)
    is_applied: bool = False


class AnomalyReport(BaseModel):
    id: str
    timestamp_sim_min: float
    anomaly_type: str  # SURGE_SPIKE, UNEXPECTED_GRIDLOCK, INTAKE_STALL, CONTAINMENT_BREACH
    location: str
    severity_score: float
    description: str


class SimulationStepState(BaseModel):
    tick: int
    elapsed_sim_minutes: float
    is_running: bool
    speed_multiplier: float = 1.0
    total_at_risk_population: int
    total_evacuated: int
    total_in_transit: int
    evacuation_progress_pct: float
    estimated_evacuation_time_minutes: float
    baseline_eet_minutes: float
    average_network_speed_kmh: float
    active_bottlenecks_count: int
    roads: List[RoadSegment]
    shelters: List[ShelterHospital]
    zones: List[EvacuationZone]
    agents: List[EvacuationAgent]
    predictions: Dict[str, PredictionHorizonData]
    advisories: List[TacticalAdvisory]
    anomalies: List[AnomalyReport]
    active_scenario: Optional[WhatIfScenario] = None


class ScenarioComparisonResult(BaseModel):
    baseline_eet_minutes: float
    what_if_eet_minutes: float
    time_delta_minutes: float
    time_delta_pct: float
    baseline_bottlenecks: int
    what_if_bottlenecks: int
    baseline_exposure_index: float
    what_if_exposure_index: float
    shelter_load_delta: Dict[str, float]
    recommendation: str
