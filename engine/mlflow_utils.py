import os
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("secureprompt_mlflow")

# Load environment variable defaults
MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://mlflow:5000")
MLFLOW_EXPERIMENT_NAME = os.getenv("MLFLOW_EXPERIMENT_NAME", "SecurePromptAI")

class MLflowManager:
    _initialized = False
    _available = False

    @classmethod
    def setup_mlflow(cls) -> bool:
        """
        Initializes MLflow tracking URI and configures the default experiment named 'SecurePromptAI'.
        Automatically creates the experiment if it does not exist.
        Returns True if successful, False if MLflow is unavailable or raises an exception.
        """
        if cls._initialized:
            return cls._available
            
        cls._initialized = True

        if os.getenv("DISABLE_MLFLOW", "false").lower() == "true":
            cls._available = False
            logger.info("MLflow tracking is disabled via DISABLE_MLFLOW environment variable.")
            return False
            
        try:
            import mlflow
            
            # Fast check if MLflow server is reachable before attempting REST calls
            if MLFLOW_TRACKING_URI.startswith("http"):
                import urllib.parse
                import socket
                parsed = urllib.parse.urlparse(MLFLOW_TRACKING_URI)
                host = parsed.hostname
                port = parsed.port or (443 if parsed.scheme == "https" else 80)
                if host:
                    try:
                        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                            sock.settimeout(0.5)
                            sock.connect((host, port))
                    except Exception:
                        logger.warning(f"MLflow server at {MLFLOW_TRACKING_URI} is unreachable. Operating in local-only mode.")
                        cls._available = False
                        return False

            mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
            
            # Configure or automatically create experiment named 'SecurePromptAI'
            experiment_name = "SecurePromptAI"
            exp = mlflow.get_experiment_by_name(experiment_name)
            if exp is None:
                try:
                    mlflow.create_experiment(experiment_name)
                    logger.info(f"Created new MLflow experiment '{experiment_name}'.")
                except Exception as e:
                    logger.warning(f"Could not create experiment '{experiment_name}': {e}")
            mlflow.set_experiment(experiment_name)
            
            cls._available = True
            logger.info(f"MLflow client successfully linked to experiment '{experiment_name}' at: {MLFLOW_TRACKING_URI}")
            return True
        except ImportError:
            logger.warning("MLflow library is not installed. Experiment tracking is disabled.")
            cls._available = False
            return False
        except Exception as e:
            logger.warning(f"Unable to connect to MLflow server at {MLFLOW_TRACKING_URI}: {e}. Operating in local-only mode.")
            cls._available = False
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
    def log_model(
        cls, 
        model: Any, 
        artifact_path: str, 
        registered_model_name: Optional[str] = None,
        signature: Optional[Any] = None,
        input_example: Optional[Any] = None
    ) -> Optional[Any]:
        """
        Logs a python model artifact (scikit-learn, pytorch, or Hugging Face pipeline) to MLflow.
        Supports model signatures and input examples. Returns model info metadata if successful.
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
                    registered_model_name=registered_model_name,
                    signature=signature,
                    input_example=input_example
                )
            else: # HF pipeline or PyTorch model
                import mlflow.pytorch
                model_info = mlflow.pytorch.log_model(
                    pytorch_model=model,
                    artifact_path=artifact_path,
                    registered_model_name=registered_model_name,
                    signature=signature,
                    input_example=input_example
                )
            
            logger.info(f"Model logged to MLflow artifacts path: {artifact_path}")
            return model_info
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
            model_uri = f"runs:/{run_id}/{artifact_path}"
            logger.info(f"Registering model version from {model_uri} into registry '{model_name}'...")
            mv = mlflow.register_model(model_uri, model_name)
            logger.info(f"Successfully registered model '{model_name}' Version {mv.version}")
            return int(mv.version)
        except Exception as e:
            logger.error(f"Failed to register model in MLflow Registry: {e}")
            return None

    @classmethod
    def set_run_tags(cls, run_id: str, tags: Dict[str, str]):
        """
        Applies a dict of metadata tags to a specific MLflow run.
        """
        if not cls.setup_mlflow():
            return
        try:
            from mlflow.tracking import MlflowClient
            client = MlflowClient()
            for k, v in tags.items():
                client.set_tag(run_id, k, v)
        except Exception as e:
            logger.error(f"Failed to set tags on run '{run_id}': {e}")

    @classmethod
    def set_model_version_tags(cls, model_name: str, version: int, tags: Dict[str, str]):
        """
        Applies a dict of metadata tags to a specific registered model version.
        """
        if not cls.setup_mlflow():
            return
        try:
            from mlflow.tracking import MlflowClient
            client = MlflowClient()
            for k, v in tags.items():
                client.set_model_version_tag(model_name, str(version), k, v)
        except Exception as e:
            logger.error(f"Failed to set tags on model '{model_name}' version {version}: {e}")

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

    @classmethod
    def load_model_by_version(cls, model_name: str, version: int) -> Optional[Any]:
        """
        Loads a specific version of a registered Scikit-learn model from the registry.
        """
        if not cls.setup_mlflow():
            return None
        try:
            import mlflow.sklearn
            model_uri = f"models:/{model_name}/{version}"
            model = mlflow.sklearn.load_model(model_uri)
            logger.info(f"Loaded model '{model_name}' version {version} from MLflow registry.")
            return model
        except Exception as e:
            logger.error(f"Failed to load model '{model_name}' version {version} from registry: {e}")
            return None

    @classmethod
    def load_latest_production_model(cls, model_name: str) -> Optional[Any]:
        """
        Loads the latest Production-stage registered Scikit-learn model from the registry.
        """
        if not cls.setup_mlflow():
            return None
        try:
            import mlflow.sklearn
            model_uri = f"models:/{model_name}/Production"
            model = mlflow.sklearn.load_model(model_uri)
            logger.info(f"Loaded latest Production model '{model_name}' from MLflow registry.")
            return model
        except Exception as e:
            logger.error(f"Failed to load latest Production model '{model_name}' from registry: {e}")
            return None

    @classmethod
    def highlight_best_run(cls, metric_name: str = "accuracy") -> Optional[Dict[str, Any]]:
        """
        Identifies the best-performing run in 'SecurePromptAI' based on the highest metric accuracy.
        Applies a run tag 'is_best=true' to the best run while clearing it from others, and returns metadata.
        """
        if not cls.setup_mlflow():
            return None
        try:
            from mlflow.tracking import MlflowClient
            client = MlflowClient()
            experiment_name = "SecurePromptAI"
            exp = client.get_experiment_by_name(experiment_name)
            if not exp:
                return None
            
            runs = client.search_runs(
                experiment_ids=[exp.experiment_id],
                order_by=[f"metrics.{metric_name} DESC"]
            )
            if not runs:
                return None
                
            best_run = runs[0]
            best_run_id = best_run.info.run_id
            
            # Clean up old "is_best" tags
            for run in runs:
                try:
                    if run.data.tags.get("is_best") == "true":
                        client.delete_run_tag(run.info.run_id, "is_best")
                except Exception:
                    pass
            
            # Tag current best run
            try:
                client.set_tag(best_run_id, "is_best", "true")
                logger.info(f"Set 'is_best=true' tag on run ID '{best_run_id}' (accuracy: {best_run.data.metrics.get('accuracy')})")
            except Exception:
                pass
                
            return {
                "run_id": best_run_id,
                "accuracy": best_run.data.metrics.get("accuracy", 0.0),
                "precision": best_run.data.metrics.get("precision", 0.0),
                "recall": best_run.data.metrics.get("recall", 0.0),
                "f1_score": best_run.data.metrics.get("f1_score", 0.0),
                "params": best_run.data.params
            }
        except Exception as e:
            logger.error(f"Failed to highlight best run: {e}")
            return None
