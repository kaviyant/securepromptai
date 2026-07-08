import os
import subprocess
import logging
from typing import Dict, Any, Optional
from engine.dataset_generator import DatasetGenerator

logger = logging.getLogger("secureprompt_dvc")

class DvcManager:
    @staticmethod
    def initialize_dvc() -> bool:
        """
        Runs 'dvc init' in the project directory if the .dvc folder does not exist.
        Configures a local storage remote in the sandbox to track files without cloud dependencies.
        """
        if os.path.exists(".dvc"):
            logger.info("DVC is already initialized in this repository.")
            return True
            
        try:
            # Initialize DVC
            logger.info("Initializing DVC repository...")
            subprocess.run(["dvc", "init", "--no-scm"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            # Setup a local remote storage path
            remote_path = os.path.abspath(".dvc/local_remote")
            os.makedirs(remote_path, exist_ok=True)
            
            logger.info(f"Setting up DVC local storage remote at: {remote_path}")
            subprocess.run(["dvc", "remote", "add", "-d", "local_storage", remote_path], check=True)
            logger.info("DVC initialized and local remote set up successfully.")
            return True
        except Exception as e:
            logger.warning(f"DVC CLI not available or failed to initialize: {e}. Writing mock DVC tracking file descriptors.")
            # Self-generate mock configuration files to simulate DVC existence
            os.makedirs(".dvc", exist_ok=True)
            with open(".dvc/config", "w") as f:
                f.write("[core]\n    analytics = false\n['remote \"local_storage\"']\n    url = .dvc/local_remote\n")
            return False

    @staticmethod
    def track_dataset(dataset_path: str = "data/dataset.csv", size: int = 500) -> Dict[str, Any]:
        """
        Generates and saves a training dataset, then tracks it using DVC.
        Returns the DVC file contents or tracking metadata.
        """
        os.makedirs(os.path.dirname(dataset_path), exist_ok=True)
        
        # 1. Export dataset
        logger.info(f"Generating dataset of size {size} to version-control: {dataset_path}")
        df = DatasetGenerator.generate_dataframe(size=size)
        df.to_csv(dataset_path, index=False)
        
        # 2. Initialize DVC if needed
        DvcManager.initialize_dvc()
        
        dvc_meta = {
            "dataset_path": dataset_path,
            "dvc_file": f"{dataset_path}.dvc",
            "status": "untracked",
            "md5_hash": ""
        }

        # 3. Track dataset file via DVC CLI
        try:
            logger.info(f"Running DVC add for {dataset_path}...")
            result = subprocess.run(["dvc", "add", dataset_path], check=True, capture_output=True, text=True)
            logger.info(result.stdout)
            
            dvc_meta["status"] = "tracked"
            
            # Extract hash from .dvc file
            dvc_file_path = f"{dataset_path}.dvc"
            if os.path.exists(dvc_file_path):
                with open(dvc_file_path, "r") as f:
                    content = f.read()
                    dvc_meta["dvc_file_content"] = content
                    # Simple MD5 parsing from DVC yaml structure
                    for line in content.splitlines():
                        if "md5:" in line:
                            dvc_meta["md5_hash"] = line.split("md5:")[-1].strip()
                            
            # Run DVC push to local remote
            subprocess.run(["dvc", "push"], check=False)
            
        except Exception as e:
            logger.warning(f"DVC CLI add command failed: {e}. Simulating DVC yaml descriptors.")
            # Generate mock .dvc descriptor file
            import hashlib
            with open(dataset_path, "rb") as f:
                file_hash = hashlib.md5(f.read()).hexdigest()
            
            mock_dvc_content = f"outs:\n- md5: {file_hash}\n  path: {os.path.basename(dataset_path)}\n"
            dvc_file_path = f"{dataset_path}.dvc"
            with open(dvc_file_path, "w") as f:
                f.write(mock_dvc_content)
                
            dvc_meta["status"] = "mock_tracked"
            dvc_meta["md5_hash"] = file_hash
            dvc_meta["dvc_file_content"] = mock_dvc_content

        return dvc_meta

    @staticmethod
    def track_model_artifacts(model_dir: str = "model") -> Dict[str, Any]:
        """
        Tracks serialized model pickle binaries or HuggingFace weights folders with DVC.
        """
        DvcManager.initialize_dvc()
        artifacts_status = {}
        
        # Identify targets
        targets = []
        # Sklearn binary targets
        for fn in ["vectorizer.pkl", "classifier.pkl"]:
            path = os.path.join(model_dir, fn)
            if os.path.exists(path):
                targets.append(path)
                
        # DistilBERT target folder
        distilbert_path = os.path.join(model_dir, "distilbert")
        if os.path.exists(distilbert_path):
            targets.append(distilbert_path)

        for target in targets:
            try:
                subprocess.run(["dvc", "add", target], check=True, capture_output=True)
                artifacts_status[target] = "tracked"
            except Exception:
                # Simulating tracking
                artifacts_status[target] = "mock_tracked"
                # Write a mock .dvc file
                with open(f"{target}.dvc", "w") as f:
                    f.write(f"outs:\n- path: {os.path.basename(target)}\n  desc: Mock version control metadata\n")
                    
        return artifacts_status

if __name__ == "__main__":
    # Test tracking data and models
    logger.setLevel(logging.INFO)
    console_handler = logging.StreamHandler()
    logger.addHandler(console_handler)
    
    meta = DvcManager.track_dataset(dataset_path="data/test_dataset.csv", size=50)
    print("Dataset versioning metadata:", meta)
    
    models_meta = DvcManager.track_model_artifacts(model_dir="model")
    print("Models versioning metadata:", models_meta)
