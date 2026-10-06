"""
TwinEvac - Graph Manager
Manages the directed geospatial road network in NetworkX, calculates BPR travel times,
handles edge modifications, closures, and hazard cost weightings.
"""

import json
import math
from typing import Dict, List, Optional, Tuple, Any
import networkx as nx

from app.core.config import settings
from app.schemas.models import RoadNode, RoadSegment, Coordinate


class GraphManager:
    def __init__(self, network_path: Optional[str] = None):
        self.network_path = network_path or str(settings.SALEM_NETWORK_PATH)
        self.graph = nx.DiGraph()
        self.nodes_dict: Dict[str, RoadNode] = {}
        self.edges_dict: Dict[str, RoadSegment] = {}
        self.raw_data: Dict[str, Any] = {}
        self.load_network()

    def load_network(self):
        """Loads and builds directed graph from the JSON network specification."""
        with open(self.network_path, "r", encoding="utf-8") as f:
            self.raw_data = json.load(f)

        self.graph.clear()
        self.nodes_dict.clear()
        self.edges_dict.clear()

        # Add Nodes
        for n_data in self.raw_data.get("nodes", []):
            node = RoadNode(
                id=n_data["id"],
                name=n_data["name"],
                lat=n_data["lat"],
                lng=n_data["lng"],
                type=n_data.get("type", "intersection")
            )
            self.nodes_dict[node.id] = node
            self.graph.add_node(node.id, data=node, lat=node.lat, lng=node.lng, name=node.name)

        # Add Edges (each street has directional flow; major arterials allow bi-directional movement)
        for e_data in self.raw_data.get("edges", []):
            # Forward edge
            fwd_segment = RoadSegment(
                id=e_data["id"],
                source=e_data["source"],
                target=e_data["target"],
                name=e_data["name"],
                distance_km=float(e_data["distance_km"]),
                lanes=int(e_data.get("lanes", 2)),
                free_flow_speed_kmh=float(e_data.get("free_flow_speed_kmh", 45.0)),
                capacity_pcu_per_hour=float(e_data.get("capacity_pcu_per_hour", 1800.0)),
                current_volume=0.0,
                current_speed_kmh=float(e_data.get("free_flow_speed_kmh", 45.0)),
                congestion_index=0.0,
                risk_level="LOW",
                flood_depth_cm=0.0,
                contagion_exposure_score=0.0,
                is_closed=False,
                is_one_way=e_data.get("is_one_way", False),
                bottleneck_severity=0.0
            )
            self.edges_dict[fwd_segment.id] = fwd_segment
            self._add_graph_edge(fwd_segment)

            # Reverse edge (unless strictly one-way)
            if not fwd_segment.is_one_way:
                rev_id = f"{fwd_segment.id}_REV"
                rev_segment = RoadSegment(
                    id=rev_id,
                    source=e_data["target"],
                    target=e_data["source"],
                    name=f"{e_data['name']} (Opposite)",
                    distance_km=float(e_data["distance_km"]),
                    lanes=int(e_data.get("lanes", 2)),
                    free_flow_speed_kmh=float(e_data.get("free_flow_speed_kmh", 45.0)),
                    capacity_pcu_per_hour=float(e_data.get("capacity_pcu_per_hour", 1800.0)),
                    current_volume=0.0,
                    current_speed_kmh=float(e_data.get("free_flow_speed_kmh", 45.0)),
                    congestion_index=0.0,
                    risk_level="LOW",
                    flood_depth_cm=0.0,
                    contagion_exposure_score=0.0,
                    is_closed=False,
                    is_one_way=False,
                    bottleneck_severity=0.0
                )
                self.edges_dict[rev_id] = rev_segment
                self._add_graph_edge(rev_segment)

        self.recompute_all_edge_metrics()

    def _add_graph_edge(self, segment: RoadSegment):
        free_flow_time_min = (segment.distance_km / max(segment.free_flow_speed_kmh, 1.0)) * 60.0
        self.graph.add_edge(
            segment.source,
            segment.target,
            id=segment.id,
            distance_km=segment.distance_km,
            free_flow_time_min=free_flow_time_min,
            effective_time_min=free_flow_time_min,
            capacity=segment.capacity_pcu_per_hour,
            volume=0.0,
            cost=free_flow_time_min,
            is_closed=segment.is_closed,
            risk_level=segment.risk_level
        )

    def calculate_bpr_travel_time(self, distance_km: float, free_flow_speed_kmh: float, volume: float, capacity: float) -> Tuple[float, float, float]:
        """
        Calculates effective travel time using the Bureau of Public Roads (BPR) function:
        T = T0 * (1 + alpha * (V / C)^beta)
        Returns: (travel_time_minutes, current_speed_kmh, congestion_index)
        """
        base_time_min = (distance_km / max(free_flow_speed_kmh, 5.0)) * 60.0
        vc_ratio = max(0.0, volume / max(capacity, 100.0))
        
        # BPR calculation
        travel_time_min = base_time_min * (1.0 + settings.BPR_ALPHA * math.pow(vc_ratio, settings.BPR_BETA))
        
        # Speed derived from travel time
        current_speed_kmh = (distance_km / max(travel_time_min / 60.0, 0.001))
        current_speed_kmh = max(3.0, min(free_flow_speed_kmh, current_speed_kmh))
        
        # Congestion index from 0.0 (empty) to 1.0 (jammed)
        # vc_ratio = 1.0 => congestion ~ 0.5-0.6, vc_ratio > 1.5 => ~ 1.0
        congestion_index = min(1.0, vc_ratio / 1.6)
        
        return travel_time_min, current_speed_kmh, congestion_index

    def calculate_edge_cost(self, segment: RoadSegment, travel_time_min: float) -> float:
        """
        Calculates dynamic evacuation traversal cost incorporating travel time,
        congestion delay, and disease/flood hazard penalties.
        """
        if segment.is_closed:
            return 999999.0

        risk_multipliers = {
            "LOW": 1.0,
            "MEDIUM": 1.5,
            "HIGH": 3.0,
            "CRITICAL": 10.0
        }
        risk_mult = risk_multipliers.get(segment.risk_level, 1.0)
        
        # Flood penalty: exponentially increases with depth
        flood_penalty = 1.0 + (segment.flood_depth_cm / 20.0) ** 1.8 if segment.flood_depth_cm > 0 else 1.0
        
        # Contagion penalty: penalize routing uninfected evacuees through high-viral corridors
        contagion_penalty = 1.0 + (segment.contagion_exposure_score * settings.WEIGHT_CONTAGION_EXPOSURE)

        total_cost = travel_time_min * risk_mult * flood_penalty * contagion_penalty
        return total_cost

    def update_edge_flow(self, edge_id: str, added_volume: float):
        """Updates current volume of a segment and recalculates metrics."""
        if edge_id in self.edges_dict:
            seg = self.edges_dict[edge_id]
            seg.current_volume = max(0.0, added_volume)
            self._update_single_edge_metrics(seg)

    def set_edge_hazard(self, edge_id: str, flood_depth_cm: float, contagion_score: float, is_closed: bool = False):
        """Applies flood depth, contagion exposure, or road closure to an edge."""
        if edge_id in self.edges_dict:
            seg = self.edges_dict[edge_id]
            seg.flood_depth_cm = flood_depth_cm
            seg.contagion_exposure_score = min(1.0, max(0.0, contagion_score))
            seg.is_closed = is_closed
            self._update_single_edge_metrics(seg)

    def _update_single_edge_metrics(self, seg: RoadSegment):
        t_time, speed, cong = self.calculate_bpr_travel_time(
            seg.distance_km, seg.free_flow_speed_kmh, seg.current_volume, seg.capacity_pcu_per_hour
        )
        seg.current_speed_kmh = round(speed, 1)
        seg.congestion_index = round(cong, 3)

        # Risk classification
        if seg.is_closed or seg.flood_depth_cm > 40.0 or (seg.contagion_exposure_score > 0.85 and seg.congestion_index > 0.7):
            seg.risk_level = "CRITICAL"
        elif seg.flood_depth_cm > 20.0 or seg.contagion_exposure_score > 0.6 or seg.congestion_index > 0.8:
            seg.risk_level = "HIGH"
        elif seg.flood_depth_cm > 5.0 or seg.contagion_exposure_score > 0.3 or seg.congestion_index > 0.5:
            seg.risk_level = "MEDIUM"
        else:
            seg.risk_level = "LOW"

        # Bottleneck severity
        if seg.congestion_index > settings.BOTTLENECK_CONGESTION_THRESHOLD or seg.flood_depth_cm > 25.0:
            seg.bottleneck_severity = round(min(1.0, (seg.congestion_index - 0.5) * 2.0), 2)
        else:
            seg.bottleneck_severity = 0.0

        cost = self.calculate_edge_cost(seg, t_time)

        if self.graph.has_edge(seg.source, seg.target):
            self.graph[seg.source][seg.target]["effective_time_min"] = t_time
            self.graph[seg.source][seg.target]["cost"] = cost
            self.graph[seg.source][seg.target]["is_closed"] = seg.is_closed
            self.graph[seg.source][seg.target]["volume"] = seg.current_volume
            self.graph[seg.source][seg.target]["risk_level"] = seg.risk_level

    def recompute_all_edge_metrics(self):
        """Refreshes all edges in graph and schema dictionaries."""
        for seg in self.edges_dict.values():
            self._update_single_edge_metrics(seg)

    def get_shortest_path(self, origin: str, destination: str, weight: str = "cost") -> Optional[List[str]]:
        """Computes optimal path between origin node and destination node."""
        if not self.graph.has_node(origin) or not self.graph.has_node(destination):
            return None
        try:
            path = nx.shortest_path(self.graph, source=origin, target=destination, weight=weight)
            return path
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return None

    def get_path_edges(self, path_nodes: List[str]) -> List[str]:
        """Converts a sequence of node IDs into a list of road edge IDs."""
        edge_ids = []
        for i in range(len(path_nodes) - 1):
            u, v = path_nodes[i], path_nodes[i + 1]
            if self.graph.has_edge(u, v):
                edge_ids.append(self.graph[u][v]["id"])
        return edge_ids

    def clone(self) -> 'GraphManager':
        """Deep clones the GraphManager instance for What-If scenario isolation."""
        import copy
        new_mgr = GraphManager.__new__(GraphManager)
        new_mgr.network_path = self.network_path
        new_mgr.raw_data = copy.deepcopy(self.raw_data)
        new_mgr.nodes_dict = {k: v.model_copy(deep=True) for k, v in self.nodes_dict.items()}
        new_mgr.edges_dict = {k: v.model_copy(deep=True) for k, v in self.edges_dict.items()}
        new_mgr.graph = self.graph.copy()
        return new_mgr
