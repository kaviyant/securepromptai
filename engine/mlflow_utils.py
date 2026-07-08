import os
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("secureprompt_mlflow")

# Load environment variable defaults
MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://mlflow:5000")
MLFLOW_EXPERIMENT_NAME = os.getenv("MLFLOW_EXPERIMENT_NAME", "SecurePrompt_AI_Classifiers")

class MLflowManager:
    _initialized = False

    @classmethod
    def setup_mlflow(cls) -> bool:
        """
        Initializes MLflow tracking URI and configures the default experiment.
        Returns True if successful, False if MLflow is unavailable or raises an exception.
        """
        if cls._initialized:
            return True
            
        try:
            import mlflow
            mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
            mlflow.set_experiment(MLFLOW_EXPERIMENT_NAME)
            cls._initialized = True
            logger.info(f"MLflow client successfully linked to: {MLFLOW_TRACKING_URI}")
            return True
        except ImportError:
            logger.warning("MLflow library is not installed. Experiment tracking is disabled.")
            return False
        except Exception as e:
            logger.warning(f"Unable to connect to MLflow server at {MLFLOW_TRACKING_URI}: {e}. Operating in local-only mode.")
            return False

    @classmethod
    def start_run(cls, run_name: Optional[str] = None):
        """
        Starts an MLflow run. Wraps mlflow.start_run gracefully.
        """
        if not cls.setup_mlflow():
            # Return a dummy context manager to prevent syntax errors
            class DummyContext:
                def __enter__(self): return self
                def __exit__(self, exc_type, exc_val, exc_tb): pass
            return DummyContext()
            
        import mlflow
        return mlflow.start_run(run_name=run_name)

    @classmethod
    def log_params(cls, params: Dict[str, Any]):
        """
        Logs a dictionary of parameters to the current MLflow run.
        """
        if not cls.setup_mlflow():
            return
        try:
            import mlflow
            mlflow.log_params(params)
        except Exception as e:
            logger.error(f"Failed to log parameters to MLflow: {e}")

    @classmethod
    def log_metrics(cls, metrics: Dict[str, float], step: Optional[int] = None):
        """
        Logs a dictionary of metrics to the current MLflow run.
        """
        if not cls.setup_mlflow():
            return
        try:
            import mlflow
            mlflow.log_metrics(metrics, step=step)
        except Exception as e:
            logger.error(f"Failed to log metrics to MLflow: {e}")

    @classmethod
    def log_model(cls, model: Any, artifact_path: str, registered_model_name: Optional[str] = None) -> Optional[str]:
        """
        Logs a python model artifact (scikit-learn, pytorch, or Hugging Face pipeline) to MLflow.
        Returns the run model URI if successful.
        """
        if not cls.setup_mlflow():
            return None
        try:
            import mlflow
            # Check model type to log correctly
            if hasattr(model, "predict") and not hasattr(model, "config"): # Scikit-learn
                import mlflow.sklearn
                model_info = mlflow.sklearn.log_model(
                    sk_model=model,
                    artifact_path=artifact_path,
                    registered_model_name=registered_model_name
                )
            else: # HF pipeline or PyTorch model
                import mlflow.pytorch
                # DistilBERT models are HuggingFace Transformers models. We log them as generic python function or pytorch
                model_info = mlflow.pytorch.log_model(
                    pytorch_model=model,
                    artifact_path=artifact_path,
                    registered_model_name=registered_model_name
                )
            
            logger.info(f"Model logged to MLflow artifacts path: {artifact_path}")
            return model_info.model_uri
        except Exception as e:
            logger.error(f"Failed to log model to MLflow: {e}")
            return None

    @classmethod
    def register_model_version(cls, run_id: str, artifact_path: str, model_name: str) -> Optional[int]:
        """
        Registers an artifact model from a specific run to the Model Registry.
        Returns the registered model version number.
        """
        if not cls.setup_mlflow():
            return None
        try:
            import mlflow
            from mlflow.tracking import MlflowClient
            client = MlflowClient()
            
            model_uri = f"runs:/{run_id}/{artifact_path}"
            logger.info(f"Registering model version from {model_uri} into registry '{model_name}'...")
            mv = mlflow.register_model(model_uri, model_name)
            logger.info(f"Successfully registered model '{model_name}' Version {mv.version}")
            return int(mv.version)
        except Exception as e:
            logger.error(f"Failed to register model in MLflow Registry: {e}")
            return None

    @classmethod
    def transition_model_stage(cls, model_name: str, version: int, stage: str) -> bool:
        """
        Transitions a registered model's version to a specific stage: 'Production', 'Staging', or 'Archived'.
        """
        if not cls.setup_mlflow():
            return False
        try:
            from mlflow.tracking import MlflowClient
            client = MlflowClient()
            client.transition_model_version_stage(
                name=model_name,
                version=version,
                stage=stage,
                archive_existing_versions=True # Automatically demotes old production versions
            )
            logger.info(f"Transitioned model '{model_name}' Version {version} to stage '{stage}'")
            return True
        except Exception as e:
            logger.error(f"Failed to transition model stage in MLflow: {e}")
            return False

    @classmethod
    def get_production_model_uri(cls, model_name: str) -> Optional[str]:
        """
        Fetches the production stage URI of a registered model.
        """
        if not cls.setup_mlflow():
            return None
        try:
            from mlflow.tracking import MlflowClient
            client = MlflowClient()
            versions = client.get_latest_versions(model_name, stages=["Production"])
            if versions:
                prod_version = versions[0]
                uri = f"models:/{model_name}/Production"
                logger.info(f"Fetched Production model URI for {model_name}: {uri} (Version: {prod_version.version})")
                return uri
            else:
                logger.warning(f"No Production version found for model '{model_name}'")
                return None
        except Exception as e:
            logger.warning(f"Error fetching Production model URI from registry: {e}. Defaulting to local file pathway.")
            return None
