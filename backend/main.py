from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text
from routing import find_route

from database import engine, Base, SessionLocal
import models

app = FastAPI(title="TwinEvac API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
Base.metadata.create_all(bind=engine)


@app.get("/")
def home():
    return {
        "message": "TwinEvac backend is running"
    }


@app.get("/shelters")
def get_shelters():
    db: Session = SessionLocal()

    try:
        result = db.execute(
            text("""
                SELECT
                    id,
                    name,
                    capacity,
                    current_population,
                    is_open,
                    ST_Y(location) AS latitude,
                    ST_X(location) AS longitude
                FROM shelters
            """)
        )

        return [
            {
                "id": row.id,
                "name": row.name,
                "capacity": row.capacity,
                "current_population": row.current_population,
                "is_open": row.is_open,
                "latitude": row.latitude,
                "longitude": row.longitude
            }
            for row in result
        ]

    finally:
        db.close()


@app.get("/roads")
def get_roads():
    db: Session = SessionLocal()

    try:
        result = db.execute(
            text("""
                SELECT
                    id,
                    name,
                    capacity,
                    is_blocked,
                    ST_AsGeoJSON(geometry) AS geometry
                FROM roads
            """)
        )

        return [
            {
                "id": row.id,
                "name": row.name,
                "capacity": row.capacity,
                "is_blocked": row.is_blocked,
                "geometry": row.geometry
            }
            for row in result
        ]

    finally:
        db.close()


@app.get("/disaster-zones")
def get_disaster_zones():
    db: Session = SessionLocal()

    try:
        result = db.execute(
            text("""
                SELECT
                    id,
                    disaster_type,
                    severity,
                    is_active,
                    ST_AsGeoJSON(geometry) AS geometry
                FROM disaster_zones
            """)
        )

        return [
            {
                "id": row.id,
                "disaster_type": row.disaster_type,
                "severity": row.severity,
                "is_active": row.is_active,
                "geometry": row.geometry
            }
            for row in result
        ]

    finally:
        db.close()

@app.get("/dashboard/stats")
def get_dashboard_stats():
    db: Session = SessionLocal()

    try:
        shelter_result = db.execute(
            text("""
                SELECT
                    COUNT(*) AS total_shelters,
                    COUNT(*) FILTER (WHERE is_open = TRUE) AS open_shelters,
                    COALESCE(SUM(current_population), 0) AS shelter_population
                FROM shelters
            """)
        ).mappings().one()

        road_result = db.execute(
            text("""
                SELECT
                    COUNT(*) AS total_roads,
                    COUNT(*) FILTER (WHERE is_blocked = TRUE) AS blocked_roads
                FROM roads
            """)
        ).mappings().one()

        disaster_result = db.execute(
            text("""
                SELECT
                    COUNT(*) FILTER (WHERE is_active = TRUE) AS active_disasters,
                    COALESCE(MAX(severity), 0) AS max_severity
                FROM disaster_zones
            """)
        ).mappings().one()

        return {
            "shelters": {
                "total": shelter_result["total_shelters"],
                "open": shelter_result["open_shelters"],
                "population": shelter_result["shelter_population"]
            },
            "roads": {
                "total": road_result["total_roads"],
                "blocked": road_result["blocked_roads"]
            },
            "disaster": {
                "active": disaster_result["active_disasters"],
                "max_severity": disaster_result["max_severity"]
            }
        }

    finally:
        db.close()

@app.get("/route")
def get_route(
    start_lat: float,
    start_lon: float,
    destination_lat: float,
    destination_lon: float
):
    start = (start_lat, start_lon)
    destination = (destination_lat, destination_lon)

    return find_route(start, destination)

@app.post("/roads/{road_id}/block")
def block_road(road_id: int):

    db: Session = SessionLocal()

    try:
        result = db.execute(
            text("""
                UPDATE roads
                SET is_blocked = TRUE
                WHERE id = :road_id
                RETURNING id, name, is_blocked
            """),
            {"road_id": road_id}
        )

        road = result.fetchone()

        db.commit()

        if road is None:
            return {
                "success": False,
                "message": "Road not found"
            }

        return {
            "success": True,
            "message": f"{road.name} has been blocked",
            "road_id": road.id,
            "road_name": road.name,
            "is_blocked": road.is_blocked
        }

    finally:
        db.close()
@app.post("/roads/{road_id}/unblock")
def unblock_road(road_id: int):

    db: Session = SessionLocal()

    try:
        result = db.execute(
            text("""
                UPDATE roads
                SET is_blocked = FALSE
                WHERE id = :road_id
                RETURNING id, name, is_blocked
            """),
            {"road_id": road_id}
        )

        road = result.fetchone()

        db.commit()

        if road is None:
            return {
                "success": False,
                "message": "Road not found"
            }

        return {
            "success": True,
            "message": f"{road.name} has been unblocked",
            "road_id": road.id,
            "road_name": road.name,
            "is_blocked": road.is_blocked
        }

    finally:
        db.close()