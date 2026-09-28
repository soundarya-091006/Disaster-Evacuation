"""
TwinEvac - FastAPI Application Main Entry Point
AI-Powered Disease & Disaster Evacuation Digital Twin SaaS
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api import (
    websocket,
    routes_digital_twin,
    routes_simulation,
    routes_analytics,
    routes_reports
)
from app.engine.rolling_optimizer import rolling_optimizer

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("twin_evac")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing TwinEvac Digital Twin Engine...")
    # Optionally start rolling loop automatically or await operator start
    yield
    logger.info("Shutting down TwinEvac Digital Twin...")
    rolling_optimizer.pause()


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=settings.DESCRIPTION,
    lifespan=lifespan
)

# Enable CORS for local Vite frontend and SaaS dashboards
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API Routers
app.include_router(websocket.router)
app.include_router(routes_digital_twin.router)
app.include_router(routes_simulation.router)
app.include_router(routes_analytics.router)
app.include_router(routes_reports.router)


@app.get("/")
def health_check():
    return {
        "status": "online",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "active_sim_minute": rolling_optimizer.sim.elapsed_sim_minutes,
        "is_sim_running": rolling_optimizer.sim.is_running
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
