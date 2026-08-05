import os
import pickle
import random
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report
from engine.dataset_generator import DatasetGenerator
from engine.mlflow_utils import MLflowManager

# Load backend/.env file if it exists to get the HF_TOKEN
ENV_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "backend", ".env")
if os.path.exists(ENV_PATH):
    print(f"Loading environment configurations from {ENV_PATH}...")
    with open(ENV_PATH, "r") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                os.environ[key.strip()] = val.strip().strip('"').strip("'")

# Ensure datasets is installed
try:
    from datasets import load_dataset
except ImportError as e:
    raise ImportError("Hugging Face 'datasets' library is required. Please install it with: pip install datasets") from e

# Output directory for models
MODEL_DIR = "model"
os.makedirs(MODEL_DIR, exist_ok=True)


def collect_hf_datasets(sample_size=1000):
    """
    Downloads and maps Hugging Face datasets to SecurePrompt categories:
    - databricks/databricks-dolly-15k -> General (with some Programming classification)
    - yahma/alpaca-cleaned -> General / Programming
    - medalpaca/medical_meadow_medical_flashcards -> Healthcare & Patient Records
    - financial_phrasebank -> Finance & Accounting
    """
    data = []

    # 1. Load databricks/databricks-dolly-15k (for General & Programming)
    print("Fetching databricks/databricks-dolly-15k...")
    try:
        dolly = load_dataset("databricks/databricks-dolly-15k", split="train")
        dolly_samples = random.sample(list(dolly), min(len(dolly), sample_size))
        for row in dolly_samples:
            prompt = row.get("instruction", "")
            if row.get("context"):
                prompt += "\n" + row["context"]
            
            # Simple heuristic mapping for coding category
            category = "Programming" if row.get("category") == "creative_writing" and "code" in prompt.lower() else "General"
            data.append({
                "text": prompt,
                "category": category,
                "is_sensitive": 0
            })
    except Exception as e:
        print(f"Skipping Dolly-15k due to error: {e}")

    # 2. Load yahma/alpaca-cleaned (for General and Programming prompts)
    print("Fetching yahma/alpaca-cleaned...")
    try:
        alpaca = load_dataset("yahma/alpaca-cleaned", split="train")
        alpaca_samples = random.sample(list(alpaca), min(len(alpaca), sample_size))
        for row in alpaca_samples:
            prompt = row.get("instruction", "")
            if row.get("input"):
                prompt += "\n" + row["input"]
                
            is_code = any(k in prompt.lower() for k in ["code", "function", "javascript", "python", "sql", "html"])
            category = "Programming" if is_code else "General"
            data.append({
                "text": prompt,
                "category": category,
                "is_sensitive": 0
            })
    except Exception as e:
        print(f"Skipping Alpaca-cleaned due to error: {e}")

    # 3. Load medical_meadow_medical_flashcards (for Healthcare & Patient Records)
    print("Fetching medalpaca/medical_meadow_medical_flashcards...")
    try:
        medical = load_dataset("medalpaca/medical_meadow_medical_flashcards", split="train")
        medical_samples = random.sample(list(medical), min(len(medical), sample_size))
        for row in medical_samples:
            prompt = row.get("input", "")
            data.append({
                "text": prompt,
                "category": "Healthcare",
                "is_sensitive": 0
            })
    except Exception as e:
        print(f"Skipping Medical Meadow due to error: {e}")

    # 4. Load financial_phrasebank (for Finance & Accounting)
    print("Fetching financial_phrasebank...")
    try:
        finance = load_dataset("financial_phrasebank", "sentences_allagree", split="train", trust_remote_code=True)
        finance_samples = random.sample(list(finance), min(len(finance), sample_size))
        for row in finance_samples:
            prompt = row.get("sentence", "")
            data.append({
                "text": prompt,
                "category": "Finance",
                "is_sensitive": 0
            })
    except Exception as e:
        print(f"Skipping Financial Phrasebank due to error: {e}")

    # 5. Add Sensitive/Threat Prompts for the Binary Classifier
    # Since HF datasets are mostly clean, we generate mock PII/secrets to train the binary classifier.
    print("Adding sensitive prompts from local templates...")
    synthetic_sensitive = DatasetGenerator.generate_list(size=len(data))
    for row in synthetic_sensitive:
        if row["is_sensitive"]:
            data.append({
                "text": row["text"],
                "category": "Security", # Maps to Security class
                "is_sensitive": 1
            })

    # Also augment other missing classes for the 9-class model to ensure a balanced dataset
    # Using the local generator to ensure we have a balanced multiclass dataset.
    print("Augmenting categories (HR, Legal, Customer Data, Internal Document, Security, Programming, Finance)...")
    for category in ["HR", "Legal", "Customer Data", "Internal Document", "Security", "Programming", "Finance"]:
        # Find templates in generator
        cat_samples = DatasetGenerator.generate_multiclass_list(size_per_class=sample_size // 2)
        for row in cat_samples:
            if row["category"] == category:
                data.append({
                    "text": row["text"],
                    "category": row["category"],
                    "is_sensitive": 1 if category in ["Security", "Customer Data", "Internal Document"] else 0
                })

    df = pd.DataFrame(data)
    print(f"Finished compiling datasets! Total records: {len(df)}")
    
    # Save the compiled dataset to disk
    dataset_path = "data/hf_compiled_dataset.csv"
    os.makedirs(os.path.dirname(dataset_path), exist_ok=True)
    df.to_csv(dataset_path, index=False)
    print(f"Compiled dataset saved to: {dataset_path}")
    
    return df

def train_and_save_classifiers(df):
    """
    Trains the Binary prompt classifier and the 9-Class category classifier,
    and logs the runs to MLflow.
    """
    # ==========================================
    # 1. Train Binary Sensitivity Classifier
    # ==========================================
    print("\n--- Training Binary Sensitivity Classifier ---")
    X_bin = df["text"]
    y_bin = df["is_sensitive"]

    X_train_bin, X_val_bin, y_train_bin, y_val_bin = train_test_split(
        X_bin, y_bin, test_size=0.2, random_state=42
    )

    bin_vectorizer = TfidfVectorizer(max_features=2000, ngram_range=(1, 2))
    X_train_bin_vec = bin_vectorizer.fit_transform(X_train_bin)
    X_val_bin_vec = bin_vectorizer.transform(X_val_bin)

    with MLflowManager.start_run(run_name="HF_Binary_Classifier") as run:
        bin_classifier = LogisticRegression(C=2.0, max_iter=500)
        bin_classifier.fit(X_train_bin_vec, y_train_bin)

        preds_bin = bin_classifier.predict(X_val_bin_vec)
        val_acc_bin = accuracy_score(y_val_bin, preds_bin)
        print(f"Binary Classifier Accuracy: {val_acc_bin:.4f}")
        print(classification_report(y_val_bin, preds_bin))

        # Log parameters and metrics to MLflow
        MLflowManager.log_params({
            "model_architecture": "TF-IDF + Logistic Regression (HF Dataset)",
            "c_regularization": 2.0,
            "train_size": len(X_train_bin),
            "val_size": len(X_val_bin),
            "dataset_size": len(df),
            "vectorizer_max_features": 2000
        })
        MLflowManager.log_metrics({
            "accuracy": val_acc_bin
        })

        # Save Binary weights
        with open(os.path.join(MODEL_DIR, "vectorizer.pkl"), "wb") as f:
            pickle.dump(bin_vectorizer, f)
        with open(os.path.join(MODEL_DIR, "classifier.pkl"), "wb") as f:
            pickle.dump(bin_classifier, f)
        print("Binary Classifier weights saved successfully.")

    # ==========================================
    # 2. Train 9-Class Category Classifier
    # ==========================================
    print("\n--- Training 9-Class Category Classifier ---")
    # Map raw HuggingFace categories to the exact engine classes
    class_mapping = {
        "Healthcare": "Healthcare",
        "Finance": "Finance",
        "Programming": "Programming",
        "HR": "HR",
        "Legal": "Legal",
        "Customer Data": "Customer Data",
        "Internal Document": "Internal Document",
        "Security": "Security",
        "General": "General"
    }
    
    df["mapped_category"] = df["category"].map(class_mapping).fillna("General")
    
    X_cat = df["text"]
    y_cat = df["mapped_category"]

    X_train_cat, X_val_cat, y_train_cat, y_val_cat = train_test_split(
        X_cat, y_cat, test_size=0.2, random_state=42
    )

    cat_vectorizer = TfidfVectorizer(max_features=2500, ngram_range=(1, 2))
    X_train_cat_vec = cat_vectorizer.fit_transform(X_train_cat)
    X_val_cat_vec = cat_vectorizer.transform(X_val_cat)

    with MLflowManager.start_run(run_name="HF_9Class_Classifier") as run:
        cat_classifier = LogisticRegression(C=2.0, max_iter=500)
        cat_classifier.fit(X_train_cat_vec, y_train_cat)

        preds_cat = cat_classifier.predict(X_val_cat_vec)
        val_acc_cat = accuracy_score(y_val_cat, preds_cat)
        print(f"9-Class Classifier Accuracy: {val_acc_cat:.4f}")
        print(classification_report(y_val_cat, preds_cat))

        # Log parameters and metrics to MLflow
        MLflowManager.log_params({
            "model_architecture": "TF-IDF + Logistic Regression (9-Class HF)",
            "c_regularization": 2.0,
            "train_size": len(X_train_cat),
            "val_size": len(X_val_cat),
            "dataset_size": len(df),
            "vectorizer_max_features": 2500
        })
        MLflowManager.log_metrics({
            "accuracy": val_acc_cat
        })

        # Save 9-Class weights
        with open(os.path.join(MODEL_DIR, "classifier_9class_vec.pkl"), "wb") as f:
            pickle.dump(cat_vectorizer, f)
        with open(os.path.join(MODEL_DIR, "classifier_9class_cls.pkl"), "wb") as f:
            pickle.dump(cat_classifier, f)
        print("9-Class Classifier weights saved successfully.")

if __name__ == "__main__":
    # If the compiled CSV exists, load it directly to train. Otherwise, collect from HF.
    dataset_path = "data/hf_compiled_dataset.csv"
    if os.path.exists(dataset_path):
        print(f"Found local compiled dataset at {dataset_path}. Training directly...")
        df = pd.read_csv(dataset_path)
        # Drop rows with missing text values to prevent scikit-learn vectorizer exceptions
        df = df.dropna(subset=["text"])
    else:
        print(f"Local compiled dataset not found. Downloading from Hugging Face...")
        df = collect_hf_datasets(sample_size=1000)
    
    train_and_save_classifiers(df)
