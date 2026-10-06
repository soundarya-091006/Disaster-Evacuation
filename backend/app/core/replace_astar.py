from pathlib import Path

path = Path("graph_manager.py")
text = path.read_text(encoding="utf-8")

old = '''    def get_shortest_path(self, origin: str, destination: str, weight: str = "cost") -> Optional[List[str]]:
        """Computes optimal path between origin node and destination node."""
        if not self.graph.has_node(origin) or not self.graph.has_node(destination):
            return None
        try:
            path = nx.shortest_path(self.graph, source=origin, target=destination, weight=weight)
            return path
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return None
'''

new = '''    def get_shortest_path(self, origin: str, destination: str, weight: str = "cost") -> Optional[List[str]]:
        """Computes an optimal path using A* with an admissible geographic heuristic."""
        if not self.graph.has_node(origin) or not self.graph.has_node(destination):
            return None

        # A* heuristic must use the same units as the edge weight.
        # For the default "cost", edge costs are based on travel time in minutes
        # multiplied by penalties >= 1, so straight-line minimum travel time
        # is an admissible lower bound.

        if weight != "cost":
            heuristic = lambda _u, _v: 0.0
        else:
            max_speed_kmh = max(
                (
                    segment.free_flow_speed_kmh
                    for segment in self.edges_dict.values()
                    if segment.free_flow_speed_kmh > 0
                ),
                default=1.0,
            )

            def heuristic(u: str, v: str) -> float:
                node_u = self.nodes_dict.get(u)
                node_v = self.nodes_dict.get(v)

                if not node_u or not node_v:
                    return 0.0

                lat1 = math.radians(node_u.latitude)
                lon1 = math.radians(node_u.longitude)
                lat2 = math.radians(node_v.latitude)
                lon2 = math.radians(node_v.longitude)

                dlat = lat2 - lat1
                dlon = lon2 - lon1

                a = (
                    math.sin(dlat / 2) ** 2
                    + math.cos(lat1)
                    * math.cos(lat2)
                    * math.sin(dlon / 2) ** 2
                )

                distance_km = 6371.0 * 2 * math.asin(math.sqrt(a))

                return (distance_km / max_speed_kmh) * 60.0

        try:
            return nx.astar_path(
                self.graph,
                source=origin,
                target=destination,
                heuristic=heuristic,
                weight=weight,
            )
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return None
'''

if old not in text:
    raise SystemExit("ERROR: Original get_shortest_path block was not found.")

path.write_text(text.replace(old, new), encoding="utf-8")
print("A* replacement applied successfully.")
