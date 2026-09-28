import argparse
import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from sqlalchemy import text

from database import SessionLocal


ROAD_CAPACITY = {
    "motorway": 1800,
    "motorway_link": 1200,
    "trunk": 1400,
    "trunk_link": 1000,
    "primary": 1000,
    "primary_link": 800,
    "secondary": 800,
    "secondary_link": 650,
    "tertiary": 600,
    "tertiary_link": 500,
    "unclassified": 400,
    "residential": 400,
    "living_street": 200,
    "service": 250,
    "road": 300,
}

ROAD_TYPES = "|".join(ROAD_CAPACITY)


def build_query(bbox):
    south, west, north, east = bbox
    return (
        "[out:json][timeout:60];"
        f'way["highway"~"^({ROAD_TYPES})$"]'
        f"({south},{west},{north},{east});"
        "out tags geom;"
    )


def parse_ways(elements):
    roads = []

    for element in elements:
        tags = element.get("tags", {})
        road_type = tags.get("highway")
        geometry = element.get("geometry", [])

        if road_type not in ROAD_CAPACITY or len(geometry) < 2:
            continue

        coordinates = [
            [point["lon"], point["lat"]]
            for point in geometry
        ]
        roads.append({
            "name": tags.get("name") or f"{road_type.title()} {element['id']}",
            "capacity": ROAD_CAPACITY[road_type],
            "geometry": json.dumps({
                "type": "LineString",
                "coordinates": coordinates,
            }),
        })

    return roads


def fetch_ways(bbox, endpoint):
    body = urlencode({"data": build_query(bbox)}).encode("utf-8")
    request = Request(
        endpoint,
        data=body,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "TwinEvac/0.1 (open-data road import)",
        },
        method="POST",
    )

    try:
        with urlopen(request, timeout=75) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError) as error:
        raise RuntimeError(f"Overpass request failed: {error}") from error

    return parse_ways(payload.get("elements", []))


def import_roads(roads, replace_existing=False):
    if not roads:
        raise ValueError("No routable roads were returned; database was not changed.")

    db = SessionLocal()
    try:
        if replace_existing:
            db.execute(text("DELETE FROM roads"))

        db.execute(
            text("""
                INSERT INTO roads (name, capacity, is_blocked, geometry)
                VALUES (
                    :name,
                    :capacity,
                    FALSE,
                    ST_SetSRID(ST_GeomFromGeoJSON(:geometry), 4326)
                )
            """),
            roads,
        )
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(
        description="Import routable OpenStreetMap ways into TwinEvac's roads table."
    )
    parser.add_argument(
        "--bbox",
        nargs=4,
        type=float,
        metavar=("SOUTH", "WEST", "NORTH", "EAST"),
        default=(11.65, 78.13, 11.69, 78.18),
        help="Bounding box; defaults to the Salem sample area.",
    )
    parser.add_argument(
        "--overpass-url",
        default="https://overpass-api.de/api/interpreter",
        help="Overpass API interpreter endpoint.",
    )
    parser.add_argument(
        "--replace-existing",
        action="store_true",
        help="Delete existing roads before importing. Without this, roads are appended.",
    )
    args = parser.parse_args()

    south, west, north, east = args.bbox
    if south >= north or west >= east:
        parser.error("bbox must satisfy SOUTH < NORTH and WEST < EAST")

    try:
        roads = fetch_ways(args.bbox, args.overpass_url)
        import_roads(roads, replace_existing=args.replace_existing)
    except (RuntimeError, ValueError) as error:
        parser.error(str(error))

    action = "replaced existing roads with" if args.replace_existing else "appended"
    print(f"Successfully {action} {len(roads)} OSM road ways.")


if __name__ == "__main__":
    main()