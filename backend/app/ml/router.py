"""
TwinEvac - Capacity-Constrained Dynamic Router
Calculates global evacuation routes minimizing Total Evacuation Time (TET)
and cross-infection exposure while dynamically preventing shelter overflow.
"""

from typing import Dict, List, Optional, Tuple
from app.core.graph_manager import GraphManager
from app.schemas.models import ShelterHospital, EvacuationAgent, RoadSegment


class EvacuationRouter:
    def __init__(self, graph_mgr: GraphManager):
        self.graph_mgr = graph_mgr

    def calculate_shelter_penalty(self, shelter: ShelterHospital, agent_needs_quarantine: bool = False) -> float:
        """
        Calculates a dynamic impedance penalty for a shelter based on current fill rate.
        Prevents funnelling crowds into a facility that is nearing capacity.
        """
        if shelter.status == "FULL" or shelter.status == "ISOLATED":
            return 99999.0

        if agent_needs_quarantine:
            occ_ratio = shelter.quarantine_beds_occupied / max(shelter.quarantine_beds_total, 1)
        else:
            occ_ratio = shelter.occupied / max(shelter.total_capacity, 1)

        if occ_ratio >= 0.95:
            return 250.0  # Massive deterrence
        elif occ_ratio >= 0.80:
            # Quadratic ramp up penalty
            normalized = (occ_ratio - 0.80) / 0.15
            return 15.0 + 35.0 * (normalized ** 2)
        elif occ_ratio >= 0.65:
            return 5.0 * ((occ_ratio - 0.65) / 0.15)
        else:
            return 0.0

    def find_best_evacuation_destination(
        self,
        origin_node_id: str,
        shelters: List[ShelterHospital],
        agent_needs_quarantine: bool = False
    ) -> Tuple[Optional[str], Optional[List[str]], float]:
        """
        Evaluates all reachable safe shelters and selects the one that minimizes:
        Total Cost = Path Traversal Cost + Shelter Congestion Penalty.
        Returns: (best_shelter_id, best_path_nodes, total_cost)
        """
        best_shelter_id: Optional[str] = None
        best_path: Optional[List[str]] = None
        min_total_cost = float("inf")

        for shelter in shelters:
            # Check quarantine capability if needed
            if agent_needs_quarantine and shelter.quarantine_beds_total <= 0:
                continue

            # Determine shelter access node (mapped by convention or ID)
            access_node = getattr(shelter, "access_node_id", None) or f"NODE_{shelter.id.replace('SHELTER_', '')}"
            if not self.graph_mgr.graph.has_node(access_node):
                # Fallback to direct name lookup or nearby node
                continue

            path = self.graph_mgr.get_shortest_path(origin_node_id, access_node, weight="cost")
            if not path:
                continue

            # Calculate path cumulative cost
            path_cost = 0.0
            for i in range(len(path) - 1):
                u, v = path[i], path[i + 1]
                path_cost += self.graph_mgr.graph[u][v].get("cost", 1.0)

            penalty = self.calculate_shelter_penalty(shelter, agent_needs_quarantine)
            total_candidate_cost = path_cost + penalty

            if total_candidate_cost < min_total_cost:
                min_total_cost = total_candidate_cost
                best_shelter_id = shelter.id
                best_path = path

        return best_shelter_id, best_path, min_total_cost

    def optimize_agent_route(
        self,
        agent: EvacuationAgent,
        shelters: List[ShelterHospital]
    ) -> bool:
        """
        Re-computes and assigns optimal route for an in-transit or waiting agent.
        Returns True if a valid route was assigned.
        """
        # Determine current origin node
        current_node = agent.route[0] if agent.route else None
        if not current_node:
            return False

        needs_quarantine = (agent.agent_type == "ambulance") or (agent.infection_exposure_accumulated > 0.4)

        best_shelter_id, best_path, _ = self.find_best_evacuation_destination(
            current_node, shelters, agent_needs_quarantine=needs_quarantine
        )

        if best_path and len(best_path) >= 2:
            agent.destination_shelter_id = best_shelter_id or agent.destination_shelter_id
            agent.route = best_path
            agent.route_edge_ids = self.graph_mgr.get_path_edges(best_path)
            if agent.route_edge_ids:
                agent.current_edge_id = agent.route_edge_ids[0]
            return True

        return False
