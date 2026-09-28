"""
TwinEvac - Simulation Control Endpoints
Start, pause, step forward, reset, and adjust simulation speed.
"""

from fastapi import APIRouter
from pydantic import BaseModel
from app.engine.rolling_optimizer import rolling_optimizer
from app.schemas.models import SimulationStepState

router = APIRouter(prefix="/sim", tags=["Simulation Control"])


class SpeedRequest(BaseModel):
    multiplier: float


@router.post("/start", response_model=dict)
def start_simulation():
    """Starts the continuous rolling simulation loop."""
    rolling_optimizer.start()
    return {"status": "started", "is_running": True}


@router.post("/pause", response_model=dict)
def pause_simulation():
    """Pauses the simulation."""
    rolling_optimizer.pause()
    return {"status": "paused", "is_running": False}


@router.post("/step", response_model=SimulationStepState)
def step_simulation():
    """Manually steps the simulation forward by one interval."""
    return rolling_optimizer.step_once()


@router.post("/reset", response_model=SimulationStepState)
def reset_simulation():
    """Resets the simulation to the initial benchmark baseline."""
    return rolling_optimizer.reset()


@router.post("/speed", response_model=dict)
def set_simulation_speed(req: SpeedRequest):
    """Adjusts the simulation speed multiplier (0.5x to 10.0x)."""
    rolling_optimizer.set_speed(req.multiplier)
    return {"status": "success", "speed_multiplier": rolling_optimizer.sim.speed_multiplier}
