import os
import logging
import pickle
import time
import hashlib
import json
from typing import Dict, Any, List, Optional
from engine.dataset_generator import DatasetGenerator
from engine.mlflow_utils import MLflowManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("secureprompt_trainer")

try:
    import torch
    from transformers import (
        DistilBertTokenizerFast, 
        DistilBertForSequenceClassification, 
        Trainer, 
        TrainingArguments,
        TrainerCallback
    )
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

if TORCH_AVAILABLE:
    class PromptDataset(torch.utils.data.Dataset):
        def __init__(self, encodings, labels):
            self.encodings = encodings
            self.labels = labels

        def __getitem__(self, idx):
            item = {key: torch.tensor(val[idx]) for key, val in self.encodings.items()}
            item['labels'] = torch.tensor(self.labels[idx])
            return item

        def __len__(self):
            return len(self.labels)

    class MLflowLoggingCallback(TrainerCallback):
        """
        Custom HuggingFace Trainer callback to log training/eval metrics to MLflow at each epoch.
        """
        def on_log(self, args, state, control, logs=None, **kwargs):
            if logs:
                # Log to active MLflow run
                metrics = {k: v for k, v in logs.items() if isinstance(v, (int, float))}
                MLflowManager.log_metrics(metrics, step=state.global_step)
else:
    class PromptDataset:
        pass
    class MLflowLoggingCallback:
        pass


def get_git_commit() -> str:
    """
    Retrieves the current Git commit hash if available.
    """
    try:
        import subprocess
        res = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True)
        return res.stdout.strip()
    except Exception:
        return "unknown"


def train_fallback_sklearn(
    model_dir: str = "model",
    dataset_size: int = 500,
    c_parameter: float = 2.0
) -> Dict[str, Any]:
    """
    Fits a high-speed Scikit-learn Logistic Regression classifier on synthetic prompts,
    logs hyperparameters/metrics to MLflow, and registers the model in the registry.
    """
    logger.info("Starting Scikit-learn classification model training...")
    os.makedirs(model_dir, exist_ok=True)
    
    vectorizer_path = os.path.join(model_dir, "vectorizer.pkl")
    classifier_path = os.path.join(model_dir, "classifier.pkl")
    
    # Measure training time (Start)
    start_time = time.time()

    # 1. Generate dataset
    df = DatasetGenerator.generate_dataframe(size=dataset_size)
    X = df["text"]
    y = df["is_sensitive"]

    # Compute a unique hash of the training dataset to act as the dataset version
    try:
        data_str = json.dumps(df, sort_keys=True)
        dataset_version = hashlib.md5(data_str.encode("utf-8")).hexdigest()
    except Exception:
        dataset_version = "unknown"

    # 2. Train-test split (80% train, 20% test)
    from sklearn.model_selection import train_test_split
    X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.2, random_state=42)

    # 3. Setup MLflow Run under experiment 'SecurePromptAI'
    run_id = "local_run"
    model_version = 1
    val_acc = 0.0
    val_prec = 0.0
    val_rec = 0.0
    val_f1 = 0.0
    val_roc_auc = 0.0

    try:
        import mlflow
        from mlflow.models import infer_signature
        import pandas as pd
    except ImportError:
        mlflow = None

    # We start the run context using MLflowManager helper
    with MLflowManager.start_run(run_name="Sklearn_Logistic_Regression") as run:
        if run and hasattr(run, "info"):
            run_id = run.info.run_id
        
        # 4. Vectorize text features
        from sklearn.feature_extraction.text import TfidfVectorizer
        vectorizer = TfidfVectorizer(max_features=1000, ngram_range=(1, 2))
        X_train_vec = vectorizer.fit_transform(X_train)
        X_val_vec = vectorizer.transform(X_val)

        # 5. Fit Classifier
        from sklearn.linear_model import LogisticRegression
        classifier = LogisticRegression(C=c_parameter)
        classifier.fit(X_train_vec, y_train)

        # Measure training execution time (End)
        training_time = time.time() - start_time

        # 6. Evaluate model performance metrics
        from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score, confusion_matrix, classification_report
        preds = classifier.predict(X_val_vec)
        val_acc = accuracy_score(y_val, preds)
        val_prec = precision_score(y_val, preds, zero_division=0)
        val_rec = recall_score(y_val, preds, zero_division=0)
        val_f1 = f1_score(y_val, preds, zero_division=0)
        
        try:
            probs = classifier.predict_proba(X_val_vec)[:, 1]
            val_roc_auc = roc_auc_score(y_val, probs)
        except Exception:
            val_roc_auc = roc_auc_score(y_val, preds)

        logger.info(f"Evaluation Results -> Accuracy: {val_acc:.4f}, F1-Score: {val_f1:.4f}, ROC-AUC: {val_roc_auc:.4f}")

        # Log hyperparameters to MLflow run
        MLflowManager.log_params({
            "model_architecture": "TF-IDF + Logistic Regression",
            "c_regularization": c_parameter,
            "train_size": len(X_train),
            "val_size": len(X_val),
            "dataset_size": dataset_size,
            "vectorizer_max_features": 1000,
            "vectorizer_ngram_range": "1, 2",
            "dataset_version": dataset_version
        })

        # Log evaluation metrics to MLflow run
        MLflowManager.log_metrics({
            "accuracy": val_acc,
            "precision": val_prec,
            "recall": val_rec,
            "f1_score": val_f1,
            "roc_auc": val_roc_auc,
            "training_time_seconds": training_time
        })

        # 7. Save local model files
        with open(vectorizer_path, "wb") as f:
            pickle.dump(vectorizer, f)
        with open(classifier_path, "wb") as f:
            pickle.dump(classifier, f)
        logger.info(f"Saved local models to '{vectorizer_path}' and '{classifier_path}'")

        # Log Confusion Matrix as an artifact
        try:
            cm = confusion_matrix(y_val, preds)
            cm_path = os.path.join(model_dir, "confusion_matrix.txt")
            with open(cm_path, "w") as f:
                f.write(str(cm))
            if mlflow:
                mlflow.log_artifact(cm_path)
        except Exception as e:
            logger.warning(f"Failed to log Confusion Matrix artifact: {e}")

        # Log Classification Report as an artifact
        try:
            report = classification_report(y_val, preds)
            report_path = os.path.join(model_dir, "classification_report.txt")
            with open(report_path, "w") as f:
                f.write(report)
            if mlflow:
                mlflow.log_artifact(report_path)
        except Exception as e:
            logger.warning(f"Failed to log Classification Report artifact: {e}")

        # 8. Log Model to MLflow Registry with Signatures and Input Examples
        model_info = None
        if mlflow:
            try:
                # Construct input example using first 5 validation rows
                input_example = pd.DataFrame(X_val_vec[:5].toarray())
                preds_example = classifier.predict(X_val_vec[:5])
                signature = infer_signature(input_example, preds_example)
                
                model_info = MLflowManager.log_model(
                    model=classifier, 
                    artifact_path="sklearn_logistic_regression",
                    registered_model_name="SecurePrompt_Sklearn_Classifier",
                    signature=signature,
                    input_example=input_example
                )
            except Exception as e:
                logger.error(f"Failed to log model signatures: {e}")

        # Register model and retrieve registered version number
        if run_id != "local_run" and model_info:
            version_num = MLflowManager.register_model_version(
                run_id=run_id,
                artifact_path="sklearn_logistic_regression",
                model_name="SecurePrompt_Sklearn_Classifier"
            )
            if version_num:
                model_version = version_num

        # Apply git commit and version tags to run and registry model version
        git_commit = get_git_commit()
        if run_id != "local_run":
            MLflowManager.set_run_tags(run_id, {
                "git_commit": git_commit,
                "code_version": "1.0.0",
                "model_version": str(model_version)
            })
            MLflowManager.set_model_version_tags(
                model_name="SecurePrompt_Sklearn_Classifier",
                version=model_version,
                tags={
                    "git_commit": git_commit,
                    "code_version": "1.0.0"
                }
            )

        # Highlight best performing model and automatically deploy (Production stage)
        is_best_run = True
        if run_id != "local_run":
            try:
                best_run = MLflowManager.highlight_best_run(metric_name="accuracy")
                if best_run and best_run["accuracy"] > val_acc:
                    is_best_run = False
            except Exception as e:
                logger.warning(f"Failed to search for best run: {e}")

        if is_best_run:
            # Save the best model separately
            best_dir = os.path.join(model_dir, "best_sklearn")
            os.makedirs(best_dir, exist_ok=True)
            with open(os.path.join(best_dir, "classifier.pkl"), "wb") as f:
                pickle.dump(classifier, f)
            with open(os.path.join(best_dir, "vectorizer.pkl"), "wb") as f:
                pickle.dump(vectorizer, f)
            logger.info(f"Saved the best Scikit-learn classifier model to: '{best_dir}'")
            
            # Transition best model version to Production stage
            if run_id != "local_run":
                MLflowManager.transition_model_stage(
                    model_name="SecurePrompt_Sklearn_Classifier",
                    version=model_version,
                    stage="Production"
                )

    # 9. Print Training Dashboard Summary
    print("\n" + "="*60)
    print("               MLOPS RETRAINING DASHBOARD               ")
    print("="*60)
    print(f"Experiment Name:     SecurePromptAI")
    print(f"Run ID:              {run_id}")
    print(f"Model Name:          SecurePrompt_Sklearn_Classifier")
    print(f"Model Version:       {model_version}")
    print(f"Accuracy:            {val_acc:.4f}")
    print(f"Precision:           {val_prec:.4f}")
    print(f"Recall:              {val_rec:.4f}")
    print(f"F1 Score:            {val_f1:.4f}")
    print(f"Training Time:       {training_time:.2f} seconds")
    print(f"MLflow Tracking URL: {MLflowManager.setup_mlflow() and MLflowManager.setup_mlflow() and os.getenv('MLFLOW_TRACKING_URI', 'http://localhost:5000')}")
    print("="*60 + "\n")

    return {"accuracy": val_acc, "f1_score": val_f1, "run_id": run_id, "version": model_version}


def train_distilbert(
    output_dir: str = "model/distilbert", 
    epochs: int = 2, 
    batch_size: int = 16, 
    dataset_size: int = 200
) -> Dict[str, Any]:
    """
    Trains a DistilBERT sequence classifier on synthetic prompt data,
    logs parameters and metrics to MLflow, and registers the model.
    """
    if not TORCH_AVAILABLE:
        logger.error("PyTorch or HuggingFace Transformers is not installed. DistilBERT training skipped.")
        return {}

    try:
        import accelerate
    except ImportError as e:
        logger.error(f"DistilBERT dependencies missing (e.g. accelerate): {e}. Skipping DistilBERT training.")
        return {}

    logger.info(f"Generating synthetic training dataset of size {dataset_size}...")
    dataset = DatasetGenerator.generate_list(size=dataset_size)
    
    texts = [d["text"] for d in dataset]
    labels = [int(d["is_sensitive"]) for d in dataset]

    # Compute dataset hash as dataset version
    try:
        data_str = json.dumps(dataset, sort_keys=True)
        dataset_version = hashlib.md5(data_str.encode("utf-8")).hexdigest()
    except Exception:
        dataset_version = "unknown"

    # Split: 80% train, 20% validation
    split_idx = int(len(texts) * 0.8)
    train_texts, val_texts = texts[:split_idx], texts[split_idx:]
    train_labels, val_labels = labels[:split_idx], labels[split_idx:]

    logger.info("Initializing DistilBERT tokenizer...")
    tokenizer = DistilBertTokenizerFast.from_pretrained('distilbert-base-uncased')

    logger.info("Tokenizing text datasets...")
    train_encodings = tokenizer(train_texts, truncation=True, padding=True, max_length=128)
    val_encodings = tokenizer(val_texts, truncation=True, padding=True, max_length=128)

    train_dataset = PromptDataset(train_encodings, train_labels)
    val_dataset = PromptDataset(val_encodings, val_labels)

    # 1. Start MLflow Run
    run_id = "local_run"
    model_version = 1
    val_acc = 0.0
    val_prec = 0.0
    val_rec = 0.0
    val_f1 = 0.0
    val_roc_auc = 0.0
    training_time = 0.0

    try:
        import mlflow
        from mlflow.models import infer_signature
    except ImportError:
        mlflow = None

    # Hugging Face evaluation metric computer
    def compute_metrics(eval_pred):
        predictions, labels = eval_pred
        import numpy as np
        from scipy.special import softmax
        from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score
        
        preds = np.argmax(predictions, axis=1)
        acc = accuracy_score(labels, preds)
        prec = precision_score(labels, preds, zero_division=0)
        rec = recall_score(labels, preds, zero_division=0)
        f1 = f1_score(labels, preds, zero_division=0)
        try:
            probs = softmax(predictions, axis=1)[:, 1]
            roc = roc_auc_score(labels, probs)
        except Exception:
            roc = roc_auc_score(labels, preds)
            
        return {
            "accuracy": acc,
            "precision": prec,
            "recall": rec,
            "f1_score": f1,
            "roc_auc": roc
        }

    start_time = time.time()

    with MLflowManager.start_run(run_name="DistilBERT_Classifier") as run:
        if run and hasattr(run, "info"):
            run_id = run.info.run_id
        
        logger.info("Loading pre-trained distilbert-base-uncased model...")
        model = DistilBertForSequenceClassification.from_pretrained('distilbert-base-uncased', num_labels=2)

        # Set up Training Arguments dynamically to support both older and newer versions of transformers
        args_dict = {
            "output_dir": './results',          
            "num_train_epochs": epochs,          
            "per_device_train_batch_size": batch_size,  
            "per_device_eval_batch_size": batch_size,   
            "warmup_steps": 50,                
            "weight_decay": 0.01,               
            "logging_dir": './logs',            
            "logging_steps": 10,
            "save_strategy": "epoch",
            "load_best_model_at_end": True,
            "metric_for_best_model": "loss"
        }
        
        import inspect
        sig = inspect.signature(TrainingArguments.__init__)
        if "eval_strategy" in sig.parameters:
            args_dict["eval_strategy"] = "epoch"
        else:
            args_dict["evaluation_strategy"] = "epoch"

        training_args = TrainingArguments(**args_dict)

        logger.info("Initializing HuggingFace Trainer with MLflow log callback...")
        trainer = Trainer(
            model=model,                         
            args=training_args,                  
            train_dataset=train_dataset,         
            eval_dataset=val_dataset,
            compute_metrics=compute_metrics,
            callbacks=[MLflowLoggingCallback()]  # Hook custom MLflow metric logging
        )

        logger.info("Starting training loop...")
        trainer.train()

        # Measure training duration
        training_time = time.time() - start_time

        # Evaluate performance on validation set
        eval_metrics = trainer.evaluate()
        logger.info(f"HuggingFace Validation Evaluation: {eval_metrics}")
        
        val_acc = eval_metrics.get("eval_accuracy", 0.0)
        val_prec = eval_metrics.get("eval_precision", 0.0)
        val_rec = eval_metrics.get("eval_recall", 0.0)
        val_f1 = eval_metrics.get("eval_f1_score", 0.0)
        val_roc_auc = eval_metrics.get("eval_roc_auc", 0.0)

        # Log hyperparameters to MLflow
        MLflowManager.log_params({
            "model_architecture": "DistilBERT",
            "epochs": epochs,
            "batch_size": batch_size,
            "train_dataset_size": len(train_texts),
            "val_dataset_size": len(val_texts),
            "dataset_size": dataset_size,
            "tokenizer_max_length": 128,
            "dataset_version": dataset_version
        })

        # Log evaluation metrics to MLflow
        MLflowManager.log_metrics({
            "accuracy": val_acc,
            "precision": val_prec,
            "recall": val_rec,
            "f1_score": val_f1,
            "roc_auc": val_roc_auc,
            "training_time_seconds": training_time,
            "eval_loss": eval_metrics.get("eval_loss", 0.0)
        })

        # Save model locally
        os.makedirs(output_dir, exist_ok=True)
        model.save_pretrained(output_dir)
        tokenizer.save_pretrained(output_dir)
        logger.info(f"Model files saved locally at '{output_dir}'")

        # Generate Confusion Matrix and Classification Report artifacts
        from sklearn.metrics import confusion_matrix, classification_report
        try:
            predictions_output = trainer.predict(val_dataset)
            import numpy as np
            val_preds = np.argmax(predictions_output.predictions, axis=1)

            cm = confusion_matrix(val_labels, val_preds)
            cm_path = os.path.join(output_dir, "confusion_matrix.txt")
            with open(cm_path, "w") as f:
                f.write(str(cm))
            
            report = classification_report(val_labels, val_preds)
            report_path = os.path.join(output_dir, "classification_report.txt")
            with open(report_path, "w") as f:
                f.write(report)

            if mlflow:
                mlflow.log_artifact(cm_path)
                mlflow.log_artifact(report_path)
        except Exception as e:
            logger.warning(f"Failed to log DistilBERT evaluation artifacts: {e}")

        # Log Model to MLflow Model Registry with signatures/examples
        model_info = None
        if mlflow:
            try:
                # DistilBERT model signature and inputs
                input_example = val_texts[:5]
                signature = infer_signature(input_example, val_preds[:5])
                
                model_info = MLflowManager.log_model(
                    model=model,
                    artifact_path="distilbert_prompt_classifier",
                    registered_model_name="SecurePrompt_DistilBERT_Classifier",
                    signature=signature,
                    input_example=input_example
                )
            except Exception as e:
                logger.error(f"Failed to log DistilBERT signatures: {e}")

        # Register version
        if run_id != "local_run" and model_info:
            version_num = MLflowManager.register_model_version(
                run_id=run_id,
                artifact_path="distilbert_prompt_classifier",
                model_name="SecurePrompt_DistilBERT_Classifier"
            )
            if version_num:
                model_version = version_num

        # Apply git and version tags
        git_commit = get_git_commit()
        if run_id != "local_run":
            MLflowManager.set_run_tags(run_id, {
                "git_commit": git_commit,
                "code_version": "1.0.0",
                "model_version": str(model_version)
            })
            MLflowManager.set_model_version_tags(
                model_name="SecurePrompt_DistilBERT_Classifier",
                version=model_version,
                tags={
                    "git_commit": git_commit,
                    "code_version": "1.0.0"
                }
            )

        # Highlight best model and automatically deploy (Production stage)
        is_best_run = True
        if run_id != "local_run":
            try:
                best_run = MLflowManager.highlight_best_run(metric_name="accuracy")
                if best_run and best_run["accuracy"] > val_acc:
                    is_best_run = False
            except Exception as e:
                logger.warning(f"Failed to search for best run: {e}")

        if is_best_run:
            # Save the best model separately
            best_dir = os.path.join(os.path.dirname(output_dir), "best_distilbert")
            os.makedirs(best_dir, exist_ok=True)
            model.save_pretrained(best_dir)
            tokenizer.save_pretrained(best_dir)
            logger.info(f"Saved the best DistilBERT model to: '{best_dir}'")
            
            if run_id != "local_run":
                MLflowManager.transition_model_stage(
                    model_name="SecurePrompt_DistilBERT_Classifier",
                    version=model_version,
                    stage="Production"
                )

    # Print Training Dashboard Summary
    print("\n" + "="*60)
    print("               MLOPS RETRAINING DASHBOARD               ")
    print("="*60)
    print(f"Experiment Name:     SecurePromptAI")
    print(f"Run ID:              {run_id}")
    print(f"Model Name:          SecurePrompt_DistilBERT_Classifier")
    print(f"Model Version:       {model_version}")
    print(f"Accuracy:            {val_acc:.4f}")
    print(f"Precision:           {val_prec:.4f}")
    print(f"Recall:              {val_rec:.4f}")
    print(f"F1 Score:            {val_f1:.4f}")
    print(f"Training Time:       {training_time:.2f} seconds")
    print(f"MLflow Tracking URL: {MLflowManager.setup_mlflow() and MLflowManager.setup_mlflow() and os.getenv('MLFLOW_TRACKING_URI', 'http://localhost:5000')}")
    print("="*60 + "\n")

    return {"eval_metrics": eval_metrics, "run_id": run_id, "version": model_version}


if __name__ == "__main__":
    # Test training loops
    # 1. Train Sklearn Fallback
    train_fallback_sklearn(dataset_size=100)

    # 2. Train DistilBERT
    if TORCH_AVAILABLE:
        train_distilbert(dataset_size=50, epochs=1)
    else:
        logger.warning("Torch library not available; skipping DistilBERT trainer verification.")
