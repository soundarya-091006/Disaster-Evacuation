"""
TwinEvac - Environmental & Weather Ingestion Service
Tracks live/simulated meteorological feeds (rainfall intensity, wind speed, inundation surge),
and applies dynamic precipitation runoff to road network segments.
"""

from typing import Dict, Any, List, Optional
from app.schemas.models import RoadSegment


class WeatherService:
    _instance: Optional["WeatherService"] = None

    def __init__(self):
        self.rainfall_intensity_mmh: float = 35.0
        self.wind_speed_kmh: float = 26.0
        self.temperature_c: float = 27.5
        self.condition: str = "Monsoon Precipitation (35 mm/h)"
        self.flood_surge_scale: float = 1.15

        # Base flood susceptibility per edge ID
        self.flood_susceptibility: Dict[str, float] = {
            "EDGE_4ROADS_SHEVAPET": 1.4,
            "EDGE_4ROADS_SHEVAPET_REV": 1.4,
            "EDGE_SHEVAPET_GUGAI": 1.6,
            "EDGE_SHEVAPET_GUGAI_REV": 1.6,
            "EDGE_GUGAI_GMKMC": 1.1,
            "EDGE_GUGAI_GMKMC_REV": 1.1,
            "EDGE_SHEVAPET_ANNADHAN": 1.2,
            "EDGE_SHEVAPET_ANNADHAN_REV": 1.2,
            "EDGE_MEYYANUR_4ROADS": 0.8,
            "EDGE_MEYYANUR_4ROADS_REV": 0.8,
            "EDGE_4ROADS_GMKMC": 0.7,
            "EDGE_4ROADS_GMKMC_REV": 0.7,
            "EDGE_GUGAI_SEELANAIKEN": 0.9,
            "EDGE_GUGAI_SEELANAIKEN_REV": 0.9,
        }

    @classmethod
    def get_instance(cls) -> "WeatherService":
        if cls._instance is None:
            cls._instance = WeatherService()
        return cls._instance

    def set_weather(self, rainfall_mmh: float, condition: Optional[str] = None):
        """Updates rainfall intensity and recalibrates flood surge scale."""
        self.rainfall_intensity_mmh = max(0.0, min(150.0, rainfall_mmh))
        self.flood_surge_scale = max(0.1, round(self.rainfall_intensity_mmh / 30.0, 2))

        if condition:
            self.condition = condition
        else:
            if self.rainfall_intensity_mmh < 5.0:
                self.condition = "Clear Skies (Dry Conditions)"
            elif self.rainfall_intensity_mmh < 22.0:
                self.condition = f"Light Showers ({self.rainfall_intensity_mmh:.0f} mm/h)"
            elif self.rainfall_intensity_mmh < 48.0:
                self.condition = f"Monsoon Precipitation ({self.rainfall_intensity_mmh:.0f} mm/h)"
            elif self.rainfall_intensity_mmh < 80.0:
                self.condition = f"Severe Torrential Downpour ({self.rainfall_intensity_mmh:.0f} mm/h)"
            else:
                self.condition = f"Extreme Flash Flood Inundation ({self.rainfall_intensity_mmh:.0f} mm/h)"

    def update_road_flood_depths(self, roads: List[RoadSegment]):
        """
        Dynamically adjusts flood depth (cm) on each road segment
        based on current rainfall intensity and geological susceptibility.
        """
        for road in roads:
            susceptibility = self.flood_susceptibility.get(road.id, 0.25)
            # Base flood depth calculation:
            # 0 mm/h -> 0 cm
            # 35 mm/h -> ~20-30 cm on vulnerable roads
            # 80 mm/h -> ~45-55 cm on vulnerable roads
            new_depth = (self.rainfall_intensity_mmh * 0.55) * susceptibility
            road.flood_depth_cm = round(max(0.0, min(80.0, new_depth)), 1)

    def get_state(self) -> Dict[str, Any]:
        """Returns meteorological telemetry payload."""
        return {
            "rainfall_intensity_mmh": self.rainfall_intensity_mmh,
            "wind_speed_kmh": self.wind_speed_kmh,
            "temperature_c": self.temperature_c,
            "condition": self.condition,
            "flood_surge_scale": self.flood_surge_scale
        }


# Global singleton
weather_service = WeatherService.get_instance()
