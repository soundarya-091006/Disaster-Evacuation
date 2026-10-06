"""
TwinEvac - Traffic & Congestion Predictor (15m / 30m / 60m Horizons)
Predicts road congestion ratios and travel speeds ahead of time using
time-series autoregression, upstream flow integration, and hazard scaling.
"""

import math
from typing import Dict, List, Tuple
import numpy as np

from app.schemas.models import RoadSegment, PredictionHorizonData


class TrafficPredictor:
    def __init__(self):
        # Weight vectors for forward forecasting (15m, 30m, 60m)
        # Horizon factors simulate peak evacuation surge accumulation
        self.horizon_factors = {
            15: {"decay": 0.85, "surge_mult": 1.25, "uncertainty": 0.06},
            30: {"decay": 0.70, "surge_mult": 1.45, "uncertainty": 0.11},
            60: {"decay": 0.55, "surge_mult": 1.65, "uncertainty": 0.18},
        }

    def predict_edge_congestion(
        self,
        edge: RoadSegment,
        horizon_min: int,
        upstream_avg_congestion: float = 0.0,
        hazard_expansion_rate: float = 1.0
    ) -> Tuple[float, float, Tuple[float, float]]:
        """
        Generates predictive congestion index and speed for an edge at a future horizon.
        Returns: (pred_congestion, pred_speed_kmh, (conf_low, conf_high))
        """
        params = self.horizon_factors.get(horizon_min, self.horizon_factors[30])
        
        current_c = edge.congestion_index
        flood_factor = min(1.0, (edge.flood_depth_cm / 30.0) * hazard_expansion_rate)
        contagion_factor = edge.contagion_exposure_score * 0.4
        
        # Upstream flow spillover
        inflow = upstream_avg_congestion * 0.35
        
        # Time-series trend: ongoing evacuation accumulates flow unless already congested
        surge = params["surge_mult"] * (1.0 - current_c * 0.3)
        raw_pred = (current_c * params["decay"]) + (inflow * 0.3) + (flood_factor * 0.4) + (contagion_factor * 0.2)
        raw_pred = raw_pred * surge

        # Edge closure logic
        if edge.is_closed:
            pred_congestion = 1.0
            pred_speed = 0.0
            confidence_interval = (1.0, 1.0)
            return pred_congestion, pred_speed, confidence_interval

        pred_congestion = max(0.05, min(0.98, raw_pred))
        
        # Speed estimate
        pred_speed = edge.free_flow_speed_kmh * max(0.1, (1.0 - pred_congestion * 0.85))
        
        # Uncertainty band
        sigma = params["uncertainty"] * (1.0 + current_c * 0.5)
        conf_low = max(0.0, pred_congestion - 1.645 * sigma)
        conf_high = min(1.0, pred_congestion + 1.645 * sigma)

        return round(pred_congestion, 3), round(pred_speed, 1), (round(conf_low, 3), round(conf_high, 3))

    def generate_horizon_predictions(
        self,
        roads: List[RoadSegment],
        shelters_occupancy: Dict[str, float],
        elapsed_sim_minutes: float
    ) -> Dict[str, PredictionHorizonData]:
        """
        Produces prediction datasets for 15, 30, and 60-minute time horizons.
        """
        predictions_map: Dict[str, PredictionHorizonData] = {}

        # Compute average network congestion
        active_roads = [r for r in roads if not r.is_closed]
        avg_network_cong = np.mean([r.congestion_index for r in active_roads]) if active_roads else 0.0

        for horizon in [15, 30, 60]:
            high_risk_edges = []
            predicted_speeds = []
            predicted_congestions = []
            predicted_bottlenecks = []

            for r in roads:
                p_cong, p_speed, (c_low, c_high) = self.predict_edge_congestion(
                    r, horizon, upstream_avg_congestion=avg_network_cong
                )
                predicted_speeds.append(p_speed)
                predicted_congestions.append(p_cong)

                if p_cong >= 0.75 or r.is_closed:
                    high_risk_edges.append(r.id)
                    predicted_bottlenecks.append({
                        "edge_id": r.id,
                        "road_name": r.name,
                        "source": r.source,
                        "target": r.target,
                        "predicted_congestion_index": p_cong,
                        "confidence_range": [c_low, c_high],
                        "estimated_delay_min": round((r.distance_km / max(p_speed, 1.0)) * 60, 1)
                    })

            # Predict future shelter occupancy
            pred_shelter_load: Dict[str, float] = {}
            for s_id, curr_occ in shelters_occupancy.items():
                intake_surge = (horizon / 15.0) * 8.5  # % arrival projection
                projected = min(100.0, curr_occ + intake_surge)
                pred_shelter_load[s_id] = round(projected, 1)

            # Horizon confidence (confidence degrades with time horizon)
            confidence = 94.0 if horizon == 15 else (87.5 if horizon == 30 else 78.0)

            predictions_map[f"{horizon}m"] = PredictionHorizonData(
                horizon_minutes=horizon,
                predicted_congested_road_count=len(high_risk_edges),
                predicted_average_speed_kmh=round(float(np.mean(predicted_speeds)), 1) if predicted_speeds else 35.0,
                predicted_network_congestion_pct=round(float(np.mean(predicted_congestions)) * 100, 1) if predicted_congestions else 0.0,
                high_risk_road_ids=high_risk_edges,
                shelter_predicted_occupancy=pred_shelter_load,
                predicted_bottlenecks=predicted_bottlenecks,
                confidence_pct=confidence
            )

        return predictions_map
