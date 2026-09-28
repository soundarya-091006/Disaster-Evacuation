"""
TwinEvac Core Configuration
Settings, thresholds, prediction horizons, and data paths.
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"

class Settings:
    PROJECT_NAME: str = "TwinEvac Digital Twin SaaS"
    VERSION: str = "2.4.0-enterprise"
    DESCRIPTION: str = "AI-Powered Disease & Disaster Evacuation Digital Twin with Continuous Rolling Optimization"
    
    # Data file paths
    SALEM_NETWORK_PATH: Path = DATA_DIR / "salem_network.json"
    SHELTERS_PATH: Path = DATA_DIR / "shelters_hospitals.json"
    POPULATION_ZONES_PATH: Path = DATA_DIR / "population_zones.json"
    
    # Simulation settings
    SIM_TICK_SECONDS: float = 1.0  # Real-world seconds per simulation loop step
    SIM_MINUTES_PER_TICK: float = 0.5  # Simulated minutes advanced per tick
    PREDICTION_HORIZONS: list[int] = [15, 30, 60]  # Forward forecasting horizons
    
    # BPR (Bureau of Public Roads) function parameters
    BPR_ALPHA: float = 0.15
    BPR_BETA: float = 4.0
    
    # Risk & Hazard weights for dynamic routing cost
    WEIGHT_TRAVEL_TIME: float = 1.0
    WEIGHT_CONGESTION: float = 2.5
    WEIGHT_CONTAGION_EXPOSURE: float = 3.5
    WEIGHT_FLOOD_DEPTH: float = 4.0
    WEIGHT_SHELTER_OVERFLOW_PENALTY: float = 5.0
    
    # Anomaly thresholds
    BOTTLENECK_CONGESTION_THRESHOLD: float = 0.75
    SHELTER_NEAR_CAPACITY_THRESHOLD: float = 0.85
    SHELTER_FULL_THRESHOLD: float = 0.98

settings = Settings()
