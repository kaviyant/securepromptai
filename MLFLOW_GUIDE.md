# Connecting SecurePrompt AI Models to MLflow

This guide explains how to start your local **MLflow Tracking Server**, connect the model training pipeline to it, and view model metrics (like accuracy) and registered versions.

---

## 🔍 Why Did the Command Fail?

The command `mlflow --version` failed because the `mlflow` command-line utility is installed inside the project's Python virtual environment (`venv`), not in your global system PATH.

To run MLflow commands, you must either:
1. **Prefix the command** with the virtual environment path: `.\venv\Scripts\mlflow.exe`
2. **Activate the virtual environment** in your terminal first:
   * **PowerShell**: `.\venv\Scripts\Activate.ps1`
   * **Command Prompt (CMD)**: `.\venv\Scripts\activate.bat`

---

## 🏃 Step-by-Step Guide to Start MLflow and Check Accuracy

### Step 1: Start the Local MLflow Server
Run this command in a new terminal window to start the tracking server using the existing sqlite database (`mlflow.db`):

```powershell
.\venv\Scripts\mlflow.exe server --backend-store-uri sqlite:///mlflow.db --default-artifact-root ./mlruns --host 127.0.0.1 --port 5000
```

> [!NOTE]
> Once started, leave this terminal window running. You can access the MLflow dashboard by opening your browser and navigating to:
> **[http://localhost:5000](http://localhost:5000)**

---

### Step 2: Set the Tracking Environment Variable
To ensure that your training scripts connect to this local server (instead of the container address), set the `MLFLOW_TRACKING_URI` variable in your active terminal:

* **PowerShell**:
  ```powershell
  $env:MLFLOW_TRACKING_URI="http://localhost:5000"
  ```
* **Command Prompt (CMD)**:
  ```cmd
  set MLFLOW_TRACKING_URI=http://localhost:5000
  ```
* **Git Bash / Linux / macOS**:
  ```bash
  export MLFLOW_TRACKING_URI=http://localhost:5000
  ```

---

### Step 3: Run Model Retraining

You have two choices for retraining:

#### Option A: Quick Template Retraining (Synthetic Data)
Logs a fast training run using simple hand-crafted templates. Because templates are highly distinct, accuracy will usually be a perfect `1.0`:
```powershell
.\venv\Scripts\python.exe -m engine.trainer
```

#### Option B: Diverse Dataset Retraining (Hugging Face Datasets)
Trains both the Binary and 9-Class classifiers on over **7,900+ real-world prompts** (from databricks-dolly, alpaca-cleaned, medical-meadow, financial-phrasebank). This will yield realistic performance metrics in MLflow (e.g., ~98.7% accuracy for the 9-class model):
```powershell
.\venv\Scripts\python.exe -m engine.train_with_hf
```

#### Option C: Custom 10,000 Dataset Retraining (realistic prompts) [Recommended]
Trains the models on your custom `secureprompt_dataset_10000_realistic.csv` (10,000 realistic prompts with risk levels mapped). This automatically registers new model versions and transitions the champion binary classifier version to `Production` in the MLflow Model Registry:
```powershell
.\venv\Scripts\python.exe -m engine.train_with_custom_dataset
```

The scripts will:
1. Load training prompts.
2. Train a **TF-IDF + Logistic Regression** classifier.
3. Compute metrics (`accuracy`, `precision`, `recall`, `f1_score`).
4. Log runs directly into your MLflow experiments database and manage model version stages.

---

## 🖥️ How to Navigate the MLflow UI

Once you open **[http://localhost:5000](http://localhost:5000)** in your browser:

### 1. View Accuracy & Metrics (Experiments Tab)
1. Select the **`SecurePromptAI`** experiment from the left sidebar.
2. You will see a list of all training runs.
3. Look at the columns for:
   * **`accuracy`**: Shows the classifier's accuracy on the validation split.
   * **`f1_score`**, **`precision`**, and **`recall`**: Core performance measures.
4. Click on any run to inspect detailed logs, hyperparameters, and artifacts like the Confusion Matrix or Classification Report.

```text
+------------------------------------------------------------------------------------+
|  Runs | Created             | Duration | accuracy | f1_score | model_architecture  |
|-------|---------------------|----------|----------|----------|---------------------|
|  [ ]  | 2026-07-21 09:12:00 | 2.4s     | 0.9420   | 0.9385   | TF-IDF + LogReg     |
+------------------------------------------------------------------------------------+
```

### 2. View Model Versions & Stages (Models Tab)
1. Click on the **Models** tab in the top navigation bar.
2. Select **`SecurePrompt_Sklearn_Classifier`** or **`SecurePrompt_DistilBERT_Classifier`**.
3. You will see a list of registered versions (e.g. `Version 1`, `Version 2`).
4. Look at the **Stage** column to verify which version is tagged as **`Production`** (the active serving model).

---

## 💡 Quick Tips

* **Local Sync**: The FastAPI server checks for environment configurations. If you run your server locally with `MLFLOW_MODEL_SYNC=true` and `MLFLOW_TRACKING_URI=http://localhost:5000`, the backend will dynamically download and hot-swap the classifier to matching production weights.
* **Troubleshooting Connection**: If the training script cannot connect to MLflow, verify that `.\venv\Scripts\mlflow.exe server` is running on port 5000 and that you have set the environment variable correctly in your active terminal.
