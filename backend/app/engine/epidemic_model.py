"""
TwinEvac - Epidemic & Spatial Hazard Model
Models disease contagion hotspots (e.g. Shevapet / Gugai clusters) and flood inundation.
Calculates corridor exposure scores so routing algorithms divert crowds away from infection vectors.
"""

import math
from typing import List, Dict, Tuple, Any
from app.schemas.models import Coordinate, EvacuationZone, RoadSegment


class EpidemicHazardModel:
    def __init__(self):
        # Disease transmission parameters
        self.basic_reproduction_r0: float = 2.8
        self.airborne_radius_km: float = 1.2
        self.flood_expansion_rate: float = 1.05

    def calculate_distance_km(self, p1: Coordinate, p2: Coordinate) -> float:
        """Haversine distance in km between two lat/lng coordinates."""
        R = 6371.0  # Earth radius in km
        dlat = math.radians(p2.lat - p1.lat)
        dlng = math.radians(p2.lng - p1.lng)
        a = (
            math.sin(dlat / 2) ** 2 +
            math.cos(math.radians(p1.lat)) * math.cos(math.radians(p2.lat)) * math.sin(dlng / 2) ** 2
        )
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return R * c

    def update_road_hazard_exposure(
        self,
        roads: List[RoadSegment],
        zones: List[EvacuationZone],
        nodes_dict: Dict[str, Any],
        hazard_expansion_multiplier: float = 1.0
    ):
        """
        Calculates contagion exposure score and flood depth on each road segment
        based on proximity to high-infection zones and flood basins.
        """
        for road in roads:
            if road.is_closed:
                continue

            src_node = nodes_dict.get(road.source)
            tgt_node = nodes_dict.get(road.target)
            if not src_node or not tgt_node:
                continue

            # Road midpoint
            mid_coord = Coordinate(
                lat=(src_node.lat + tgt_node.lat) / 2.0,
                lng=(src_node.lng + tgt_node.lng) / 2.0
            )

            max_exposure = 0.0
            max_flood = 0.0

            for zone in zones:
                dist = self.calculate_distance_km(mid_coord, zone.center)
                effective_radius = self.airborne_radius_km * hazard_expansion_multiplier

                if dist < effective_radius:
                    # In proximity to hazard zone
                    decay = (1.0 - (dist / effective_radius)) ** 1.5
                    
                    # Contagion intensity based on active infections
                    infection_intensity = min(1.0, zone.active_infections / 300.0)
                    exposure = infection_intensity * decay
                    if exposure > max_exposure:
                        max_exposure = exposure

                    # Flood depth calculation for flood-hazard zones
                    if "flood" in zone.hazard_type:
                        flood_calc = (zone.risk_score * 35.0 * decay) * hazard_expansion_multiplier
                        if flood_calc > max_flood:
                            max_flood = flood_calc

            road.contagion_exposure_score = round(min(1.0, max_exposure), 3)
            road.flood_depth_cm = round(max_flood, 1)
