"""
TwinEvac - Anomaly Detection Engine
Monitors edge-level and shelter-level telemetry to flag sudden volume spikes,
unexpected gridlocks, or intake stalls requiring operator intervention.
"""

import time
from typing import List, Dict, Any
from app.schemas.models import RoadSegment, ShelterHospital, AnomalyReport


class AnomalyDetector:
    def __init__(self):
        self.edge_history: Dict[str, List[float]] = {}

    def inspect_network(
        self,
        roads: List[RoadSegment],
        shelters: List[ShelterHospital],
        sim_minute: float
    ) -> List[AnomalyReport]:
        """
        Scans all roads and facilities for operational anomalies.
        Returns a list of detected AnomalyReports.
        """
        anomalies: List[AnomalyReport] = []

        # 1. Edge-level volume and congestion anomalies
        for road in roads:
            if road.is_closed:
                continue

            # Check for sudden severe bottleneck (congestion > 0.85 with low speed < 8 km/h)
            if road.congestion_index > 0.85 and road.current_speed_kmh < 10.0:
                anomalies.append(AnomalyReport(
                    id=f"ANOM_JAM_{road.id}_{int(sim_minute)}",
                    timestamp_sim_min=round(sim_minute, 1),
                    anomaly_type="UNEXPECTED_GRIDLOCK",
                    location=f"{road.name} ({road.id})",
                    severity_score=round(road.congestion_index, 2),
                    description=f"Critical gridlock detected! Travel speed dropped to {road.current_speed_kmh} km/h (Capacity: {road.capacity_pcu_per_hour:.0f} PCU/hr)."
                ))

            # Check for rapid surge (current volume vs previous observations)
            history = self.edge_history.setdefault(road.id, [])
            history.append(road.current_volume)
            if len(history) > 10:
                history.pop(0)

            if len(history) >= 4:
                avg_prior = sum(history[:-1]) / (len(history) - 1)
                latest = history[-1]
                if avg_prior > 100 and (latest / max(avg_prior, 1)) > 2.4:
                    anomalies.append(AnomalyReport(
                        id=f"ANOM_SURGE_{road.id}_{int(sim_minute)}",
                        timestamp_sim_min=round(sim_minute, 1),
                        anomaly_type="SURGE_SPIKE",
                        location=f"{road.name}",
                        severity_score=0.82,
                        description=f"Sudden 240%+ traffic surge detected ({latest:.0f} vs avg {avg_prior:.0f} PCU/hr). Early bottleneck warning."
                    ))

        # 2. Facility / Shelter-level capacity alerts
        for shelter in shelters:
            occ_pct = shelter.occupancy_pct
            if occ_pct >= 95.0 and shelter.status != "FULL":
                anomalies.append(AnomalyReport(
                    id=f"ANOM_SHELTER_CRIT_{shelter.id}_{int(sim_minute)}",
                    timestamp_sim_min=round(sim_minute, 1),
                    anomaly_type="INTAKE_STALL",
                    location=shelter.name,
                    severity_score=0.95,
                    description=f"Facility at {occ_pct}% capacity ({shelter.occupied}/{shelter.total_capacity}). Incoming flows must be diverted."
                ))

        return anomalies
