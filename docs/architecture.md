# SecurePrompt AI - System Architecture Design

This document details the software and systems architecture of SecurePrompt AI and the integrated MLOps framework.

## 🗺️ System Component Mapping

```text
                  +------------------------------------------------------+
                  |               Client Chrome Extension                |
                  +------------------------------------------------------+
                                             |
                                     (HTTP POST /api/scan)
                                             v
+--------------------------------------------------------------------------------------+
|                                    NGINX Proxy                                       |
+--------------------------------------------------------------------------------------+
            |                                  |                           |
     (Proxy Pass /api)                 (Proxy Pass /mlflow)        (Proxy Pass /grafana)
            v                                  v                           v
+-----------------------+              +---------------+           +---------------+
|    FastAPI Backend    |              |  MLflow Server|           |    Grafana    |
+-----------------------+              +---------------+           +---------------+
      |           |                            ^                           ^
   (Read)     (Log Scan)                       |                           |
      |           v                            |                     (Scrape KPIs)
      |   +---------------+                    |                           |
      |   |  MongoDB DB   |                    |                           |
      |   +---------------+                    |                           |
      |           ^                            |                           |
      v           |                            |                           |
+-----------------------+                      |                           |
|       ML Engine       |                      |                           |
|  - Heuristics Scanner |                      |                           |
|  - DistilBERT NER     |                      |                           |
|  - Sklearn Classifier |----------------------+                           |
|  - Drift / Retraining |                                                  |
+-----------------------+                                                  |
      ^                                                                    |
      |                                                                    |
      +---------------------------------- Prometheus Scraper --------------+
```

---

## 🔄 Sequence Flow: Real-Time Interception API

```text
Client Chrome            NGINX            FastAPI         Prometheus         ML Engine
  Extension              Proxy            Backend          Scraper           Firewall
      |                    |                 |                |                 |
      |-- (POST /api/scan)->|                 |                |                 |
      |                    |-- (POST /api)-->|                |                 |
      |                    |                 |-- (Run scan)-------------------->|
      |                    |                 |<-- (Action, Risk Level, Score)---|
      |                    |                 |                |                 |
      |                    |                 |-- (Log Scan)--> [MongoDB]        |
      |                    |                 |-- (Record)----> [Prometheus      |
      |                    |                 |                 Metrics client]  |
      |                    |<-- (JSON Res)---|                |                 |
      |<-- (JSON Res)------|                 |                |                 |
      |                    |                 |                |                 |
      |                    |                 |<- (Scrape)-----|                 |
      |                    |                 |-- (Metrics)--->|                 |
```

---

## 📈 MLOps Lifecycle & Automation Mechanics

The platform establishes three core automated loops:

### 1. The Monitoring Loop
* Client submits prompts -> **Prometheus Middleware** records query latency and response actions.
* The `/metrics` router collects memory, CPU, and running accuracy.
* **Grafana** scrapes Prometheus every 5 seconds to update visualization panels.

### 2. The Data & Concept Drift Loop
* A scheduled cron task or administrator webhook triggers `/api/mlops/drift-check`.
* **DriftDetector** queries the target sample (last 100 prompts from MongoDB) and baseline training sizes.
* The detector calculates **Population Stability Index (PSI)**. If `PSI >= 0.25`, the data drift alert fires and triggers the Retraining Pipeline in the background.

### 3. The Retraining and Hot-Swap Loop
* **RetrainingPipeline** aggregates MongoDB prompt tables and baseline records.
* Retrains the classification model and tracks the dataset and models with DVC.
* Logs validation loss and accuracy parameters to **MLflow Registry**.
* If evaluation benchmarks match targets, promotes the version stage to `Production`.
* When `MLFLOW_MODEL_SYNC` is active, the FastAPI container downloads and hot-swaps the model weights at runtime.
