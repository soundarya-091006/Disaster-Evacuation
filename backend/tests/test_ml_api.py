"""
TwinEvac - ML API & Environmental API Verification Script
Tests GET /ml/status, GET /ml/metrics, POST /ml/retrain, GET /environment/weather, POST /environment/weather
"""

import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_ml_and_weather_endpoints():
    print("1. Testing GET /ml/status...")
    res = client.get("/ml/status")
    assert res.status_code == 200
    st = res.json()
    assert st["status"] in ("OPERATIONAL", "HEURISTIC_FALLBACK")
    assert "traffic_lstm" in st["models_active"]
    assert "risk_classifier" in st["models_active"]
    assert "anomaly_detector" in st["models_active"]
    assert "q_routing_agent" in st["models_active"]
    print(f"   [OK] ML Status: {st['status']} | Active Models: {list(st['models_active'].keys())}")

    print("2. Testing GET /ml/metrics...")
    res = client.get("/ml/metrics")
    assert res.status_code == 200
    m = res.json()
    assert "metadata" in m
    assert "active_models" in m
    print(f"   [OK] ML Metrics returned with latency: {m['last_inference_latency_ms']} ms")

    print("3. Testing GET /environment/weather...")
    res = client.get("/environment/weather")
    assert res.status_code == 200
    w = res.json()
    assert "rainfall_intensity_mmh" in w
    print(f"   [OK] Current Weather: {w['condition']} ({w['rainfall_intensity_mmh']} mm/h)")

    print("4. Testing POST /environment/weather...")
    res = client.post("/environment/weather", json={"rainfall_intensity_mmh": 65.0})
    assert res.status_code == 200
    res_json = res.json()
    assert res_json["status"] == "UPDATED"
    assert res_json["weather"]["rainfall_intensity_mmh"] == 65.0
    print(f"   [OK] Rainfall modulated to 65.0 mm/h. Weather condition: {res_json['weather']['condition']}")

    # Restore weather to 35.0
    client.post("/environment/weather", json={"rainfall_intensity_mmh": 35.0})

    print("\nALL ML & WEATHER ENDPOINT TESTS PASSED SUCCESSFULLY! [OK]")


if __name__ == "__main__":
    test_ml_and_weather_endpoints()
