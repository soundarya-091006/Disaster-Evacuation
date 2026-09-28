import math
import networkx as nx

from sqlalchemy import text

from database import SessionLocal


def calculate_distance(point1, point2):
    """Calculate distance between two latitude/longitude points."""

    lat1, lon1 = point1
    lat2, lon2 = point2

    earth_radius = 6371000

    lat1 = math.radians(lat1)
    lat2 = math.radians(lat2)

    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1)
        * math.cos(lat2)
        * math.sin(delta_lon / 2) ** 2
    )

    c = 2 * math.atan2(
        math.sqrt(a),
        math.sqrt(1 - a)
    )

    return earth_radius * c


def heuristic(node, destination):
    """A* straight-line distance heuristic."""
    return calculate_distance(node, destination)


def find_route(start, destination):

    graph = nx.Graph()

    db = SessionLocal()

    try:

        # Get roads from PostGIS
        result = db.execute(
            text("""
                SELECT
                    id,
                    name,
                    is_blocked,
                    ST_AsGeoJSON(geometry) AS geometry
                FROM roads
            """)
        )

        for row in result:

            # Ignore blocked roads
            if row.is_blocked:
                continue

            geometry = row.geometry

            coordinates = geometry["coordinates"] \
                if isinstance(geometry, dict) \
                else __import__("json").loads(geometry)["coordinates"]

            # Add every road segment to graph
            for i in range(len(coordinates) - 1):

                lon1, lat1 = coordinates[i]
                lon2, lat2 = coordinates[i + 1]

                point1 = (lat1, lon1)
                point2 = (lat2, lon2)

                distance = calculate_distance(
                    point1,
                    point2
                )

                graph.add_edge(
                    point1,
                    point2,
                    weight=distance,
                    road=row.name
                )

    finally:
        db.close()

    # Check whether start and destination exist
    if start not in graph:
        return {
            "algorithm": "A*",
            "route": [],
            "distance_meters": None,
            "message": "Start point is not a road node"
        }

    if destination not in graph:
        return {
            "algorithm": "A*",
            "route": [],
            "distance_meters": None,
            "message": "Destination point is not a road node"
        }

    try:

        path = nx.astar_path(
            graph,
            source=start,
            target=destination,
            heuristic=heuristic,
            weight="weight"
        )

        distance = nx.astar_path_length(
            graph,
            source=start,
            target=destination,
            heuristic=heuristic,
            weight="weight"
        )

        return {
            "algorithm": "A*",
            "route": path,
            "distance_meters": round(distance, 2)
        }

    except nx.NetworkXNoPath:

        return {
            "algorithm": "A*",
            "route": [],
            "distance_meters": None,
            "message": "No route available"
        }