import os
import pickle
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report
from engine.mlflow_utils import MLflowManager

# Load backend/.env file configurations if it exists
ENV_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "backend", ".env")
if os.path.exists(ENV_PATH):
    print(f"Loading environment configurations from {ENV_PATH}...")
    with open(ENV_PATH, "r") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                os.environ[key.strip()] = val.strip().strip('"').strip("'")

# Output directory for models
MODEL_DIR = "model"
os.makedirs(MODEL_DIR, exist_ok=True)

def train_custom_dataset(dataset_path: str):
    """
    Loads custom dataset, maps features, trains Binary and 9-Class classifiers,
    and registers/promotes the champion binary model in the MLflow Registry.
    """
    if not os.path.exists(dataset_path):
        raise FileNotFoundError(f"Custom dataset not found at: {dataset_path}")

    print(f"Loading custom dataset from {dataset_path}...")
    df = pd.read_csv(dataset_path)

    # Clean rows with missing prompt contents
    original_len = len(df)
    df = df.dropna(subset=["prompt_content"])
    print(f"Loaded {len(df)} rows (dropped {original_len - len(df)} rows with missing prompts).")

    # ===================================================
    # 1. Map Columns to Classifier Labels
    # ===================================================
    # Map risk_level to is_sensitive (Low -> 0, Medium/High/Critical -> 1)
    df["is_sensitive"] = df["risk_level"].map({
        "Low": 0,
        "Medium": 1,
        "High": 1,
        "Critical": 1
    }).fillna(0).astype(int)

    # Map categories to the standard 9 classes used by PromptClassifier
    category_mapping = {
        "General Query": "General",
        "Coding Assistance": "Programming",
        "Source Code": "Programming",
        "Password": "Security",
        "API Key": "Security",
        "Customer Data": "Customer Data",
        "Document Review": "Internal Document",
        "Financial Data": "Finance"
    }
    df["mapped_category"] = df["category"].map(category_mapping).fillna("General")

    # ===================================================
    # 2. Train Binary Sensitivity Classifier
    # ===================================================
    print("\n--- Training Binary Sensitivity Classifier ---")
    X_bin = df["prompt_content"]
    y_bin = df["is_sensitive"]

    X_train_bin, X_val_bin, y_train_bin, y_val_bin = train_test_split(
        X_bin, y_bin, test_size=0.2, random_state=42
    )

    bin_vectorizer = TfidfVectorizer(max_features=3000, ngram_range=(1, 2))
    X_train_bin_vec = bin_vectorizer.fit_transform(X_train_bin)
    X_val_bin_vec = bin_vectorizer.transform(X_val_bin)

    run_id = "local_run"
    model_version = 1

    with MLflowManager.start_run(run_name="Logistic_Regression_Classifier") as run:
        if run and hasattr(run, "info"):
            run_id = run.info.run_id

        bin_classifier = LogisticRegression(C=1.5, max_iter=500)
        bin_classifier.fit(X_train_bin_vec, y_train_bin)

        preds_bin = bin_classifier.predict(X_val_bin_vec)
        val_acc_bin = accuracy_score(y_val_bin, preds_bin)
        print(f"Binary Classifier Validation Accuracy: {val_acc_bin:.4f}")
        print(classification_report(y_val_bin, preds_bin))

        # Log parameters and metrics to MLflow
        MLflowManager.log_params({
            "model_architecture": "TF-IDF + Logistic Regression (Custom 10k)",
            "c_regularization": 1.5,
            "train_size": len(X_train_bin),
            "val_size": len(X_val_bin),
            "dataset_size": len(df),
            "vectorizer_max_features": 3000
        })
        MLflowManager.log_metrics({
            "accuracy": val_acc_bin
        })

        # Save Binary weights locally
        with open(os.path.join(MODEL_DIR, "vectorizer.pkl"), "wb") as f:
            pickle.dump(bin_vectorizer, f)
        with open(os.path.join(MODEL_DIR, "classifier.pkl"), "wb") as f:
            pickle.dump(bin_classifier, f)
        print("Binary Classifier weights saved successfully.")

        # Log Model to MLflow Registry with Signatures
        model_info = None
        try:
            from mlflow.models import infer_signature
            input_example = pd.DataFrame(X_val_bin_vec[:5].toarray())
            preds_example = bin_classifier.predict(X_val_bin_vec[:5])
            signature = infer_signature(input_example, preds_example)
            
            model_info = MLflowManager.log_model(
                model=bin_classifier, 
                artifact_path="sklearn_logistic_regression",
                registered_model_name="SecurePrompt_Sklearn_Classifier",
                signature=signature,
                input_example=input_example
            )
        except Exception as e:
            print(f"Failed to log model signatures to MLflow: {e}")

        # Register and promote version
        if run_id != "local_run" and model_info:
            version_num = MLflowManager.register_model_version(
                run_id=run_id,
                artifact_path="sklearn_logistic_regression",
                model_name="SecurePrompt_Sklearn_Classifier"
            )
            if version_num:
                model_version = version_num
                # Automatically transition the stage to Production
                MLflowManager.transition_model_stage(
                    model_name="SecurePrompt_Sklearn_Classifier",
                    version=model_version,
                    stage="Production"
                )
                print(f"Model version updated to: Version {model_version} in 'Production'")

    # ===================================================
    # 3. Train 9-Class Category Classifier
    # ===================================================
    print("\n--- Training 9-Class Category Classifier ---")
    X_cat = df["prompt_content"]
    y_cat = df["mapped_category"]

    X_train_cat, X_val_cat, y_train_cat, y_val_cat = train_test_split(
        X_cat, y_cat, test_size=0.2, random_state=42
    )

    cat_vectorizer = TfidfVectorizer(max_features=3000, ngram_range=(1, 2))
    X_train_cat_vec = cat_vectorizer.fit_transform(X_train_cat)
    X_val_cat_vec = cat_vectorizer.transform(X_val_cat)

    with MLflowManager.start_run(run_name="Vector_Classification") as run:
        cat_classifier = LogisticRegression(C=1.5, max_iter=500)
        cat_classifier.fit(X_train_cat_vec, y_train_cat)

        preds_cat = cat_classifier.predict(X_val_cat_vec)
        val_acc_cat = accuracy_score(y_val_cat, preds_cat)
        print(f"9-Class Classifier Validation Accuracy: {val_acc_cat:.4f}")
        print(classification_report(y_val_cat, preds_cat))

        # Log parameters and metrics to MLflow
        MLflowManager.log_params({
            "model_architecture": "TF-IDF + Logistic Regression (9-Class Custom 10k)",
            "c_regularization": 1.5,
            "train_size": len(X_train_cat),
            "val_size": len(X_val_cat),
            "dataset_size": len(df),
            "vectorizer_max_features": 3000
        })
        MLflowManager.log_metrics({
            "accuracy": val_acc_cat
        })

        # Save 9-Class weights locally
        with open(os.path.join(MODEL_DIR, "classifier_9class_vec.pkl"), "wb") as f:
            pickle.dump(cat_vectorizer, f)
        with open(os.path.join(MODEL_DIR, "classifier_9class_cls.pkl"), "wb") as f:
            pickle.dump(cat_classifier, f)
        print("9-Class Classifier weights saved successfully.")

    print("\n" + "="*60)
    print("           CUSTOM DATASET TRAINING COMPLETE           ")
    print("="*60)
    print(f"Dataset Path:    {dataset_path}")
    print(f"Total Samples:   {len(df)}")
    print(f"Binary Accuracy: {val_acc_bin:.4f}")
    print(f"9-Class Accuracy: {val_acc_cat:.4f}")
    print(f"Active Model version: {model_version}")
    print("="*60 + "\n")

if __name__ == "__main__":
    train_custom_dataset("secureprompt_dataset_10000_realistic.csv")
