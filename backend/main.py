from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text

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