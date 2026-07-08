# SecurePrompt AI - Local Installation & Configuration Guide

This guide describes how to set up the local developer environment to test and run the SecurePrompt AI MLOps platform locally.

## 📋 Prerequisites

Ensure your workstation has:
1. **Python 3.10** or higher.
2. **MongoDB** installed and running locally (default: `mongodb://localhost:27017`) if running outside Docker.
3. **Git** and **DVC CLI** (Optional, for dataset version tracking commands).

---

## ⚙️ Manual Setup

If you wish to run the components directly on your system without Docker:

### 1. Create and Activate a Virtual Environment
```bash
# Windows PowerShell
python -m venv venv
.\venv\Scripts\Activate.ps1

# Linux / macOS
python3 -m venv venv
source venv/bin/activate
```

### 2. Install Dependencies
```bash
# Install backend service dependencies
pip install -r backend/requirements.txt

# Install ML classification engine dependencies
pip install -r engine/requirements.txt

# Download Named Entity Recognition weights
python -m spacy download en_core_web_sm
```

### 3. Setup Local Environment Variables
Create a `.env` file in the project root:
```env
ENV_MODE=development
DEBUG=true
MONGODB_URL=mongodb://localhost:27017
DATABASE_NAME=secureprompt_db
JWT_SECRET_KEY=dev_jwt_secret_key_for_secure_testing_only
JWT_REFRESH_SECRET_KEY=dev_jwt_refresh_secret_key_for_secure_testing_only
GROQ_API_KEY=mock_key
MLFLOW_TRACKING_URI=http://localhost:5000
MLFLOW_MODEL_SYNC=false
```

---

## 🏃 Running Services Locally

### 1. Start MLflow (Local Server)
Run a local tracking server to capture metrics:
```bash
mlflow server --backend-store-uri sqlite:///mlflow.db --default-artifact-root ./mlruns --port 5000
```

### 2. Train Base Classification Models
Generate the synthetic dataset and train the baseline model:
```bash
# This will save vectorizer.pkl and classifier.pkl inside the /model folder
python -m engine.trainer
```

### 3. Launch FastAPI Application Server
Start the Uvicorn web gateway:
```bash
# From the root directory:
uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

### 4. Verify Local URLs
- **Web API Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Prometheus Scraper**: [http://localhost:8000/metrics](http://localhost:8000/metrics)
- **MLflow Board**: [http://localhost:5000](http://localhost:5000)
