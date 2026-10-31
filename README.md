# TwinEvac — AI-Powered Disease & Disaster Evacuation Digital Twin SaaS

**TwinEvac** is a multi-hazard and epidemic evacuation **Digital Twin SaaS platform** developed for Emergency Operations Centers, Municipal Corporations, and Disaster Management Authorities. 

Unlike traditional reactive alert systems (which simply notify populations without actionable routing guidance), TwinEvac constructs a continuously updated virtual replica of an urban or district environment (benchmarked on the **Salem District & Municipal Corporation** urban corridor). It dynamically models road congestion, disease contagion vectors, flood inundation, and shelter/hospital capacity to:
- Predict congestion and evacuation bottlenecks **ahead of time** across **15-minute, 30-minute, and 60-minute forward horizons**.
- Perform **dynamic multi-objective capacity-constrained routing** that minimizes Total Evacuation Time (TET) while preventing shelter overload and pathogen exposure.
- Enable interactive **What-If Counterfactual Simulations** ("What if Shevapet is cordoned off?", "What if GMKMC Hospital reaches 100% capacity?", "What if floodwaters expand by 40%?").
- Execute a **continuous rolling re-optimization loop** that streams live telemetry and autonomous dispatch orders via WebSockets.

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            TWINEVAC PLATFORM                                │
├──────────────────────────┬──────────────────────────────────────────────────┤
│ Frontend (React 19 + TS) │ • 2.5D Canvas Digital Twin Map (Salem Corridor)  │
│                          │ • 15m / 30m / 60m Predictive Horizon Scrubber    │
│                          │ • Interactive What-If Counterfactual Sandbox     │
│                          │ • Enterprise AI Model Hub (Latencies & Retrain)  │
│                          │ • Environmental & Weather Simulator Modal        │
│                          │ • Dynamic Evacuation Analytics Time-Series Modal │
│                          │ • Live Hospital / Quarantine Bed Gauges          │
│                          │ • Automated AI Tactical Dispatch Advisories      │
│                          │ • One-Click Executive PDF & JSON Audit Reports   │
├──────────────────────────┼──────────────────────────────────────────────────┤
│ Backend (FastAPI Python) │ • Multi-Agent Mobility Simulation (Agents/PCU)   │
│                          │ • Spatial Epidemic & Dynamic Flood Runoff Model  │
│                          │ • Weather Service (Rainfall mm/h & Road Runoff)  │
│                          │ • BPR Travel Time & A* Impedance Routing Engine  │
│                          │ • PyTorch 2-Layer LSTM Traffic Forecaster        │
│                          │ • Tabular Random Forest Forecaster (R²=0.9468)   │
│                          │ • Multi-Hazard Random Forest Classifier (Acc=92%)│
│                          │ • Unsupervised Isolation Forest Anomaly Detector │
│                          │ • Graph Reinforcement Learning Q-Routing Policy  │
│                          │ • Rolling Re-optimization Loop & WebSocket Bus   │
└──────────────────────────┴──────────────────────────────────────────────────┘
```

---

## Key Differentiators vs. Existing Systems

| Feature | Reactive Alerts (SMS/Apps) | Traditional Simulators (SUMO/MassMotion) | **TwinEvac Digital Twin SaaS** |
| :--- | :--- | :--- | :--- |
| **Prediction Horizon** | None (Post-event) | Retrospective / Batch | **Proactive (15m, 30m, 60m ahead)** |
| **Hazard Scope** | Single hazard | Fire-only or Vehicle-only | **Multi-hazard (Epidemics + Floods + Infrastructure)** |
| **Route Guidance** | None ("Evacuate now") | Static shortest path | **Capacity-constrained dynamic load balancing** |
| **Hospital / Triage** | Ignored | Ignored | **Live quarantine bed & intake tracking** |
| **What-If Sandbox** | Not available | Requires offline script re-run | **Interactive real-time counterfactual delta** |
| **Re-optimization** | Static one-shot | Static run | **Continuous rolling feedback loop (1-2s tick)** |
| **Software Stack** | Custom broadcast | Licensed / Commercial engines | **100% Open Data & Open Standards** |

---

## Directory Structure

```
Disaster-Evacuation-twinevac-digital-twin/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── routes_digital_twin.py   # State, nodes, roads, shelters, zones
│   │   │   ├── routes_simulation.py     # Start, pause, step, reset, speed
│   │   │   ├── routes_analytics.py      # 15/30/60m predictions, What-If evaluate/apply
│   │   │   ├── routes_reports.py        # Executive PDF and JSON incident reports
│   │   │   ├── routes_ml.py             # Model status, metrics, runtime hot-retraining
│   │   │   ├── routes_weather.py        # Environmental & rainfall modulation
│   │   │   └── websocket.py             # Live telemetry WebSocket (/ws/telemetry)
│   │   ├── core/
│   │   │   ├── config.py                # System settings and BPR parameters
│   │   │   ├── graph_manager.py         # NetworkX road graph & geospatial logic
│   │   │   └── weather_service.py       # Weather state & road runoff calculation
│   │   ├── engine/
│   │   │   ├── simulation.py            # Multi-agent mobility & BPR flow engine
│   │   │   ├── epidemic_model.py        # Spatial contagion exposure model
│   │   │   ├── what_if_engine.py        # Counterfactual simulation sandbox & delta
│   │   │   └── rolling_optimizer.py     # Background loop & client broadcaster
│   │   ├── ml/
│   │   │   ├── models/                  # Trained PyTorch .pt & Scikit-Learn .joblib files
│   │   │   ├── train_models.py          # Complete offline training & evaluation pipeline
│   │   │   ├── ml_service.py            # Central high-performance batched inference engine
│   │   │   ├── traffic_predictor.py     # 15m/30m/60m time-series forecasting
│   │   │   ├── risk_classifier.py       # Multi-hazard risk tiering (LOW/MED/HIGH/CRIT)
│   │   │   ├── router.py                # RL Q-learning + A* dynamic routing
│   │   │   └── anomaly_detector.py      # Isolation forest gridlock & surge detector
│   │   ├── schemas/
│   │   │   └── models.py                # Pydantic models for Twin state & API
│   │   └── main.py                      # FastAPI app entry point
│   ├── data/
│   │   ├── salem_network.json           # Salem road network (17 nodes, 42 edges)
│   │   ├── shelters_hospitals.json      # Emergency shelters & quarantine hospitals
│   │   └── population_zones.json        # Population zones & active contagion counts
│   ├── tests/
│   │   ├── test_engine.py               # Backend unit test suite (9 tests)
│   │   ├── verify_api.py                # REST API test suite (8 endpoints)
│   │   ├── test_ws_buttons.py           # WebSocket push verification
│   │   └── test_ml_api.py               # AI/ML & weather endpoints verification
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── MapView.tsx              # Interactive 2.5D Digital Twin Canvas
│   │   │   ├── TelemetryHeader.tsx      # Operations Command Bar with AI & Weather chips
│   │   │   ├── AIModelHubModal.tsx      # Model cards, latencies, feature weights, retrain
│   │   │   ├── WeatherControlModal.tsx  # Dynamic rainfall slider & disaster presets
│   │   │   ├── AnalyticsTrendsModal.tsx # SVG time-series charts for congestion & shelters
│   │   │   ├── PredictionHorizon.tsx    # 15m / 30m / 60m timeline scrubber
│   │   │   ├── WhatIfPanel.tsx          # What-If scenario builder & presets
│   │   │   ├── ScenarioCompareModal.tsx # Side-by-side Baseline vs What-If analysis
│   │   │   ├── ShelterGauges.tsx        # Hospital & shelter occupancy cards
│   │   │   ├── AdvisoryFeed.tsx         # Autonomous AI dispatch orders
│   │   │   └── ExportReportModal.tsx    # PDF / JSON audit export modal
│   │   ├── hooks/
│   │   │   └── useDigitalTwinSocket.ts  # Real-time WebSocket hook with fallback
│   │   ├── types/
│   │   │   └── digital_twin.ts          # TypeScript type definitions
│   │   ├── App.tsx                      # SaaS Command Center main layout
│   │   └── main.tsx
│   ├── index.html
│   ├── vite.config.ts
│   └── package.json
└── README.md
```

---

## Quickstart Guide

### 1. Backend Setup & Run
```bash
# Navigate to backend
cd backend

# Install dependencies (Python 3.11+)
pip install -r requirements.txt

# Run backend test suite
python tests/test_engine.py        # engine + regression tests
python tests/verify_api.py        # every REST endpoint
python tests/test_ws_buttons.py   # live websocket pushes (Start/Pause/Speed/Apply/Clear)

# Launch FastAPI server (starts on http://localhost:8000)
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
Interactive OpenAPI/Swagger documentation is available at:
`http://localhost:8000/docs`

### 2. Frontend Setup & Run
```bash
# In a new terminal, navigate to frontend
cd frontend

# Install dependencies (Node.js 18+)
npm install

# Start Vite development server (starts on http://localhost:5173)
npm run dev
```

Open `http://localhost:5173` in your browser to access the live Digital Twin Command Center.

---

## Operational Scenarios Tested
1. **Baseline Operations**: Initial crowd flows from Shevapet and Gugai toward GMKMC Hospital and Steel Plant Base.
2. **Shevapet Red-Zone Contagion Lockdown**: Physical cordon closes central access corridors; dynamic router diverts traffic via outer rings, avoiding cross-infection.
3. **GMKMC Hospital 100% Saturation**: When hospital triage reaches maximum capacity, router redirects ambulances to Steel Plant and Gorimedu facilities.
4. **Salem 4-Roads Flash Inundation**: Simulates severe waterlogging at central 4-Roads arterial, testing automatic peripheral detour efficiency.
5. **Express Transit Bus Deployment**: Deploys emergency bus convoys on the National Highway bypass, cutting total evacuation completion time by ~22%.

---

## Export & Audit Reports
- **Executive PDF Audit**: Formatted incident documentation with summary tables, shelter fill metrics, horizon forecasts, and AI tactical dispatches for district authorities.
- **Raw JSON Snapshot**: Machine-readable payload for integration with national disaster databases (NDMA, IMD, State EOCs).

---

## Testing

```bash
# Backend (from backend/)
python tests/test_engine.py
python tests/verify_api.py
python tests/test_ws_buttons.py
python tests/test_ml_api.py

# Complete End-to-End browser test (34/34 checks passing)
# Start the backend (port 8000) and `npm run build && npx vite preview --port 5173 --host 127.0.0.1`, then:
python tests/e2e/test_buttons_e2e.py
```

The frontend reads the backend address from `VITE_API_URL` (default `http://localhost:8000`).

See `PROJECT_STATUS.md` for what is complete, what was fixed, and what remains.
