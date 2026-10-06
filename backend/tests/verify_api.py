"""
TwinEvac - End-to-End API Verification Script
Tests all REST endpoints: state, nodes, shelters, predictions, What-If evaluation, and PDF export.
"""

import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def run_api_tests():
    print("1. Testing Health Check Endpoint (GET /)...")
    res = client.get("/")
    assert res.status_code == 200
    print(f"   [OK] Health check: {res.json()['service']} v{res.json()['version']}")

    print("2. Testing Digital Twin State (GET /twin/state)...")
    res = client.get("/twin/state")
    assert res.status_code == 200
    state = res.json()
    assert len(state["roads"]) > 15
    assert len(state["shelters"]) >= 4
    assert len(state["zones"]) >= 5
    assert "15m" in state["predictions"]
    print(f"   [OK] State returned: {len(state['roads'])} roads, {len(state['shelters'])} shelters, {len(state['agents'])} agents.")

    print("3. Testing Predictive Horizons (GET /analytics/predictions)...")
    res = client.get("/analytics/predictions")
    assert res.status_code == 200
    preds = res.json()
    assert "15m" in preds and "30m" in preds and "60m" in preds
    print(f"   [OK] Forecasts loaded: 15m conf={preds['15m']['confidence_pct']}%, 30m conf={preds['30m']['confidence_pct']}%, 60m conf={preds['60m']['confidence_pct']}%.")

    print("4. Testing Predefined Scenarios (GET /analytics/predefined-scenarios)...")
    res = client.get("/analytics/predefined-scenarios")
    assert res.status_code == 200
    scenarios = res.json()
    assert len(scenarios) == 4
    print(f"   [OK] {len(scenarios)} pre-built emergency scenarios available.")

    print("5. Testing What-If Scenario Evaluation (POST /analytics/what-if/evaluate)...")
    first_scenario = scenarios[0]
    res = client.post("/analytics/what-if/evaluate", json=first_scenario)
    assert res.status_code == 200
    eval_result = res.json()
    assert "baseline_eet_minutes" in eval_result
    assert "what_if_eet_minutes" in eval_result
    print(f"   [OK] What-If Evaluated: Baseline={eval_result['baseline_eet_minutes']}m, What-If={eval_result['what_if_eet_minutes']}m, Delta={eval_result['time_delta_pct']}%.")

    print("6. Testing Simulation Controls (POST /sim/step, /sim/speed)...")
    res = client.post("/sim/step")
    assert res.status_code == 200
    res = client.post("/sim/speed", json={"multiplier": 2.0})
    assert res.status_code == 200
    print("   [OK] Simulation stepped and speed adjusted to 2.0x.")

    print("7. Testing JSON Report Export (GET /reports/export-json)...")
    res = client.get("/reports/export-json")
    assert res.status_code == 200
    json_report = res.json()
    assert "report_metadata" in json_report
    print("   [OK] JSON Audit report generated successfully.")

    print("8. Testing Executive PDF Report Export (GET /reports/export-pdf)...")
    res = client.get("/reports/export-pdf")
    assert res.status_code == 200
    assert res.headers["content-type"] == "application/pdf"
    assert len(res.content) > 1000
    print(f"   [OK] PDF Audit Report generated ({len(res.content)} bytes).")

    print("\nALL END-TO-END API TESTS PASSED PERFECTLY! [OK]")


if __name__ == "__main__":
    run_api_tests()
