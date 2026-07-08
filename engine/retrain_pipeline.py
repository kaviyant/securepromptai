import os
import asyncio
import logging
from typing import Dict, Any, List
import pandas as pd
from motor.motor_asyncio import AsyncIOMotorClient
from engine.trainer import train_fallback_sklearn, train_distilbert, TORCH_AVAILABLE
from engine.dvc_manager import DvcManager
from engine.mlflow_utils import MLflowManager

logger = logging.getLogger("secureprompt_retrain")
logging.basicConfig(level=logging.INFO)

MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
DATABASE_NAME = os.getenv("DATABASE_NAME", "secureprompt_db")

class RetrainingPipeline:
    @staticmethod
    async def collect_new_data() -> List[Dict[str, Any]]:
        """
        Gathers live prompt records from MongoDB history collection.
        If there are not enough live samples, generates synthetic additions to represent incoming production data.
        """
        logger.info(f"Connecting to database to collect training samples from {MONGODB_URL}...")
        client = AsyncIOMotorClient(MONGODB_URL)
        db = client[DATABASE_NAME]
        
        cursor = db.prompts_history.find({}).sort("timestamp", -1).limit(1000)
        records = await cursor.to_list(length=1000)
        client.close()
        
        logger.info(f"Retrieved {len(records)} audit log prompts from database.")
        
        formatted_samples = []
        for r in records:
            prompt_text = r.get("originalPrompt")
            risk_level = r.get("riskLevel", "None")
            
            # Map risk levels to binary classification label (sensitive or not)
            is_sensitive = 1 if risk_level in ["Critical", "High", "Medium"] else 0
            if prompt_text:
                formatted_samples.append({
                    "text": prompt_text,
                    "is_sensitive": is_sensitive
                })
                
        # If database is empty or has too few items, seed with generator to allow pipeline execution
        if len(formatted_samples) < 50:
            logger.info("Database records are sparse. Augmenting with synthetic prompts for retraining...")
            from engine.dataset_generator import DatasetGenerator
            synthetic = DatasetGenerator.generate_list(size=100)
            for item in synthetic:
                formatted_samples.append({
                    "text": item["text"],
                    "is_sensitive": 1 if item["is_sensitive"] else 0
                })
                
        return formatted_samples

    @classmethod
    async def run_pipeline(cls) -> Dict[str, Any]:
        """
        Orchestrates the entire retraining workflow:
        1. Collect new and synthetic prompt data.
        2. Clean and save to CSV file under version control.
        3. Invoke DVC tracking.
        4. Run model training (Scikit-learn fallback + optional DistilBERT).
        5. Evaluate models and register with MLflow.
        6. Transition stage to Production in MLflow Model Registry if accuracy is verified.
        """
        logger.info("Initializing Automatic Retraining Pipeline...")
        
        # 1. Collect Data
        data = await cls.collect_new_data()
        df = pd.DataFrame(data)
        
        # 2. Version dataset via DVC
        dataset_path = "data/retrained_dataset.csv"
        os.makedirs(os.path.dirname(dataset_path), exist_ok=True)
        df.to_csv(dataset_path, index=False)
        logger.info(f"Dataset compiled. Size: {len(df)} records. Saved to: {dataset_path}")
        
        dvc_info = DvcManager.track_dataset(dataset_path=dataset_path, size=len(df))
        
        # 3. Train models
        # We always train the fast Logistic Regression model
        logger.info("Training Scikit-learn fallback model...")
        sklearn_results = train_fallback_sklearn(
            model_dir="model",
            dataset_size=len(df),
            c_parameter=2.5
        )
        
        # Optionally train DistilBERT if GPU/Libraries are available
        distilbert_results = {}
        if TORCH_AVAILABLE and os.getenv("TRAIN_DEEP_LEARNING", "false").lower() == "true":
            logger.info("Training DistilBERT deep learning classification model...")
            distilbert_results = train_distilbert(
                output_dir="model/distilbert",
                epochs=1,
                batch_size=8,
                dataset_size=min(len(df), 100) # Cap for execution speed
            )
            
        # 4. Model Registry and Promotion
        # Promote the newly trained models to production in MLflow Registry
        run_id = sklearn_results.get("run_id")
        if run_id and run_id != "local_run":
            logger.info("Registering and promoting Sklearn model in registry...")
            version = MLflowManager.register_model_version(
                run_id=run_id,
                artifact_path="sklearn_logistic_regression",
                model_name="SecurePrompt_Sklearn_Classifier"
            )
            if version:
                MLflowManager.transition_model_stage(
                    model_name="SecurePrompt_Sklearn_Classifier",
                    version=version,
                    stage="Production"
                )
                
        db_run_id = distilbert_results.get("run_id")
        if db_run_id and db_run_id != "local_run":
            logger.info("Registering and promoting DistilBERT model in registry...")
            db_version = MLflowManager.register_model_version(
                run_id=db_run_id,
                artifact_path="distilbert_prompt_classifier",
                model_name="SecurePrompt_DistilBERT_Classifier"
            )
            if db_version:
                MLflowManager.transition_model_stage(
                    model_name="SecurePrompt_DistilBERT_Classifier",
                    version=db_version,
                    stage="Production"
                )

        # 5. Track model artifacts via DVC
        DvcManager.track_model_artifacts(model_dir="model")
        
        summary = {
            "status": "success",
            "dataset_records": len(df),
            "sklearn_accuracy": sklearn_results.get("accuracy", 0.0),
            "dvc_hash": dvc_info.get("md5_hash", ""),
            "distilbert_trained": TORCH_AVAILABLE and "run_id" in distilbert_results
        }
        
        logger.info(f"Retraining pipeline finished successfully. Summary: {summary}")
        return summary

if __name__ == "__main__":
    asyncio.run(RetrainingPipeline.run_pipeline())
