from pydantic import BaseModel


class ShelterResponse(BaseModel):
    id: int
    name: str
    capacity: int
    current_population: int
    is_open: bool


class RoadResponse(BaseModel):
    id: int
    name: str
    capacity: int
    is_blocked: bool


class DisasterZoneResponse(BaseModel):
    id: int
    disaster_type: str
    severity: float
    is_active: bool