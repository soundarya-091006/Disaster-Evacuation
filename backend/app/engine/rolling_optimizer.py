"""
TwinEvac - Rolling Re-Optimization Loop & Background Runner
Runs periodic simulation ticks, executes capacity re-routing,
and broadcasts live telemetry to all connected WebSocket clients.
"""

import asyncio
import json
import logging
from typing import Set, Optional
from fastapi import WebSocket

from app.core.config import settings
from app.engine.simulation import EvacuationSimulation
from app.engine.what_if_engine import WhatIfEngine
from app.schemas.models import SimulationStepState, WhatIfScenario

logger = logging.getLogger("twin_evac.rolling_loop")


class RollingOptimizer:
    def __init__(self):
        self.sim = EvacuationSimulation()
        self.what_if_engine = WhatIfEngine(self.sim)
        self.connected_websockets: Set[WebSocket] = set()
        self.is_running: bool = False
        self.runner_task: Optional[asyncio.Task] = None

    async def register_client(self, websocket: WebSocket):
        await websocket.accept()
        self.connected_websockets.add(websocket)
        # Send initial snapshot immediately
        state = self.sim.get_current_state()
        await websocket.send_text(state.model_dump_json())

    def unregister_client(self, websocket: WebSocket):
        self.connected_websockets.discard(websocket)

    async def broadcast_state(self, state: SimulationStepState):
        if not self.connected_websockets:
            return
        payload = state.model_dump_json()
        dead_sockets = set()
        for ws in self.connected_websockets:
            try:
                await ws.send_text(payload)
            except Exception:
                dead_sockets.add(ws)
        for dead in dead_sockets:
            self.connected_websockets.discard(dead)

    async def run_loop(self):
        """Asynchronous execution loop for the digital twin."""
        logger.info("Starting TwinEvac Rolling Re-optimization loop...")
        while True:
            try:
                if self.is_running:
                    state = self.sim.step()
                    await self.broadcast_state(state)
                await asyncio.sleep(settings.SIM_TICK_SECONDS)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in rolling loop tick: {e}", exc_info=True)
                await asyncio.sleep(1.0)

    def start(self):
        self.is_running = True
        self.sim.is_running = True
        if self.runner_task is None or self.runner_task.done():
            self.runner_task = asyncio.create_task(self.run_loop())

    def pause(self):
        self.is_running = False
        self.sim.is_running = False

    def _safe_broadcast(self, state: SimulationStepState):
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self.broadcast_state(state))
        except RuntimeError:
            pass

    def step_once(self) -> SimulationStepState:
        state = self.sim.step()
        self._safe_broadcast(state)
        return state

    def reset(self) -> SimulationStepState:
        self.is_running = False
        self.sim.reset()
        state = self.sim.get_current_state()
        self._safe_broadcast(state)
        return state

    def set_speed(self, multiplier: float):
        self.sim.speed_multiplier = max(0.2, min(10.0, multiplier))

    def apply_scenario(self, scenario: WhatIfScenario) -> SimulationStepState:
        self.sim.apply_scenario(scenario)
        state = self.sim.get_current_state()
        self._safe_broadcast(state)
        return state


# Singleton optimizer instance
rolling_optimizer = RollingOptimizer()
