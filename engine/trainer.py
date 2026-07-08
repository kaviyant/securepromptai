import os
import logging
import pickle
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
    
    # 1. Generate dataset
    df = DatasetGenerator.generate_dataframe(size=dataset_size)
    X = df["text"]
    y = df["is_sensitive"]

    # 2. Train-test split (80% train, 20% test)
    from sklearn.model_selection import train_test_split
    X_train, X_val, y_train, y_val = train_test_split(X, y, test_size=0.2, random_state=42)

    # 3. Setup MLflow Run
    with MLflowManager.start_run(run_name="Sklearn_Logistic_Regression") as run:
        run_id = run.info.run_id if run and hasattr(run, "info") else "local_run"
        
        # Log parameters
        MLflowManager.log_params({
            "model_architecture": "TF-IDF + Logistic Regression",
            "dataset_size": dataset_size,
            "c_regularization": c_parameter,
            "train_size": len(X_train),
            "val_size": len(X_val)
        })

        # 4. Vectorize
        from sklearn.feature_extraction.text import TfidfVectorizer
        vectorizer = TfidfVectorizer(max_features=1000, ngram_range=(1, 2))
        X_train_vec = vectorizer.fit_transform(X_train)
        X_val_vec = vectorizer.transform(X_val)

        # 5. Fit Classifier
        from sklearn.linear_model import LogisticRegression
        from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
        
        classifier = LogisticRegression(C=c_parameter)
        classifier.fit(X_train_vec, y_train)

        # 6. Evaluate
        preds = classifier.predict(X_val_vec)
        val_acc = accuracy_score(y_val, preds)
        val_prec = precision_score(y_val, preds, zero_division=0)
        val_rec = recall_score(y_val, preds, zero_division=0)
        val_f1 = f1_score(y_val, preds, zero_division=0)

        logger.info(f"Evaluation Results -> Accuracy: {val_acc:.4f}, F1-Score: {val_f1:.4f}")

        # Log metrics to MLflow
        MLflowManager.log_metrics({
            "accuracy": val_acc,
            "precision": val_prec,
            "recall": val_rec,
            "f1_score": val_f1
        })

        # 7. Save local model files
        with open(vectorizer_path, "wb") as f:
            pickle.dump(vectorizer, f)
        with open(classifier_path, "wb") as f:
            pickle.dump(classifier, f)
        logger.info(f"Saved local models to '{vectorizer_path}' and '{classifier_path}'")

        # 8. Log Model to MLflow Registry
        # Bundle vectorizer and classifier in a pipeline dict or log sklearn model
        class SklearnClassifierWrapper:
            def __init__(self, vec, clf):
                self.vectorizer = vec
                self.classifier = clf
            def predict(self, text_list):
                v = self.vectorizer.transform(text_list)
                return self.classifier.predict(v)
        
        wrapper = SklearnClassifierWrapper(vectorizer, classifier)
        MLflowManager.log_model(
            model=classifier, 
            artifact_path="sklearn_logistic_regression",
            registered_model_name="SecurePrompt_Sklearn_Classifier"
        )
        
    return {"accuracy": val_acc, "f1_score": val_f1, "run_id": run_id}


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

    logger.info(f"Generating synthetic training dataset of size {dataset_size}...")
    dataset = DatasetGenerator.generate_list(size=dataset_size)
    
    texts = [d["text"] for d in dataset]
    labels = [int(d["is_sensitive"]) for d in dataset]

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
    with MLflowManager.start_run(run_name="DistilBERT_Classifier") as run:
        run_id = run.info.run_id if run and hasattr(run, "info") else "local_run"
        
        # Log hyperparameters
        MLflowManager.log_params({
            "model_architecture": "DistilBERT",
            "epochs": epochs,
            "batch_size": batch_size,
            "dataset_size": dataset_size,
            "train_dataset_size": len(train_texts),
            "val_dataset_size": len(val_texts)
        })

        logger.info("Loading pre-trained distilbert-base-uncased model...")
        model = DistilBertForSequenceClassification.from_pretrained('distilbert-base-uncased', num_labels=2)

        # Set up Training Arguments
        training_args = TrainingArguments(
            output_dir='./results',          
            num_train_epochs=epochs,          
            per_device_train_batch_size=batch_size,  
            per_device_eval_batch_size=batch_size,   
            warmup_steps=50,                
            weight_decay=0.01,               
            logging_dir='./logs',            
            logging_steps=10,
            evaluation_strategy="epoch",
            save_strategy="epoch",
            load_best_model_at_end=True,
            metric_for_best_model="loss"
        )

        logger.info("Initializing HuggingFace Trainer with MLflow log callback...")
        trainer = Trainer(
            model=model,                         
            args=training_args,                  
            train_dataset=train_dataset,         
            eval_dataset=val_dataset,
            callbacks=[MLflowLoggingCallback()]  # Hook custom MLflow metric logging
        )

        logger.info("Starting training loop...")
        trainer.train()

        # Evaluate performance on validation set
        eval_metrics = trainer.evaluate()
        logger.info(f"HuggingFace Validation Evaluation: {eval_metrics}")
        
        # Log final evaluation metrics
        MLflowManager.log_metrics({
            "eval_loss": eval_metrics.get("eval_loss", 0.0),
            "eval_runtime": eval_metrics.get("eval_runtime", 0.0),
            "eval_samples_per_second": eval_metrics.get("eval_samples_per_second", 0.0)
        })

        # Save model locally
        os.makedirs(output_dir, exist_ok=True)
        model.save_pretrained(output_dir)
        tokenizer.save_pretrained(output_dir)
        logger.info(f"Model files saved locally at '{output_dir}'")

        # Log Model to MLflow Model Registry
        MLflowManager.log_model(
            model=model,
            artifact_path="distilbert_prompt_classifier",
            registered_model_name="SecurePrompt_DistilBERT_Classifier"
        )

    return {"eval_metrics": eval_metrics, "run_id": run_id}


if __name__ == "__main__":
    # Test training loops
    # 1. Train Sklearn Fallback
    train_fallback_sklearn(dataset_size=100)

    # 2. Train DistilBERT
    if TORCH_AVAILABLE:
        train_distilbert(dataset_size=50, epochs=1)
    else:
        logger.warning("Torch library not available; skipping DistilBERT trainer verification.")
