"""
TwinEvac - Multi-Hazard Dynamic Risk Classifier
Classifies roads and geographic zones into risk tiers (LOW, MEDIUM, HIGH, CRITICAL)
by synthesizing flood inundation, disease exposure risk, and capacity strain.
"""

from typing import Dict, List, Tuple
from app.schemas.models import RoadSegment, EvacuationZone


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

        # 1. Flood hazard component
        flood_norm = min(1.0, road.flood_depth_cm / 50.0)
        if road.flood_depth_cm > 30.0:
            reasons.append(f"Severe inundation ({road.flood_depth_cm:.0f}cm depth)")
        elif road.flood_depth_cm > 10.0:
            reasons.append(f"Waterlogging ({road.flood_depth_cm:.0f}cm depth)")

        # 2. Disease / Contagion corridor hazard
        contagion_norm = road.contagion_exposure_score
        if road.contagion_exposure_score > 0.7:
            reasons.append(f"High pathogen contagion vector ({road.contagion_exposure_score*100:.0f}%)")
        elif road.contagion_exposure_score > 0.35:
            reasons.append("Moderate epidemiological exposure")

        # 3. Congestion & Bottleneck strain
        cong_norm = road.congestion_index
        if road.congestion_index > 0.8:
            reasons.append(f"Severe gridlock bottleneck ({road.congestion_index*100:.0f}%)")
        elif road.congestion_index > 0.5:
            reasons.append("Elevated traffic density")

        composite_score = (
            flood_norm * self.weights["flood"] +
            contagion_norm * self.weights["contagion"] +
            cong_norm * self.weights["congestion"]
        )

        if composite_score >= 0.75 or road.flood_depth_cm > 40.0:
            tier = "CRITICAL"
        elif composite_score >= 0.50 or road.flood_depth_cm > 20.0:
            tier = "HIGH"
        elif composite_score >= 0.25:
            tier = "MEDIUM"
        else:
            tier = "LOW"

        return tier, round(composite_score, 3), reasons

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
