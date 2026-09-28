"""
TwinEvac - WebSocket Telemetry Endpoint
Handles client connections for zero-latency live simulation state streaming.
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.engine.rolling_optimizer import rolling_optimizer

router = APIRouter()


@router.websocket("/ws/telemetry")
async def websocket_telemetry_endpoint(websocket: WebSocket):
    await rolling_optimizer.register_client(websocket)
    try:
        while True:
            # Keep socket alive and receive client commands if any
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        rolling_optimizer.unregister_client(websocket)
    except Exception:
        rolling_optimizer.unregister_client(websocket)
