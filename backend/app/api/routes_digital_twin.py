"""
TwinEvac - Digital Twin Inspection Endpoints
Provides REST endpoints to query network nodes, road segments, shelters, and zones.
"""

from typing import List, Dict, Any
from fastapi import APIRouter
from app.engine.rolling_optimizer import rolling_optimizer
from app.schemas.models import (
    RoadNode, RoadSegment, ShelterHospital, EvacuationZone, SimulationStepState
)

router = APIRouter(prefix="/twin", tags=["Digital Twin"])


@router.get("/state", response_model=SimulationStepState)
def get_current_twin_state():
    """Returns complete real-time snapshot of the digital twin."""
    return rolling_optimizer.sim.get_current_state()


@router.get("/nodes", response_model=List[RoadNode])
def get_road_nodes():
    """Returns all geographic nodes and intersections in the network."""
    return list(rolling_optimizer.sim.graph_mgr.nodes_dict.values())


@router.get("/roads", response_model=List[RoadSegment])
def get_road_segments():
    """Returns all road segments with real-time congestion and risk tiers."""
    return list(rolling_optimizer.sim.graph_mgr.edges_dict.values())


@router.get("/shelters", response_model=List[ShelterHospital])
def get_shelters_and_hospitals():
    """Returns all designated emergency shelters, quarantine facilities, and bed occupancies."""
    return rolling_optimizer.sim.shelters


@router.get("/zones", response_model=List[EvacuationZone])
def get_evacuation_zones():
    """Returns all origin population sectors and active infection counts."""
    return rolling_optimizer.sim.zones
