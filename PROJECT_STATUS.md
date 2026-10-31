# TwinEvac — Project Status

## Completed
- FastAPI backend: state / nodes / roads / shelters / zones, simulation control (start, pause, step, reset, speed), analytics (15/30/60 min forecasts, 4 preset What-If scenarios, evaluate / apply / clear), PDF + JSON audit export, live WebSocket telemetry.
- Simulation engine: Salem network (17 nodes, 42 directed edges), BPR congestion, A* routing with shelter-capacity penalties, agent-based convoys (ambulance / bus / pedestrian / vehicle), hazard (flood + contagion) exposure, anomaly + advisory feed.
- What-If engine: forks the live twin (optimized `__deepcopy__` preserving ML weights), compares baseline vs scenario at the same horizon (evacuation time, route cost, bottlenecks, exposure, shelter load).
- AI/ML Production Layer (Fully Trained & Deployed):
  1. PyTorch LSTM Multi-Horizon Traffic Forecaster (`traffic_lstm.pt`): 2-layer LSTM predicting V/C ratios at 15m, 30m, and 60m horizons.
  2. Tabular Traffic Random Forest Ensemble (`traffic_rf.joblib`, R² = 0.9468): Ultra-fast batch inference.
  3. Multi-Hazard Random Forest Classifier (`risk_rf.joblib`, Accuracy = 91.92%, F1 = 0.9187): Categorizes safety into LOW, MEDIUM, HIGH, CRITICAL.
  4. Isolation Forest Anomaly Detector (`anomaly_isoforest.joblib`, Contamination = 0.06): Detects spatial surges and gridlocks.
  5. Multi-Horizon Shelter Occupancy Regressor (`shelter_predictor.joblib`, R² = 0.9870).
  6. Graph Reinforcement Learning Q-Routing Agent (`q_routing_agent.json`): 64 state-action pairs balancing route loads dynamically.
  7. Centralized `MLService` singleton with vectorized batching (<3ms inference latency) and runtime hot-retraining API (`POST /ml/retrain`).
- Weather & Environmental Engine:
  - Dynamic rainfall intensity (mm/h), wind speed, flood runoff propagation on road edges.
  - Interactive weather simulator modal and REST endpoints (`GET/POST /environment/weather`).
- Time-Series Trends & Historical Tracking:
  - Interactive SVG time-series modal displaying live congestion and hospital/shelter load trends.
- React SaaS Command Center:
  - Telemetry header, forecast scrubber, canvas map (pan/zoom/layers/click-to-select road), What-If sandbox, comparison modal, shelter gauges, advisory feed, export modal.
  - Added AI Model Hub modal with live latency meters, architecture cards, feature importance visualizer, and one-click re-training button.
  - Added Environmental Simulator modal with rainfall sliders and disaster presets (Clear, Monsoon, Flash Flood Surge, Cyclone).
  - Added Evacuation Analytics modal with SVG charts for multi-horizon evacuation dynamics.
- Dead Patch Artifacts Cleaned:
  - Removed `backend/app/core/graph_manager_backup.py`, `graph_manager_before_astar.py`, `replace_astar.py`.
- Automated Testing & Verification:
  - Backend Unit & Regression: 9/9 passed (`test_engine.py`).
  - REST API Verification: 8/8 passed (`verify_api.py`).
  - WebSocket Push Verification: 100% passed (`test_ws_buttons.py`).
  - ML & Weather API Verification: 100% passed (`test_ml_api.py`).
  - Playwright End-to-End Browser Test Suite: 34/34 checks passed (100% button and modal coverage with zero uncaught errors).

## Future Roadmap (Production Scale-out)
1. Persistence: Optional PostgreSQL/PostGIS (+ TimescaleDB) backend connector for multi-district history.
2. Direct OpenStreetMap (OSM) / Overpass API automated ingester for arbitrary cities beyond Salem.
3. Docker Compose and Kubernetes deployment manifests with GPU acceleration for large-scale multi-million agent simulations.
