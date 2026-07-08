# SecurePrompt AI - Troubleshooting Guide

This guide details common diagnostics and resolutions for issues that may arise when running the SecurePrompt AI MLOps platform.

---

## 🔌 1. MongoDB Database Reconnection Errors

* **Symptom**: `Failed to initialize indexes or bootstrapping database: Connection refused`
* **Root Cause**: MongoDB is offline or configured on a different host port.
* **Troubleshooting Steps**:
  1. Check if MongoDB container is running:
     ```bash
     docker ps | grep mongodb
     ```
  2. Inspect container logs:
     ```bash
     docker logs secureprompt_mongodb
     ```
  3. Verify connection string in `.env` (it must use `mongodb` container name as host when inside docker-compose network: `MONGODB_URL=mongodb://mongodb:27017`).

---

## 🛠️ 2. Docker Compose Build Failures

* **Symptom**: `ModuleNotFoundError: No module named 'engine'` inside FastAPI container.
* **Root Cause**: Backend image was built without copying the sibling engine/ folder, or the context in `docker-compose.yml` was set to `/backend` instead of `/` (the project root).
* **Troubleshooting Steps**:
  1. Re-check the root `docker-compose.yml`. Ensure the `context` parameter for the backend build is set to `.`, and the `dockerfile` points to `backend/Dockerfile`.
  2. Clear cached docker layers and rebuild:
     ```bash
     docker compose down
     docker compose build --no-cache
     docker compose up -d
     ```

---

## 📈 3. MLflow Tracking Connection Drops

* **Symptom**: `Failed to log metrics/parameters to MLflow: Max retries exceeded` or warning logs on container startup.
* **Root Cause**: The MLflow tracking container takes longer to bootstrap than the FastAPI backend.
* **Troubleshooting Steps**:
  1. SecurePrompt has built-in graceful exception handlers for MLflow. The system will continue to operate, classify, and scan prompts in local fallback mode.
  2. Verify MLflow status:
     ```bash
     docker logs secureprompt_mlflow
     ```
  3. Confirm you can access `http://localhost:5000` via web browser. If running on a cloud VM, ensure port `5000` (or proxy path `/mlflow`) is whitelisted in your server security group.

---

## 💾 4. DVC Cache and Tracking Synchronization

* **Symptom**: `dvc command not found` when executing retraining script.
* **Root Cause**: DVC CLI utility package is missing from python path or system host.
* **Troubleshooting Steps**:
  1. SecurePrompt's `DvcManager` detects if DVC CLI is absent and falls back to generating mock `.dvc` files to avoid crashing the execution.
  2. Install DVC globally or inside virtual environment:
     ```bash
     pip install dvc
     ```
  3. To reset the DVC cache locally:
     ```bash
     dvc gc -f
     ```
