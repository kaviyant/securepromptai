import os
import pickle
import logging
from typing import Dict, Any, List
from engine.dataset_generator import DatasetGenerator
from engine.mlflow_utils import MLflowManager

logger = logging.getLogger("secureprompt")

class MLDetector:
    def __init__(self, model_dir: str = "model"):
        self.model_dir = model_dir
        self.vectorizer_path = os.path.join(model_dir, "vectorizer.pkl")
        self.classifier_path = os.path.join(model_dir, "classifier.pkl")
        
        self.vectorizer = None
        self.classifier = None
        self.distilbert_pipeline = None

        self._init_models()

    def _init_models(self):
        """
        Initializes classifiers. If MLFLOW_MODEL_SYNC is enabled, tries to load
        from the MLflow Model Registry first. Otherwise, loads from local disk,
        falling back to auto-training if missing.
        """
        os.makedirs(self.model_dir, exist_ok=True)
        
        sync_enabled = os.getenv("MLFLOW_MODEL_SYNC", "false").lower() == "true"
        model_loaded = False

        # 1. Attempt to sync from MLflow Registry if enabled
        if sync_enabled:
            logger.info("MLflow Model Sync enabled. Checking registry for Production models...")
            model_loaded = self.sync_and_load_from_mlflow()

        # 2. Local DistilBERT fallback (if MLflow loading failed or is disabled)
        if not model_loaded:
            db_model_path = os.path.join(self.model_dir, "distilbert")
            if os.path.exists(db_model_path):
                try:
                    from transformers import pipeline
                    self.distilbert_pipeline = pipeline(
                        "text-classification",
                        model=db_model_path,
                        tokenizer=db_model_path,
                        device=-1 # CPU default
                    )
                    logger.info("Loaded local pre-trained DistilBERT pipeline.")
                    model_loaded = True
                except Exception as e:
                    logger.warning(f"Could not load local DistilBERT model: {e}")

        # 3. Scikit-learn Fallback (runs in parallel or as fallback)
        self.load_local_sklearn()

    def sync_and_load_from_mlflow(self) -> bool:
        """
        Queries MLflow Model Registry for Production stage classifiers and loads them.
        Returns True if DistilBERT was loaded successfully.
        """
        try:
            # Check for DistilBERT Registry model
            prod_uri = MLflowManager.get_production_model_uri("SecurePrompt_DistilBERT_Classifier")
            if prod_uri:
                import mlflow
                from mlflow.artifacts import download_artifacts
                from transformers import pipeline
                
                logger.info(f"Downloading Production DistilBERT from registry: {prod_uri}")
                local_dir = download_artifacts(artifact_uri=prod_uri)
                
                self.distilbert_pipeline = pipeline(
                    "text-classification",
                    model=local_dir,
                    tokenizer=local_dir,
                    device=-1
                )
                logger.info("Successfully loaded registered Production DistilBERT model.")
                return True
                
            # Check if there is an Sklearn production model to sync
            sklearn_uri = MLflowManager.get_production_model_uri("SecurePrompt_Sklearn_Classifier")
            if sklearn_uri:
                import mlflow
                from mlflow.artifacts import download_artifacts
                logger.info(f"Downloading Production Sklearn from registry: {sklearn_uri}")
                local_dir = download_artifacts(artifact_uri=sklearn_uri)
                
                # MLflow saves sklearn models with a 'model.pkl' inside
                clf_file = os.path.join(local_dir, "model.pkl")
                if os.path.exists(clf_file):
                    with open(clf_file, "rb") as f:
                        self.classifier = pickle.load(f)
                    logger.info("Successfully loaded registered Production Sklearn classifier.")
        except Exception as e:
            logger.warning(f"Failed to sync models from MLflow: {e}. Reverting to disk cache.")
        return False

    def load_local_sklearn(self):
        """
        Loads Scikit-learn TF-IDF & Logistic Regression models from the local disk.
        If missing, runs the automated fallback training.
        """
        if os.path.exists(self.vectorizer_path) and os.path.exists(self.classifier_path):
            try:
                with open(self.vectorizer_path, "rb") as f:
                    self.vectorizer = pickle.load(f)
                with open(self.classifier_path, "rb") as f:
                    self.classifier = pickle.load(f)
                logger.info("Loaded local Scikit-learn ML classifier and vectorizer.")
            except Exception as e:
                logger.error(f"Failed to load Scikit-learn model: {e}. Re-training model.")
                self.train_and_save_fallback()
        else:
            logger.info("Scikit-learn model not found. Automatically training fallback classifier...")
            self.train_and_save_fallback()

    def train_and_save_fallback(self):
        """
        Imports and runs the fallback training from engine.trainer.
        """
        try:
            from engine.trainer import train_fallback_sklearn
            train_fallback_sklearn(model_dir=self.model_dir, dataset_size=500)
            
            # Reload values
            if os.path.exists(self.vectorizer_path) and os.path.exists(self.classifier_path):
                with open(self.vectorizer_path, "rb") as f:
                    self.vectorizer = pickle.load(f)
                with open(self.classifier_path, "rb") as f:
                    self.classifier = pickle.load(f)
        except Exception as e:
            logger.error(f"Failed to run automated training: {e}")

    def predict(self, text: str) -> Dict[str, Any]:
        """
        Evaluates prompt text sensitivity and outputs risk probability.
        Uses DistilBERT if loaded, otherwise falls back to fast Scikit-learn.
        """
        # 1. DistilBERT Prediction
        if self.distilbert_pipeline:
            try:
                pred = self.distilbert_pipeline(text)[0]
                label = pred["label"]
                score = pred["score"]
                is_sensitive = label == "LABEL_1" or label == "SENSITIVE"
                confidence = int(score * 100)
                
                return {
                    "is_sensitive": is_sensitive,
                    "confidence": confidence,
                    "model": "DistilBERT"
                }
            except Exception as e:
                logger.warning(f"DistilBERT inference error: {e}. Falling back to Scikit-learn.")

        # 2. Scikit-learn Fallback Prediction
        if self.vectorizer and self.classifier:
            try:
                vec = self.vectorizer.transform([text])
                prob = self.classifier.predict_proba(vec)[0][1] # Probability of Class 1 (sensitive)
                is_sensitive = prob >= 0.5
                confidence = int(prob * 100) if is_sensitive else int((1 - prob) * 100)
                
                return {
                    "is_sensitive": is_sensitive,
                    "confidence": confidence,
                    "model": "Scikit-learn"
                }
            except Exception as e:
                logger.error(f"Scikit-learn inference error: {e}")

        # Default fallback if everything fails
        return {
            "is_sensitive": False,
            "confidence": 0,
            "model": "None"
        }
