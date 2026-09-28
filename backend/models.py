from sqlalchemy import Column, Integer, String, Float, Boolean
from geoalchemy2 import Geometry

from database import Base


class Shelter(Base):
    __tablename__ = "shelters"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    capacity = Column(Integer, nullable=False)
    current_population = Column(Integer, default=0)
    is_open = Column(Boolean, default=True)

    location = Column(
        Geometry("POINT", srid=4326),
        nullable=False
    )


class Road(Base):
    __tablename__ = "roads"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    capacity = Column(Integer, default=100)
    is_blocked = Column(Boolean, default=False)

    geometry = Column(
        Geometry("LINESTRING", srid=4326),
        nullable=False
    )


class DisasterZone(Base):
    __tablename__ = "disaster_zones"

    id = Column(Integer, primary_key=True, index=True)
    disaster_type = Column(String, nullable=False)
    severity = Column(Float, default=0.0)
    is_active = Column(Boolean, default=True)

    geometry = Column(
        Geometry("POLYGON", srid=4326),
        nullable=False
    )