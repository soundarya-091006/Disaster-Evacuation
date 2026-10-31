"""
TwinEvac - Weather & Environmental Simulation API Routes
Endpoints for monitoring and interactively modulating disaster weather conditions and rainfall.
"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, Dict, Any

from app.core.weather_service import weather_service
from app.engine.rolling_optimizer import rolling_optimizer

router = APIRouter(prefix="/environment", tags=["Environmental & Weather Simulation"])


class WeatherUpdateRequest(BaseModel):
    rainfall_intensity_mmh: float
    condition: Optional[str] = None


@router.get("/weather")
def get_current_weather() -> Dict[str, Any]:
    """Returns current weather state and flood surge scale."""
    return weather_service.get_state()


@router.post("/weather")
def update_weather(req: WeatherUpdateRequest) -> Dict[str, Any]:
    """Updates live rainfall intensity, recalibrates flood depths across roads, and broadcasts update."""
    state = rolling_optimizer.update_weather(req.rainfall_intensity_mmh, req.condition)
    return {
        "status": "UPDATED",
        "weather": weather_service.get_state(),
        "active_bottlenecks": state.active_bottlenecks_count,
        "estimated_evacuation_time_minutes": state.estimated_evacuation_time_minutes
    }
