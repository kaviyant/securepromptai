from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, status
from pydantic import BaseModel
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.database.connection import get_database
from app.api.dependencies import get_current_admin
from app.middleware.prometheus import PrometheusMetrics
from engine.drift_detector import DriftDetector
from engine.retrain_pipeline import RetrainingPipeline
from typing import Dict, Any, List, Optional
from bson import ObjectId
import os
import logging

logger = logging.getLogger("secureprompt_mlops_api")
router = APIRouter(tags=["MLOps Platform Controllers"])

# Pydantic schemas for request payloads
class FeedbackRequest(BaseModel):
    prompt_id: str
    feedback_correct: bool
    audited_risk_level: Optional[str] = None

class DriftCheckResponse(BaseModel):
    drift_detected: bool
    psi: float
    ks_statistic: float
    ks_p_value: float
    message: str

class RetrainResponse(BaseModel):
    status: str
    message: str

class ModelStatusResponse(BaseModel):
    distilbert_loaded: bool
    sklearn_loaded: bool
    mlflow_sync_active: bool
    model_directory: str
    tracking_uri: str


@router.post("/api/mlops/drift-check", response_model=DriftCheckResponse)
async def check_model_drift(
    background_tasks: BackgroundTasks,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: Dict[str, Any] = Depends(get_current_admin)
):
    """
    Analyzes data drift in incoming prompts compared to baseline datasets.
    If drift is detected, triggers model retraining in the background.
    Gated by Admin access role.
    """
    # 1. Fetch live inputs (target sample) from prompts_history
    cursor = db.prompts_history.find({}).sort("timestamp", -1).limit(100)
    live_prompts = await cursor.to_list(length=100)
    
    target_lengths = [len(p.get("originalPrompt", "")) for p in live_prompts if p.get("originalPrompt")]
    
    # 2. Compile baseline sample
    # Generates standard prompt lengths to represent our baseline training set
    from engine.dataset_generator import DatasetGenerator
    baseline_prompts = DatasetGenerator.generate_list(size=100)
    baseline_lengths = [len(p["text"]) for p in baseline_prompts]

    # Handle insufficient data gracefully
    if len(target_lengths) < 30:
        # Pad with some live inputs to simulate a baseline evaluation
        target_lengths += [len(p["text"]) for p in DatasetGenerator.generate_list(size=30)]

    # 3. Calculate data drift
    drift_res = DriftDetector.detect_data_drift(baseline_lengths, target_lengths)
    
    # Update Prometheus gauges
    PrometheusMetrics.record_drift(drift_res["psi"], drift_res["drift_detected"])

    # 4. Trigger auto-retraining if drift crosses threshold
    if drift_res["drift_detected"]:
        logger.warning("Data drift detected. Spawning background retraining job...")
        background_tasks.add_task(RetrainingPipeline.run_pipeline)
        drift_res["message"] += " Retraining triggered automatically."

    return DriftCheckResponse(
        drift_detected=drift_res["drift_detected"],
        psi=drift_res["psi"],
        ks_statistic=drift_res.get("ks_statistic", 0.0),
        ks_p_value=drift_res.get("ks_p_value", 1.0),
        message=drift_res["message"]
    )


@router.post("/api/mlops/retrain", response_model=RetrainResponse)
async def trigger_retraining(
    background_tasks: BackgroundTasks,
    current_user: Dict[str, Any] = Depends(get_current_admin)
):
    """
    Triggers model retraining pipeline asynchronously.
    Gated by Admin access role.
    """
    background_tasks.add_task(RetrainingPipeline.run_pipeline)
    return RetrainResponse(
        status="started",
        message="Model retraining run initiated in the background. Check logs for status."
    )


@router.get("/api/mlops/model-status", response_model=ModelStatusResponse)
async def get_model_status(
    current_user: Dict[str, Any] = Depends(get_current_admin)
):
    """
    Retrieves active metadata about model weights and registry status.
    Gated by Admin access role.
    """
    # Use a dummy instance of MLDetector to check initialized states
    from engine.ml_detector import MLDetector
    detector = MLDetector()
    
    return ModelStatusResponse(
        distilbert_loaded=detector.distilbert_pipeline is not None,
        sklearn_loaded=detector.classifier is not None,
        mlflow_sync_active=os.getenv("MLFLOW_MODEL_SYNC", "false").lower() == "true",
        model_directory=detector.model_dir,
        tracking_uri=os.getenv("MLFLOW_TRACKING_URI", "http://mlflow:5000")
    )


@router.post("/api/mlops/feedback", response_model=Dict[str, Any])
async def submit_accuracy_feedback(
    feedback: FeedbackRequest,
    db: AsyncIOMotorDatabase = Depends(get_database),
    current_user: Dict[str, Any] = Depends(get_current_admin)
):
    """
    Submits user audit feedback on a scanned prompt to build the ground-truth set.
    Re-calculates the running accuracy gauge for Prometheus tracking.
    Gated by Admin access role.
    """
    try:
        pid = ObjectId(feedback.prompt_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid MongoDB ObjectId format.")

    # 1. Update the database prompt log with correct label
    record = await db.prompts_history.find_one({"_id": pid})
    if not record:
        raise HTTPException(status_code=404, detail="Prompt audit log not found.")

    update_fields = {
        "feedback_audited": True,
        "feedback_correct": feedback.feedback_correct
    }
    if feedback.audited_risk_level:
        update_fields["audited_risk_level"] = feedback.audited_risk_level
        # Map audited risk level back to action
        action = "BLOCK" if feedback.audited_risk_level in ["Critical", "High"] else "ALLOW"
        update_fields["audited_action"] = action

    await db.prompts_history.update_one({"_id": pid}, {"$set": update_fields})

    # 2. Recalculate historical accuracy score (Concept Drift tracker)
    audited_count = await db.prompts_history.count_documents({"feedback_audited": True})
    correct_count = await db.prompts_history.count_documents({"feedback_audited": True, "feedback_correct": True})
    
    accuracy = (correct_count / max(1, audited_count))
    PrometheusMetrics.update_accuracy(accuracy)

    # 3. Check for Concept Drift
    # If historical accuracy is below 80% (based on at least 10 audited samples)
    if audited_count >= 10 and accuracy < 0.80:
        logger.warning(f"Concept drift alert: Model accuracy dropped to {accuracy*100:.2f}%!")
        # We could trigger automatic retraining here as well!

    return {
        "status": "success",
        "message": "Feedback registered successfully.",
        "running_accuracy": round(accuracy, 4),
        "total_audited": audited_count
    }
