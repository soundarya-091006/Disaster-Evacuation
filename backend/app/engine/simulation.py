"""
TwinEvac - Multi-Agent Simulation Engine
Orchestrates agent-based mobility, dynamic road congestion, shelter intake,
and disease exposure tracking across the Salem urban network.
"""

import json
import math
import uuid
from typing import List, Dict, Optional, Tuple, Any
import numpy as np

from app.core.config import settings
from app.core.graph_manager import GraphManager
from app.engine.epidemic_model import EpidemicHazardModel
from app.ml.risk_classifier import RiskClassifier
from app.ml.traffic_predictor import TrafficPredictor
from app.ml.anomaly_detector import AnomalyDetector
from app.ml.router import EvacuationRouter
from app.schemas.models import (
    RoadNode, RoadSegment, ShelterHospital, EvacuationZone,
    EvacuationAgent, TacticalAdvisory, SimulationStepState,
    WhatIfScenario, Coordinate
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
        self.baseline_eet_minutes: float = 84.0
        self.active_scenario: Optional[WhatIfScenario] = None

        self.load_initial_data()
        self.initialize_state()

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

    def spawn_initial_agents(self):
        """Spawns diverse agent groups (pedestrians, vehicles, ambulances) across high-risk origin zones."""
        self.agents.clear()
        agent_id_counter = 1

        for zone in self.zones:
            origin_node = getattr(zone, "nearest_node_id", None) or f"NODE_{zone.id.replace('ZONE_', '')}"
            if not self.graph_mgr.graph.has_node(origin_node):
                origin_node = "NODE_FOUR_ROADS"  # fallback

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

                    agent = EvacuationAgent(
                        id=f"AGT_{agent_id_counter:04d}",
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
                    agent_id_counter += 1

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
        dt_minutes = settings.SIM_MINUTES_PER_TICK * self.speed_multiplier
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

        # 2. Spawn periodic newly evacuated batches
        if self.tick_count % 3 == 0:
            self._spawn_periodic_departures()

        # 3. Update network traffic volumes & BPR travel times
        self.update_network_volumes()

        # 4. Check for anomalies
        roads_list = list(self.graph_mgr.edges_dict.values())
        anomalies = self.anomaly_detector.inspect_network(roads_list, self.shelters, self.elapsed_sim_minutes)

        # 5. Generate automated tactical advisories if bottlenecks surge
        self._evaluate_tactical_advisories()

        # 6. Compute summary telemetry
        state = self.get_current_state()
        state.anomalies = anomalies
        return state

    def _handle_shelter_arrival(self, agent: EvacuationAgent):
        """Processes agent arrival at designated shelter, incrementing headcounts."""
        for s in self.shelters:
            if s.id == agent.destination_shelter_id:
                s.occupied = min(s.total_capacity, s.occupied + agent.size)
                if agent.agent_type == "ambulance" or agent.infection_exposure_accumulated > 0.4:
                    s.quarantine_beds_occupied = min(s.quarantine_beds_total, s.quarantine_beds_occupied + agent.size)

                # Update status
                occ_pct = s.occupancy_pct
                if occ_pct >= 98.0:
                    s.status = "FULL"
                elif occ_pct >= 85.0:
                    s.status = "NEAR_CAPACITY"
                break

        # Increment cleared population in origin zone
        for z in self.zones:
            if z.id == agent.origin_zone_id:
                z.evacuated_population = min(z.total_population, z.evacuated_population + agent.size)
                z.clearance_percentage = round((z.evacuated_population / max(z.total_population, 1)) * 100, 1)
                break

    def _spawn_periodic_departures(self):
        """Spawns incremental departure waves as evacuation proceeds."""
        for z in self.zones:
            remaining = z.total_population - z.evacuated_population
            if remaining > 500 and len(self.agents) < 75:
                origin_node = getattr(z, "nearest_node_id", "NODE_FOUR_ROADS")
                best_shelter_id, best_path, _ = self.router.find_best_evacuation_destination(origin_node, self.shelters)
                if best_path and len(best_path) >= 2:
                    edge_ids = self.graph_mgr.get_path_edges(best_path)
                    new_agent = EvacuationAgent(
                        id=f"AGT_{len(self.agents)+1:04d}",
                        origin_zone_id=z.id,
                        destination_shelter_id=best_shelter_id or "SHELTER_STEEL_PLANT",
                        agent_type="private_vehicle",
                        size=20,
                        current_edge_id=edge_ids[0],
                        progress_on_edge=0.0,
                        current_lat=z.center.lat,
                        current_lng=z.center.lng,
                        route=best_path,
                        route_edge_ids=edge_ids,
                        status="in_transit"
                    )
                    self.agents.append(new_agent)

    def _evaluate_tactical_advisories(self):
        """Generates AI-driven tactical re-routing recommendations."""
        # Find any road with critical bottleneck
        for r in self.graph_mgr.edges_dict.values():
            if r.congestion_index > 0.88 and not r.is_closed:
                # Check if advisory already exists
                adv_id = f"ADV_REROUTE_{r.id}"
                if not any(a.id == adv_id for a in self.advisories):
                    self.advisories.insert(0, TacticalAdvisory(
                        id=adv_id,
                        timestamp_sim_min=round(self.elapsed_sim_minutes, 1),
                        severity="CRITICAL",
                        category="ROUTING",
                        title=f"Severe Congestion Choke on {r.name}",
                        message=f"Traffic on {r.name} reached {r.congestion_index*100:.0f}% capacity. Recommending dynamic diversion of incoming convoys.",
                        recommended_action=f"Divert westbound flows via Steel Plant Highway bypass.",
                        affected_elements=[r.id]
                    ))
                    if len(self.advisories) > 8:
                        self.advisories.pop()

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

        # Estimated Evacuation Time (EET) in minutes
        remaining_pop = max(0, total_pop - total_evac)
        evac_rate = max(65.0, sum(s.intake_rate_per_min for s in self.shelters if s.status != "FULL"))
        eet = round((remaining_pop / evac_rate) * 0.9, 1)

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
            active_scenario=self.active_scenario
        )

    def apply_scenario(self, scenario: WhatIfScenario):
        """Applies What-If scenario interventions directly to the live twin."""
        self.active_scenario = scenario

        # 1. Road Closures
        for road_id in scenario.closed_road_ids:
            if road_id in self.graph_mgr.edges_dict:
                self.graph_mgr.edges_dict[road_id].is_closed = True
                rev_id = f"{road_id}_REV"
                if rev_id in self.graph_mgr.edges_dict:
                    self.graph_mgr.edges_dict[rev_id].is_closed = True

        # 2. Shelter Capacity Multipliers
        for s_id, mult in scenario.shelter_capacity_multipliers.items():
            for s in self.shelters:
                if s.id == s_id:
                    s.total_capacity = int(s.total_capacity * mult)
                    s.quarantine_beds_total = int(s.quarantine_beds_total * mult)
                    if s.occupancy_pct >= 98.0:
                        s.status = "FULL"

        # 3. Hazard Radius Multiplier
        self.epidemic_model.update_road_hazard_exposure(
            list(self.graph_mgr.edges_dict.values()),
            self.zones,
            self.graph_mgr.nodes_dict,
            hazard_expansion_multiplier=scenario.hazard_radius_multiplier
        )

        # 4. Evacuation Speed Multiplier
        self.speed_multiplier = scenario.evacuation_speed_multiplier

        # Re-compute metrics and re-route agents affected by closures
        self.graph_mgr.recompute_all_edge_metrics()
        self.reroute_all_agents()

    def reroute_all_agents(self):
        """Re-routes all in-transit agents using the updated graph."""
        for agent in self.agents:
            if agent.status == "in_transit":
                self.router.optimize_agent_route(agent, self.shelters)

    def reset(self):
        """Resets simulation to initial state."""
        self.tick_count = 0
        self.elapsed_sim_minutes = 0.0
        self.is_running = False
        self.speed_multiplier = 1.0
        self.active_scenario = None
        self.graph_mgr.load_network()
        self.load_initial_data()
        self.initialize_state()
