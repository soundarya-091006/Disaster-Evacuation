"""
TwinEvac - Multi-Agent Simulation Engine
Orchestrates agent-based mobility, dynamic road congestion, shelter intake,
and disease exposure tracking across the Salem urban network.
"""

import json
import math
import copy
import uuid
from typing import List, Dict, Optional, Tuple, Any
import numpy as np

from app.core.config import settings
from app.core.graph_manager import GraphManager
from app.core.weather_service import weather_service
from app.engine.epidemic_model import EpidemicHazardModel
from app.ml.risk_classifier import RiskClassifier
from app.ml.traffic_predictor import TrafficPredictor
from app.ml.anomaly_detector import AnomalyDetector
from app.ml.router import EvacuationRouter
from app.ml.ml_service import ml_service
from app.schemas.models import (
    RoadNode, RoadSegment, ShelterHospital, EvacuationZone,
    EvacuationAgent, TacticalAdvisory, SimulationStepState,
    WhatIfScenario, Coordinate, WeatherState
)


class EvacuationSimulation:
    def __init__(self, network_path: Optional[str] = None):
        self.graph_mgr = GraphManager(network_path)
        self.epidemic_model = EpidemicHazardModel()
        self.risk_classifier = RiskClassifier()
        self.traffic_predictor = TrafficPredictor()
        self.anomaly_detector = AnomalyDetector()
        self.router = EvacuationRouter(self.graph_mgr)

        self.shelters: List[ShelterHospital] = []
        self.zones: List[EvacuationZone] = []
        self.agents: List[EvacuationAgent] = []
        self.advisories: List[TacticalAdvisory] = []
        
        self.tick_count: int = 0
        self.elapsed_sim_minutes: float = 0.0
        self.is_running: bool = False
        self.speed_multiplier: float = 1.0
        self.baseline_eet_minutes: float = 0.0
        self.active_scenario: Optional[WhatIfScenario] = None
        # Scenario-driven flow multiplier is kept separate from the operator's
        # 1x/2x/5x clock speed so that clearing a scenario restores both cleanly.
        self.scenario_flow_multiplier: float = 1.0
        self._agent_seq: int = 0
        self._base_shelter_caps: Dict[str, Tuple[int, int]] = {}
        self.weather_service = weather_service
        self.ml_service = ml_service
        self.history_congestion_trend: List[float] = [18.5]
        self.history_shelter_load: Dict[str, List[float]] = {}

        self.load_initial_data()
        self.initialize_state()

    def __deepcopy__(self, memo):
        cls = self.__class__
        result = cls.__new__(cls)
        memo[id(self)] = result
        result.graph_mgr = copy.deepcopy(self.graph_mgr, memo)
        result.epidemic_model = self.epidemic_model
        result.risk_classifier = self.risk_classifier
        result.traffic_predictor = self.traffic_predictor
        result.anomaly_detector = self.anomaly_detector
        result.router = EvacuationRouter(result.graph_mgr)
        result.weather_service = self.weather_service
        result.ml_service = self.ml_service
        result.shelters = [s.model_copy(deep=True) for s in self.shelters]
        result.zones = [z.model_copy(deep=True) for z in self.zones]
        result.agents = [a.model_copy(deep=True) for a in self.agents]
        result.advisories = [adv.model_copy(deep=True) for adv in self.advisories]
        result.tick_count = self.tick_count
        result.elapsed_sim_minutes = self.elapsed_sim_minutes
        result.is_running = self.is_running
        result.speed_multiplier = self.speed_multiplier
        result.baseline_eet_minutes = self.baseline_eet_minutes
        result.active_scenario = self.active_scenario.model_copy(deep=True) if self.active_scenario else None
        result.scenario_flow_multiplier = self.scenario_flow_multiplier
        result._agent_seq = self._agent_seq
        result._base_shelter_caps = dict(self._base_shelter_caps)
        result._baseline_zone_cost = dict(self._baseline_zone_cost)
        result.history_congestion_trend = list(self.history_congestion_trend)
        result.history_shelter_load = {k: list(v) for k, v in self.history_shelter_load.items()}
        return result

    def load_initial_data(self):
        """Loads shelters and population zones from JSON files."""
        # Load Shelters
        with open(settings.SHELTERS_PATH, "r", encoding="utf-8") as f:
            shelters_data = json.load(f)
            self.shelters = [ShelterHospital(**s) for s in shelters_data]

        # Load Zones
        with open(settings.POPULATION_ZONES_PATH, "r", encoding="utf-8") as f:
            zones_data = json.load(f)
            self.zones = [EvacuationZone(**z) for z in zones_data]

        self._base_shelter_caps = {
            s.id: (s.total_capacity, s.quarantine_beds_total) for s in self.shelters
        }

    def initialize_state(self):
        """Initializes network hazards, initial agents, and baseline metrics."""
        self.epidemic_model.update_road_hazard_exposure(
            list(self.graph_mgr.edges_dict.values()),
            self.zones,
            self.graph_mgr.nodes_dict
        )
        self.graph_mgr.recompute_all_edge_metrics()

        # Spawn initial batch of evacuee agents
        self.spawn_initial_agents()
        self.update_network_volumes()

        # Baseline reference values used by the EET estimator and the What-If engine
        self._baseline_zone_cost = {}
        for z in self.zones:
            cost = self.router.best_path_cost(self._zone_origin(z), self.shelters)
            if cost is not None:
                self._baseline_zone_cost[z.id] = max(cost, 0.1)
        self.baseline_eet_minutes = self._estimate_eet()

    def spawn_initial_agents(self):
        """Spawns diverse agent groups (pedestrians, vehicles, ambulances) across high-risk origin zones."""
        self.agents.clear()
        self._agent_seq = 0

        for zone in self.zones:
            origin_node = self._zone_origin(zone)

            # Number of agent clusters based on zone population
            num_groups = max(4, int(zone.total_population / 1500))

            for g in range(num_groups):
                is_ambulance = (g == 0 and zone.active_infections > 50)
                is_bus = (g % 3 == 0)
                agent_type = "ambulance" if is_ambulance else ("emergency_bus" if is_bus else "pedestrian_group")
                group_size = 5 if is_ambulance else (50 if is_bus else 15)

                best_shelter_id, best_path, _ = self.router.find_best_evacuation_destination(
                    origin_node, self.shelters, agent_needs_quarantine=is_ambulance
                )

                if best_path and len(best_path) >= 2:
                    edge_ids = self.graph_mgr.get_path_edges(best_path)
                    first_edge = edge_ids[0] if edge_ids else ""
                    
                    src_node = self.graph_mgr.nodes_dict.get(best_path[0])
                    curr_lat = src_node.lat if src_node else zone.center.lat
                    curr_lng = src_node.lng if src_node else zone.center.lng

                    self._agent_seq += 1
                    agent = EvacuationAgent(
                        id=f"AGT_{self._agent_seq:04d}",
                        origin_zone_id=zone.id,
                        destination_shelter_id=best_shelter_id or "SHELTER_GMKMC",
                        agent_type=agent_type,
                        size=group_size,
                        current_edge_id=first_edge,
                        progress_on_edge=0.05 * (g % 10),
                        current_lat=curr_lat,
                        current_lng=curr_lng,
                        route=best_path,
                        route_edge_ids=edge_ids,
                        status="in_transit",
                        infection_exposure_accumulated=0.1 if is_ambulance else 0.0
                    )
                    self.agents.append(agent)

    def _zone_origin(self, zone: EvacuationZone) -> str:
        """Road-network node where a zone's evacuees depart from."""
        node = zone.nearest_node_id or f"NODE_{zone.id.replace('ZONE_', '')}"
        if not self.graph_mgr.graph.has_node(node):
            node = "NODE_FOUR_ROADS"  # fallback
        return node

    @staticmethod
    def _refresh_shelter_status(s: ShelterHospital):
        """Derives OPEN / NEAR_CAPACITY / FULL from current occupancy (ISOLATED is left alone)."""
        if s.status == "ISOLATED":
            return
        pct = s.occupancy_pct
        if pct >= 98.0:
            s.status = "FULL"
        elif pct >= 85.0:
            s.status = "NEAR_CAPACITY"
        else:
            s.status = "OPEN"

    def update_network_volumes(self):
        """Calculates volume on each road segment based on currently traversing agents."""
        pcu_weights = {
            "pedestrian_group": 0.4,
            "private_vehicle": 1.0,
            "emergency_bus": 3.0,
            "ambulance": 1.2
        }

        # Reset volumes
        edge_volumes: Dict[str, float] = {e_id: 150.0 for e_id in self.graph_mgr.edges_dict}  # background traffic

        for agent in self.agents:
            if agent.status == "in_transit" and agent.current_edge_id:
                pcu = pcu_weights.get(agent.agent_type, 1.0) * (agent.size / 10.0) * 12.0
                edge_volumes[agent.current_edge_id] = edge_volumes.get(agent.current_edge_id, 0.0) + pcu

        for e_id, vol in edge_volumes.items():
            self.graph_mgr.update_edge_flow(e_id, vol)

    def step(self) -> SimulationStepState:
        """Executes one simulation step: advances agents, updates flows, checks anomalies."""
        self.tick_count += 1
        dt_minutes = settings.SIM_MINUTES_PER_TICK * self.speed_multiplier * self.scenario_flow_multiplier
        self.elapsed_sim_minutes += dt_minutes

        # 1. Update Agent Positions
        arrived_agents = []
        for agent in self.agents:
            if agent.status != "in_transit":
                continue

            curr_edge = self.graph_mgr.edges_dict.get(agent.current_edge_id)
            if not curr_edge:
                continue

            # Speed on this edge
            speed = max(curr_edge.current_speed_kmh, 4.0)
            if agent.agent_type == "pedestrian_group":
                speed = min(speed, 6.0)  # pedestrian walking speed cap

            # Distance traveled in dt
            dist_traveled = speed * (dt_minutes / 60.0)
            progress_delta = dist_traveled / max(curr_edge.distance_km, 0.1)
            agent.progress_on_edge += progress_delta

            # Accumulate infection exposure if road has contagion
            agent.infection_exposure_accumulated += curr_edge.contagion_exposure_score * (dt_minutes / 30.0)

            # Interpolate geographic coordinate for UI rendering
            src_n = self.graph_mgr.nodes_dict.get(curr_edge.source)
            tgt_n = self.graph_mgr.nodes_dict.get(curr_edge.target)
            if src_n and tgt_n:
                p = min(1.0, max(0.0, agent.progress_on_edge))
                agent.current_lat = round(src_n.lat + (tgt_n.lat - src_n.lat) * p, 5)
                agent.current_lng = round(src_n.lng + (tgt_n.lng - src_n.lng) * p, 5)

            # Check if agent finished current edge
            if agent.progress_on_edge >= 1.0:
                agent.progress_on_edge = 0.0
                curr_idx = -1
                try:
                    curr_idx = agent.route_edge_ids.index(agent.current_edge_id)
                except ValueError:
                    pass

                if curr_idx >= 0 and curr_idx + 1 < len(agent.route_edge_ids):
                    # Move to next edge in route
                    agent.current_edge_id = agent.route_edge_ids[curr_idx + 1]
                else:
                    # Agent reached destination shelter!
                    agent.status = "arrived"
                    arrived_agents.append(agent)
                    self._handle_shelter_arrival(agent)

        # Retry people who were turned away from a full shelter (capacity may have changed)
        if self.tick_count % 5 == 0:
            for agent in self.agents:
                if agent.status == "waiting" and agent.route:
                    if self.router.reroute_from_node(agent, agent.route[-1], self.shelters):
                        agent.status = "in_transit"

        # Drop agents that have been fully absorbed by a shelter
        self.agents = [a for a in self.agents if a.status != "arrived"]

        # 2. Spawn periodic newly evacuated batches
        if self.tick_count % 3 == 0:
            self._spawn_periodic_departures()

        # 3. Update network traffic volumes & BPR travel times
        self.update_network_volumes()

        # 4. Check for anomalies & apply dynamic environmental hazards
        roads_list = list(self.graph_mgr.edges_dict.values())
        self.weather_service.update_road_flood_depths(roads_list)
        self.graph_mgr.recompute_all_edge_metrics()

        # Update historical time-series analytics trends
        active_roads = [r for r in roads_list if not r.is_closed]
        curr_avg_cong = float(np.mean([r.congestion_index for r in active_roads])) if active_roads else 0.0
        self.history_congestion_trend.append(round(curr_avg_cong * 100, 1))
        if len(self.history_congestion_trend) > 40:
            self.history_congestion_trend.pop(0)

        for s in self.shelters:
            s_hist = self.history_shelter_load.setdefault(s.id, [])
            s_hist.append(round(s.occupancy_pct, 1))
            if len(s_hist) > 40:
                s_hist.pop(0)

        anomalies = self.anomaly_detector.inspect_network(roads_list, self.shelters, self.elapsed_sim_minutes)

        # 5. Generate automated tactical advisories if bottlenecks surge
        self._evaluate_tactical_advisories()

        # 6. Compute summary telemetry
        state = self.get_current_state()
        state.anomalies = anomalies
        return state

    def _handle_shelter_arrival(self, agent: EvacuationAgent):
        """
        Processes agent arrival at its shelter. Only as many people as there are free beds
        are admitted; the rest are redirected to the next-best open shelter (or wait).
        """
        shelter = next((x for x in self.shelters if x.id == agent.destination_shelter_id), None)
        if shelter is None:
            agent.status = "arrived"
            return

        free = max(0, shelter.total_capacity - shelter.occupied)
        accepted = min(agent.size, free)

        if accepted > 0:
            shelter.occupied += accepted
            if agent.agent_type == "ambulance" or agent.infection_exposure_accumulated > 0.4:
                q_free = max(0, shelter.quarantine_beds_total - shelter.quarantine_beds_occupied)
                shelter.quarantine_beds_occupied += min(accepted, q_free)
            for z in self.zones:
                if z.id == agent.origin_zone_id:
                    z.evacuated_population = min(z.total_population, z.evacuated_population + accepted)
                    z.clearance_percentage = round((z.evacuated_population / max(z.total_population, 1)) * 100, 1)
                    break
        self._refresh_shelter_status(shelter)

        overflow = agent.size - accepted
        if overflow <= 0:
            agent.status = "arrived"
            return

        # Turned away: redirect the remainder to another open shelter if one is reachable
        agent.size = overflow
        arrival_node = agent.route[-1] if agent.route else None
        if arrival_node and self.router.reroute_from_node(agent, arrival_node, self.shelters):
            agent.status = "in_transit"
        else:
            agent.status = "waiting"

    def _spawn_periodic_departures(self):
        """Spawns incremental departure waves as evacuation proceeds."""
        active = sum(1 for a in self.agents if a.status in ("in_transit", "waiting"))
        locked = set(self.active_scenario.quarantine_lockdown_zone_ids) if self.active_scenario else set()

        for z in self.zones:
            if active >= 70:
                break
            remaining = z.total_population - z.evacuated_population
            if remaining <= 500:
                continue
            origin_node = self._zone_origin(z)
            # People leaving a locked-down (cordoned) zone may only go to quarantine-capable facilities
            best_shelter_id, best_path, _ = self.router.find_best_evacuation_destination(
                origin_node, self.shelters, agent_needs_quarantine=(z.id in locked), allow_full=False
            )
            if not best_shelter_id or not best_path or len(best_path) < 2:
                self._raise_capacity_advisory()
                continue
            edge_ids = self.graph_mgr.get_path_edges(best_path)
            if not edge_ids:
                continue
            self._agent_seq += 1
            self.agents.append(EvacuationAgent(
                id=f"AGT_{self._agent_seq:04d}",
                origin_zone_id=z.id,
                destination_shelter_id=best_shelter_id,
                agent_type="private_vehicle",
                size=20,
                current_edge_id=edge_ids[0],
                progress_on_edge=0.0,
                current_lat=z.center.lat,
                current_lng=z.center.lng,
                route=best_path,
                route_edge_ids=edge_ids,
                status="in_transit"
            ))
            active += 1

    def _push_advisory(self, adv: TacticalAdvisory):
        if any(a.id == adv.id for a in self.advisories):
            return
        self.advisories.insert(0, adv)
        if len(self.advisories) > 8:
            self.advisories.pop()

    def _raise_capacity_advisory(self):
        self._push_advisory(TacticalAdvisory(
            id="ADV_NO_OPEN_SHELTER",
            timestamp_sim_min=round(self.elapsed_sim_minutes, 1),
            severity="CRITICAL",
            category="SHELTER_CAPACITY",
            title="No open shelter reachable for new departures",
            message="Every reachable shelter is full or cut off. New evacuation waves are on hold.",
            recommended_action="Open additional relief centres or raise capacity at existing facilities.",
            affected_elements=[s.id for s in self.shelters]
        ))

    def _evaluate_tactical_advisories(self):
        """Generates AI-driven tactical re-routing recommendations."""
        # Road chokes
        for r in self.graph_mgr.edges_dict.values():
            if r.congestion_index > 0.88 and not r.is_closed:
                self._push_advisory(TacticalAdvisory(
                    id=f"ADV_REROUTE_{r.id}",
                    timestamp_sim_min=round(self.elapsed_sim_minutes, 1),
                    severity="CRITICAL",
                    category="ROUTING",
                    title=f"Severe Congestion Choke on {r.name}",
                    message=f"Traffic on {r.name} reached {r.congestion_index*100:.0f}% capacity. Recommending dynamic diversion of incoming convoys.",
                    recommended_action="Divert flows via the nearest open parallel corridor.",
                    affected_elements=[r.id]
                ))

        # Shelter capacity
        for s in self.shelters:
            if s.status == "FULL":
                self._push_advisory(TacticalAdvisory(
                    id=f"ADV_FULL_{s.id}",
                    timestamp_sim_min=round(self.elapsed_sim_minutes, 1),
                    severity="CRITICAL",
                    category="SHELTER_CAPACITY",
                    title=f"{s.name.split(' (')[0]} is FULL",
                    message=f"{s.occupied}/{s.total_capacity} beds occupied. New arrivals are being redirected to other facilities.",
                    recommended_action="Divert incoming evacuees to the next-best open shelter.",
                    affected_elements=[s.id]
                ))
            elif s.status == "NEAR_CAPACITY":
                self._push_advisory(TacticalAdvisory(
                    id=f"ADV_NEAR_{s.id}",
                    timestamp_sim_min=round(self.elapsed_sim_minutes, 1),
                    severity="WARNING",
                    category="SHELTER_CAPACITY",
                    title=f"{s.name.split(' (')[0]} nearing capacity",
                    message=f"{s.occupancy_pct:.0f}% of beds occupied.",
                    recommended_action="Start pre-emptive diversion to alternative shelters.",
                    affected_elements=[s.id]
                ))

    def _network_efficiency(self) -> float:
        """
        How well the road network currently serves the remaining population, relative to the
        un-disrupted baseline (1.0 = as good as baseline, <1.0 = closures / floods / jams slow
        people down, 0.0 = every zone is cut off). Weighted by each zone's remaining population.
        """
        weighted, weight_sum = 0.0, 0.0
        for z in self.zones:
            remaining = max(0, z.total_population - z.evacuated_population)
            base = self._baseline_zone_cost.get(z.id)
            if remaining <= 0 or base is None:
                continue
            now = self.router.best_path_cost(self._zone_origin(z), self.shelters)
            ratio = 0.0 if now is None else min(1.5, base / max(now, 0.1))
            weighted += ratio * remaining
            weight_sum += remaining
        return (weighted / weight_sum) if weight_sum > 0 else 1.0

    def _estimate_eet(self) -> float:
        """Estimated Evacuation Time (minutes) for everyone still at risk."""
        total_pop = sum(z.total_population for z in self.zones)
        total_evac = sum(z.evacuated_population for z in self.zones)
        remaining = max(0, total_pop - total_evac)
        if remaining == 0:
            return 0.0
        open_rate = sum(s.intake_rate_per_min for s in self.shelters if s.status not in ("FULL", "ISOLATED"))
        rate = open_rate * self._network_efficiency() * self.scenario_flow_multiplier
        if rate < 1.0:
            return 999.9  # evacuation effectively blocked
        return round(min(999.9, (remaining / rate) * 0.9), 1)

    def get_current_state(self) -> SimulationStepState:
        """Assembles and returns full Digital Twin snapshot with ML forecasts."""
        roads = list(self.graph_mgr.edges_dict.values())
        
        # Calculate totals
        total_pop = sum(z.total_population for z in self.zones)
        total_evac = sum(z.evacuated_population for z in self.zones)
        in_transit = sum(a.size for a in self.agents if a.status == "in_transit")
        
        active_roads = [r for r in roads if not r.is_closed]
        avg_speed = round(float(np.mean([r.current_speed_kmh for r in active_roads])), 1) if active_roads else 0.0
        bottlenecks = sum(1 for r in roads if r.congestion_index >= 0.75 or r.flood_depth_cm > 20.0)

        eet = self._estimate_eet()

        # Shelters occupancy mapping
        shelters_occ = {s.id: s.occupancy_pct for s in self.shelters}

        # 15m, 30m, 60m forward predictions
        predictions = self.traffic_predictor.generate_horizon_predictions(
            roads, shelters_occ, self.elapsed_sim_minutes
        )

        return SimulationStepState(
            tick=self.tick_count,
            elapsed_sim_minutes=round(self.elapsed_sim_minutes, 1),
            is_running=self.is_running,
            speed_multiplier=self.speed_multiplier,
            total_at_risk_population=total_pop,
            total_evacuated=total_evac,
            total_in_transit=in_transit,
            evacuation_progress_pct=round((total_evac / max(total_pop, 1)) * 100, 1),
            estimated_evacuation_time_minutes=eet,
            baseline_eet_minutes=self.baseline_eet_minutes,
            average_network_speed_kmh=avg_speed,
            active_bottlenecks_count=bottlenecks,
            roads=roads,
            shelters=self.shelters,
            zones=self.zones,
            agents=self.agents,
            predictions=predictions,
            advisories=self.advisories,
            anomalies=[],
            active_scenario=self.active_scenario,
            weather=WeatherState(**self.weather_service.get_state()),
            ml_service_status=self.ml_service.get_status(),
            history_congestion_trend=list(self.history_congestion_trend),
            history_shelter_load={k: list(v) for k, v in self.history_shelter_load.items()}
        )

    def _restore_interventions(self):
        """Removes every What-If intervention: reopens roads, restores shelter capacities and flow."""
        for edge in self.graph_mgr.edges_dict.values():
            edge.is_closed = False
        for sh in self.shelters:
            caps = self._base_shelter_caps.get(sh.id)
            if caps:
                sh.total_capacity, sh.quarantine_beds_total = caps
            self._refresh_shelter_status(sh)
        self.scenario_flow_multiplier = 1.0

    def apply_scenario(self, scenario: WhatIfScenario):
        """
        Applies a What-If scenario to the live twin. Applying is idempotent: the scenario
        REPLACES any previously active one (roads missing from closed_road_ids are reopened and
        shelter multipliers are applied to the original capacities, never compounded).
        """
        self._restore_interventions()
        self.active_scenario = scenario

        # 1. Road closures (both directions of every named road)
        for road_id in scenario.closed_road_ids:
            base_id = road_id[:-4] if road_id.endswith("_REV") else road_id
            for rid in (base_id, f"{base_id}_REV"):
                if rid in self.graph_mgr.edges_dict:
                    self.graph_mgr.edges_dict[rid].is_closed = True

        # 2. Shelter capacity multipliers (relative to the ORIGINAL capacity)
        for s_id, mult in scenario.shelter_capacity_multipliers.items():
            for sh in self.shelters:
                if sh.id == s_id:
                    base_total, base_q = self._base_shelter_caps.get(sh.id, (sh.total_capacity, sh.quarantine_beds_total))
                    sh.total_capacity = max(0, int(base_total * mult))
                    sh.quarantine_beds_total = max(0, int(base_q * mult))
                    self._refresh_shelter_status(sh)

        # 3. Hazard radius multiplier
        self.epidemic_model.update_road_hazard_exposure(
            list(self.graph_mgr.edges_dict.values()),
            self.zones,
            self.graph_mgr.nodes_dict,
            hazard_expansion_multiplier=scenario.hazard_radius_multiplier
        )

        # 4. Evacuation flow multiplier (does not touch the operator's 1x/2x/5x clock)
        self.scenario_flow_multiplier = max(0.1, scenario.evacuation_speed_multiplier)

        # 5. Cordon advisories for locked-down zones
        for zid in scenario.quarantine_lockdown_zone_ids:
            zone = next((z for z in self.zones if z.id == zid), None)
            if zone:
                self._push_advisory(TacticalAdvisory(
                    id=f"ADV_LOCKDOWN_{zid}",
                    timestamp_sim_min=round(self.elapsed_sim_minutes, 1),
                    severity="WARNING",
                    category="QUARANTINE",
                    title=f"Containment cordon active: {zone.name}",
                    message="Evacuees from this zone are restricted to quarantine-capable facilities.",
                    recommended_action="Dispatch ambulances and screening teams to the cordon perimeter.",
                    affected_elements=[zid]
                ))

        # Re-compute metrics and re-route agents affected by closures
        self.graph_mgr.recompute_all_edge_metrics()
        self.reroute_all_agents()

    def clear_scenario(self):
        """Removes the active scenario and returns the live twin to normal operations."""
        self._restore_interventions()
        self.active_scenario = None
        self.advisories = [a for a in self.advisories if not a.id.startswith("ADV_LOCKDOWN_")]
        self.epidemic_model.update_road_hazard_exposure(
            list(self.graph_mgr.edges_dict.values()),
            self.zones,
            self.graph_mgr.nodes_dict
        )
        self.graph_mgr.recompute_all_edge_metrics()
        self.reroute_all_agents()

    def reroute_all_agents(self):
        """Re-routes all in-transit agents from their current position using the updated graph."""
        for agent in self.agents:
            if agent.status == "in_transit":
                self.router.optimize_agent_route(agent, self.shelters)

    def reset(self):
        """Resets simulation to initial state."""
        self.tick_count = 0
        self.elapsed_sim_minutes = 0.0
        self.is_running = False
        self.speed_multiplier = 1.0
        self.scenario_flow_multiplier = 1.0
        self.active_scenario = None
        self.advisories = []
        self.history_congestion_trend = [18.5]
        self.history_shelter_load = {}
        self.anomaly_detector = AnomalyDetector()
        self.graph_mgr.load_network()
        self.load_initial_data()
        self.initialize_state()
