"""
TwinEvac - WebSocket / live-button test.
Verifies that Start, Pause, Speed, Apply and Clear are pushed to connected dashboards,
which is what makes the frontend buttons update without a page refresh.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient
from app.main import app


def recv(ws):
    return json.loads(ws.receive_text())


def run():
    # The context manager keeps one event loop alive, so the background simulation loop
    # survives between requests exactly as it does under uvicorn.
    with TestClient(app) as client:
        client.post("/sim/reset")
        with client.websocket_connect("/ws/telemetry") as ws:
            first = recv(ws)
            assert first["is_running"] is False
            print("[OK] initial snapshot received on connect")

            client.post("/sim/start")
            msg = recv(ws)
            assert msg["is_running"] is True
            print("[OK] Start is pushed to the dashboard")

            t0 = msg["elapsed_sim_minutes"]
            for _ in range(3):
                msg = recv(ws)
            assert msg["elapsed_sim_minutes"] > t0
            print("[OK] live ticks stream while running")

            client.post("/sim/pause")
            paused = None
            for _ in range(6):  # drain any tick already in flight
                m = recv(ws)
                if m["is_running"] is False:
                    paused = m
                    break
            assert paused is not None, "Pause was never pushed (UI would stay on 'Pause')"
            print("[OK] Pause is pushed to the dashboard")

            client.post("/sim/speed", json={"multiplier": 5})
            m = recv(ws)
            assert m["speed_multiplier"] == 5.0
            print("[OK] Speed change is pushed")

            sc = client.get("/analytics/predefined-scenarios").json()[0]
            client.post("/analytics/what-if/apply", json=sc)
            m = recv(ws)
            assert m["active_scenario"]["scenario_id"] == sc["scenario_id"]
            print("[OK] Apply scenario is pushed")

            client.post("/analytics/what-if/clear")
            m = recv(ws)
            assert m["active_scenario"] is None
            print("[OK] Clear scenario is pushed")

        client.post("/sim/reset")
    print("\nALL WEBSOCKET BUTTON TESTS PASSED [OK]")


if __name__ == "__main__":
    run()
