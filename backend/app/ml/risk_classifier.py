"""
TwinEvac - Production Multi-Hazard Dynamic Risk Classifier
Classifies roads and geographic zones into risk tiers (LOW, MEDIUM, HIGH, CRITICAL)
using trained Random Forest Classifier and composite hazard attribution.
"""

from typing import Dict, List, Tuple
from app.schemas.models import RoadSegment, EvacuationZone
from app.ml.ml_service import ml_service
from app.core.weather_service import weather_service


class RiskClassifier:
    def __init__(self):
        self.weights = {
            "flood": 0.40,
            "contagion": 0.35,
            "congestion": 0.25
        }

    def classify_road(self, road: RoadSegment) -> Tuple[str, float, List[str]]:
        """
        Calculates composite risk score (0.0 to 1.0) and assigns a categorical risk tier.
        Returns: (risk_level, composite_score, reasons)
        """
        if road.is_closed:
            return "CRITICAL", 1.0, ["Road physically closed / containment blocked"]

        reasons = []
        if road.flood_depth_cm > 30.0:
            reasons.append(f"Severe inundation ({road.flood_depth_cm:.0f}cm depth)")
        elif road.flood_depth_cm > 10.0:
            reasons.append(f"Waterlogging ({road.flood_depth_cm:.0f}cm depth)")

        if road.contagion_exposure_score > 0.7:
            reasons.append(f"High pathogen contagion vector ({road.contagion_exposure_score*100:.0f}%)")
        elif road.contagion_exposure_score > 0.35:
            reasons.append("Moderate epidemiological exposure")

        if road.congestion_index > 0.8:
            reasons.append(f"Severe gridlock bottleneck ({road.congestion_index*100:.0f}%)")
        elif road.congestion_index > 0.5:
            reasons.append("Elevated traffic density")

        # Extract features for trained Random Forest classifier
        features = [
            road.flood_depth_cm,
            road.contagion_exposure_score,
            road.congestion_index,
            road.current_speed_kmh,
            road.capacity_pcu_per_hour,
            weather_service.rainfall_intensity_mmh,
            1.0 if road.is_closed else 0.0
        ]

        tier, composite_score, _ = ml_service.classify_risk(features)

        if not reasons:
            if tier == "LOW":
                reasons.append("Normal arterial clearance")
            else:
                reasons.append(f"Elevated multi-hazard strain (Score: {composite_score:.2f})")

        return tier, composite_score, reasons

    def classify_zone(self, zone: EvacuationZone) -> Tuple[str, float]:
        """Classifies risk level for an evacuation origin zone."""
        infection_ratio = min(1.0, zone.active_infections / max(zone.total_population * 0.05, 10.0))
        clearance_factor = 1.0 - (zone.evacuated_population / max(zone.total_population, 1))
        
        zone_risk = (zone.risk_score * 0.5) + (infection_ratio * 0.3) + (clearance_factor * 0.2)
        zone_risk = min(1.0, max(0.0, zone_risk))

        if zone_risk >= 0.70:
            tier = "CRITICAL"
        elif zone_risk >= 0.45:
            tier = "HIGH"
        elif zone_risk >= 0.25:
            tier = "MEDIUM"
        else:
            tier = "LOW"

        return tier, round(zone_risk, 3)
