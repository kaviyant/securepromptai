# SecurePrompt AI - API Reference Manual

This document details the API endpoints, request schemas, required authorization levels, and response formats.

---

## 🔐 Authentication Endpoints

### 1. User Registration
* **Endpoint**: `POST /api/register`
* **Access**: Public
* **Payload**:
  ```json
  {
    "username": "johndoe",
    "email": "johndoe@secureprompt.ai",
    "password": "SecurePassword123!",
    "role": "Employee",
    "department": "Engineering"
  }
  ```
* **Response (201 Created)**:
  ```json
  {
    "status": "success",
    "message": "User registered successfully."
  }
  ```

### 2. User Login
* **Endpoint**: `POST /api/login` (and `POST /api/login/json`)
* **Access**: Public
* **Payload (OAuth2 Password Form)**:
  * `username`: johndoe
  * `password`: SecurePassword123!
* **Response (200 OK)**:
  ```json
  {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh_token": "eyJhbGciOiJIUzI1...",
    "token_type": "bearer"
  }
  ```

---

## 🛡️ Security Interception & Scan APIs

### 1. Intercept Scan (Chrome Extension Endpoint)
* **Endpoint**: `POST /api/scan`
* **Access**: Public / Anonymous (supports optional Bearer Authorization)
* **Payload**:
  ```json
  {
    "prompt": "Connect database using AWS_KEY='AKIA1234567890ABCDEF'",
    "website": "chat.openai.com",
    "timestamp": 1720454400000,
    "session_id": "session-xyz",
    "browser_info": {
      "userAgent": "Chrome/122",
      "language": "en-US",
      "platform": "Win32"
    }
  }
  ```
* **Response (200 OK)**:
  ```json
  {
    "risk_score": 95,
    "risk_level": "Critical",
    "action": "BLOCK",
    "sanitized_prompt": "Connect database using AWS_KEY='[REDACTED_AWS_KEY]'",
    "reason": "Blocked: Critical risk level (Critical) identified. Reason: credentials/PII leakage detected.",
    "flagged_terms": ["AKIA1234567890ABCDEF"]
  }
  ```

### 2. Prompt Sanitizer helper
* **Endpoint**: `POST /api/sanitize`
* **Access**: Employee, Admin
* **Payload**:
  ```json
  {
    "prompt": "Email me at test@secureprompt.ai"
  }
  ```
* **Response (200 OK)**:
  ```json
  {
    "sanitized_prompt": "Email me at [REDACTED_EMAIL]",
    "flagged_terms": ["test@secureprompt.ai"]
  }
  ```

---

## 📈 Prometheus Scrapers

### 1. Prometheus Scraper Target
* **Endpoint**: `GET /metrics`
* **Access**: Public (internal container network)
* **Response (200 OK - Text/Plain)**:
  ```text
  # HELP http_request_duration_seconds HTTP request latency in seconds
  # TYPE http_request_duration_seconds histogram
  http_request_duration_seconds_bucket{endpoint="/api/scan",method="POST",le="0.1"} 42
  # HELP secureprompt_scans_total Total prompts scanned by SecurePrompt AI
  # TYPE secureprompt_scans_total counter
  secureprompt_scans_total{action="ALLOW",model="HeuristicRegex",risk_level="None"} 12
  ```

---

## 🛠️ MLOps Platform Controllers

### 1. Check Model Data Drift
* **Endpoint**: `POST /api/mlops/drift-check`
* **Access**: Admin (JWT Bearer Token Required)
* **Response (200 OK)**:
  ```json
  {
    "drift_detected": true,
    "psi": 0.2874,
    "ks_statistic": 0.145,
    "ks_p_value": 0.00341,
    "message": "Data drift detected! Input prompt distributions have shifted significantly. Retraining triggered automatically."
  }
  ```

### 2. Trigger Model Retraining
* **Endpoint**: `POST /api/mlops/retrain`
* **Access**: Admin (JWT Bearer Token Required)
* **Response (200 OK)**:
  ```json
  {
    "status": "started",
    "message": "Model retraining run initiated in the background. Check logs for status."
  }
  ```

### 3. Model Registry Status
* **Endpoint**: `GET /api/mlops/model-status`
* **Access**: Admin (JWT Bearer Token Required)
* **Response (200 OK)**:
  ```json
  {
    "distilbert_loaded": false,
    "sklearn_loaded": true,
    "mlflow_sync_active": true,
    "model_directory": "model",
    "tracking_uri": "http://mlflow:5000"
  }
  ```

### 4. Administrative Audit & Labeling Feedback
* **Endpoint**: `POST /api/mlops/feedback`
* **Access**: Admin (JWT Bearer Token Required)
* **Payload**:
  ```json
  {
    "prompt_id": "65ebd1bc4ef81c8567ad92cf",
    "feedback_correct": false,
    "audited_risk_level": "High"
  }
  ```
* **Response (200 OK)**:
  ```json
  {
    "status": "success",
    "message": "Feedback registered successfully.",
    "running_accuracy": 0.92,
    "total_audited": 25
  }
  ```
