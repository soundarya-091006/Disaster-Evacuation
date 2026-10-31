"""
TwinEvac - Production Anomaly Detection Engine
Monitors edge-level and shelter-level telemetry to flag sudden volume spikes,
unexpected gridlocks, or intake stalls using batched Isolation Forest inference.
"""

from typing import List, Dict, Any
import numpy as np
from app.schemas.models import RoadSegment, ShelterHospital, AnomalyReport
from app.ml.ml_service import ml_service


class AnomalyDetector:
    def __init__(self):
        self.edge_history: Dict[str, List[float]] = {}
        self.speed_history: Dict[str, List[float]] = {}

    def inspect_network(
        self,
        roads: List[RoadSegment],
        shelters: List[ShelterHospital],
        sim_minute: float
    ) -> List[AnomalyReport]:
        """
        Scans all roads and facilities for operational anomalies using batched vector inference.
        Returns a list of detected AnomalyReports.
        """
        anomalies: List[AnomalyReport] = []
        active_roads = [r for r in roads if not r.is_closed]
        if not active_roads:
            return anomalies

        features_list = []
        road_meta = []
        for road in active_roads:
            v_hist = self.edge_history.setdefault(road.id, [])
            v_hist.append(road.current_volume)
            if len(v_hist) > 10:
                v_hist.pop(0)

            s_hist = self.speed_history.setdefault(road.id, [])
            s_hist.append(road.current_speed_kmh)
            if len(s_hist) > 10:
                s_hist.pop(0)

            avg_vol = (sum(v_hist[:-1]) / (len(v_hist) - 1)) if len(v_hist) > 1 else max(100.0, road.current_volume)
            avg_spd = (sum(s_hist[:-1]) / (len(s_hist) - 1)) if len(s_hist) > 1 else road.current_speed_kmh

            vol_change = road.current_volume / max(avg_vol, 1.0)
            spd_drop = max(0.0, (avg_spd - road.current_speed_kmh) / max(avg_spd, 1.0))

            features_list.append([road.current_volume, road.current_speed_kmh, road.congestion_index, vol_change, spd_drop])
            road_meta.append((road, vol_change, avg_vol))

        batch_results = ml_service.detect_anomaly_batch(np.array(features_list, dtype=np.float32))

        for (road, vol_change, avg_vol), (is_anom, severity) in zip(road_meta, batch_results):
            if (road.congestion_index > 0.85 and road.current_speed_kmh < 10.0) or (is_anom and road.congestion_index > 0.78):
                anomalies.append(AnomalyReport(
                    id=f"ANOM_JAM_{road.id}_{int(sim_minute)}",
                    timestamp_sim_min=round(sim_minute, 1),
                    anomaly_type="UNEXPECTED_GRIDLOCK",
                    location=f"{road.name} ({road.id})",
                    severity_score=round(max(severity, road.congestion_index), 2),
                    description=f"Critical gridlock detected! Travel speed dropped to {road.current_speed_kmh:.1f} km/h (Capacity: {road.capacity_pcu_per_hour:.0f} PCU/hr)."
                ))
            elif vol_change > 2.4 and avg_vol > 80:
                anomalies.append(AnomalyReport(
                    id=f"ANOM_SURGE_{road.id}_{int(sim_minute)}",
                    timestamp_sim_min=round(sim_minute, 1),
                    anomaly_type="SURGE_SPIKE",
                    location=f"{road.name}",
                    severity_score=round(max(0.82, severity), 2),
                    description=f"Sudden {vol_change*100:.0f}% traffic surge detected ({road.current_volume:.0f} vs avg {avg_vol:.0f} PCU/hr). Early bottleneck warning."
                ))

        # Facility / Shelter-level capacity alerts
        for shelter in shelters:
            occ_pct = shelter.occupancy_pct
            if occ_pct >= 95.0 and shelter.status != "FULL":
                anomalies.append(AnomalyReport(
                    id=f"ANOM_SHELTER_CRIT_{shelter.id}_{int(sim_minute)}",
                    timestamp_sim_min=round(sim_minute, 1),
                    anomaly_type="INTAKE_STALL",
                    location=shelter.name,
                    severity_score=0.95,
                    description=f"Facility at {occ_pct:.0f}% capacity ({shelter.occupied}/{shelter.total_capacity}). Incoming flows must be diverted."
                ))

        return anomalies
