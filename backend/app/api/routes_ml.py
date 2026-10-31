"""
TwinEvac - AI/ML Management API Routes
Endpoints for querying model status, inspection metrics, and triggering dynamic retraining.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, Dict, Any

from app.ml.ml_service import ml_service

router = APIRouter(prefix="/ml", tags=["AI & Machine Learning"])


class RetrainRequest(BaseModel):
    epochs: Optional[int] = 25
    synthetic_samples: Optional[int] = 1800


@router.get("/status")
def get_ml_status() -> Dict[str, Any]:
    """Returns runtime model health, frameworks, parameters count, and inference latencies."""
    return ml_service.get_status()


@router.get("/metrics")
def get_ml_metrics() -> Dict[str, Any]:
    """Returns detailed evaluation metrics including R2 scores, RMSE, accuracy, and feature importances."""
    status = ml_service.get_status()
    return {
        "metadata": ml_service.metadata,
        "active_models": status["models_active"],
        "last_inference_latency_ms": status["last_inference_latency_ms"]
    }


@router.post("/retrain")
def trigger_retraining(req: Optional[RetrainRequest] = None) -> Dict[str, Any]:
    """Executes live online retraining of PyTorch LSTM, Random Forest, Isolation Forest, and Q-Routing models."""
    try:
        new_metadata = ml_service.retrain_models()
        return {
            "status": "SUCCESS",
            "message": "AI/ML models successfully retrained and hot-reloaded into memory.",
            "metadata": new_metadata
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Model retraining failed: {str(e)}")
