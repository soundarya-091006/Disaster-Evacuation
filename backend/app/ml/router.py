"""
TwinEvac - Capacity-Constrained Dynamic Router with Reinforcement Learning
Calculates global evacuation routes minimizing Total Evacuation Time (TET)
and cross-infection exposure while dynamically preventing shelter overflow using
graph A* search guided by trained Q-learning policy values.
"""

from typing import List, Optional, Tuple
from app.core.graph_manager import GraphManager
from app.schemas.models import ShelterHospital, EvacuationAgent
from app.ml.ml_service import ml_service


class EvacuationRouter:
    def __init__(self, graph_mgr: GraphManager):
        self.graph_mgr = graph_mgr

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def access_node(shelter: ShelterHospital) -> str:
        """Road-network node used to enter a shelter (data field, with naming fallback)."""
        return shelter.access_node_id or f"NODE_{shelter.id.replace('SHELTER_', '')}"

    def _path_cost(self, path: List[str]) -> float:
        cost = 0.0
        for u, v in zip(path[:-1], path[1:]):
            cost += self.graph_mgr.graph[u][v].get("cost", 1.0)
        return cost

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

    # ------------------------------------------------------------------
    # Destination selection
    # ------------------------------------------------------------------
    def find_best_evacuation_destination(
        self,
        origin_node_id: str,
        shelters: List[ShelterHospital],
        agent_needs_quarantine: bool = False,
        allow_full: bool = True,
    ) -> Tuple[Optional[str], Optional[List[str]], float]:
        """
        Evaluates all reachable safe shelters and selects the one that minimizes:
        Total Cost = Path Traversal Cost + Shelter Congestion Penalty - RL Policy Incentive.
        When allow_full is False, FULL / ISOLATED facilities are never chosen.
        Returns: (best_shelter_id, best_path_nodes, total_cost)
        """
        best_shelter_id: Optional[str] = None
        best_path: Optional[List[str]] = None
        min_total_cost = float("inf")

        for shelter in shelters:
            if agent_needs_quarantine and shelter.quarantine_beds_total <= 0:
                continue
            if not allow_full and shelter.status in ("FULL", "ISOLATED"):
                continue

            access_node = self.access_node(shelter)
            if not self.graph_mgr.graph.has_node(access_node):
                continue

            path = self.graph_mgr.get_shortest_path(origin_node_id, access_node, weight="cost")
            if not path:
                continue

            penalty = self.calculate_shelter_penalty(shelter, agent_needs_quarantine)
            base_cost = self._path_cost(path)

            # Apply Q-Learning policy incentive for dynamic load balancing
            next_hop = path[1] if len(path) > 1 else path[0]
            q_bonus = ml_service.get_q_value(origin_node_id, next_hop, access_node) * 0.12
            total_candidate_cost = base_cost + penalty - max(0.0, min(15.0, q_bonus))

            if total_candidate_cost < min_total_cost:
                min_total_cost = total_candidate_cost
                best_shelter_id = shelter.id
                best_path = path

        return best_shelter_id, best_path, min_total_cost

    def best_path_cost(self, origin_node_id: str, shelters: List[ShelterHospital]) -> Optional[float]:
        """Cheapest pure traversal cost from an origin to any shelter (None if cut off)."""
        best: Optional[float] = None
        for shelter in shelters:
            node = self.access_node(shelter)
            if not self.graph_mgr.graph.has_node(node):
                continue
            path = self.graph_mgr.get_shortest_path(origin_node_id, node, weight="cost")
            if not path:
                continue
            cost = self._path_cost(path)
            if best is None or cost < best:
                best = cost
        return best

    # ------------------------------------------------------------------
    # Re-routing of agents
    # ------------------------------------------------------------------
    def optimize_agent_route(
        self,
        agent: EvacuationAgent,
        shelters: List[ShelterHospital]
    ) -> bool:
        """
        Re-plans an in-transit agent FROM ITS CURRENT POSITION.
        The agent finishes the road segment it is on (keeping its progress),
        then follows a freshly computed best route from that segment's end node.
        Returns True if a new route was assigned; otherwise the old route is kept.
        """
        cur_edge = self.graph_mgr.edges_dict.get(agent.current_edge_id)
        if cur_edge is not None:
            current_node = cur_edge.target
            prefix_nodes = [cur_edge.source]
            prefix_edges = [cur_edge.id]
        else:
            current_node = agent.route[0] if agent.route else None
            prefix_nodes, prefix_edges = [], []
        if not current_node:
            return False

        needs_quarantine = (agent.agent_type == "ambulance") or (agent.infection_exposure_accumulated > 0.4)

        best_shelter_id, best_path, _ = self.find_best_evacuation_destination(
            current_node, shelters, agent_needs_quarantine=needs_quarantine, allow_full=False
        )
        if not best_path:
            return False

        edge_ids = prefix_edges + self.graph_mgr.get_path_edges(best_path)
        if not edge_ids:
            return False

        agent.destination_shelter_id = best_shelter_id or agent.destination_shelter_id
        agent.route = prefix_nodes + best_path
        agent.route_edge_ids = edge_ids
        agent.current_edge_id = edge_ids[0]  # progress_on_edge is intentionally preserved
        return True

    def reroute_from_node(
        self,
        agent: EvacuationAgent,
        node_id: str,
        shelters: List[ShelterHospital],
    ) -> bool:
        """Plans a brand-new route for an agent standing at a node (e.g. turned away from a full shelter)."""
        needs_quarantine = (agent.agent_type == "ambulance") or (agent.infection_exposure_accumulated > 0.4)
        shelter_id, path, _ = self.find_best_evacuation_destination(
            node_id, shelters, agent_needs_quarantine=needs_quarantine, allow_full=False
        )
        if not path or len(path) < 2:
            return False
        edge_ids = self.graph_mgr.get_path_edges(path)
        if not edge_ids:
            return False
        agent.destination_shelter_id = shelter_id or agent.destination_shelter_id
        agent.route = path
        agent.route_edge_ids = edge_ids
        agent.current_edge_id = edge_ids[0]
        agent.progress_on_edge = 0.0
        return True
