import sys
import os

# Set stdout encoding to utf-8 on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

import mlflow
from mlflow.tracking import MlflowClient

# Connect to local SQLite MLflow tracking DB
mlflow.set_tracking_uri("sqlite:///mlflow.db")
client = MlflowClient()

print("=" * 115)
print(" " * 42 + "SECUREPROMPT AI - MLFLOW TRACKING DASHBOARD")
print("=" * 115)

# 1. Experiments
print("\n[+] EXPERIMENTS LIST:")
print("-" * 115)
experiments = client.search_experiments()
for exp in experiments:
    print(f"  * Experiment ID : {exp.experiment_id}")
    print(f"    Name          : {exp.name}")
    print(f"    Artifact Path : {exp.artifact_location}")
    print(f"    Lifecycle     : {exp.lifecycle_stage}")
    print("-" * 115)

# 2. Registered Model Registry & Versions
print("\n[+] MODEL REGISTRY & VERSIONS:")
print("-" * 115)
print(f"{'Model Name':<38} | {'Ver':<5} | {'Stage':<12} | {'Run ID':<32} | {'Creation Source'}")
print("-" * 115)
try:
    models = client.search_registered_models()
    for m in models:
        versions = client.search_model_versions(f"name='{m.name}'")
        for mv in versions:
            source_name = mv.source.replace("\\", "/").split("/")[-1] if mv.source else "N/A"
            print(f"{m.name:<38} | {mv.version:<5} | {mv.current_stage:<12} | {mv.run_id:<32} | {source_name}")
except Exception as e:
    print(f"Error reading model registry: {e}")
print("-" * 115)

# 3. Detailed Experiment Runs, Hyperparameters & Metrics
print("\n[+] EXPERIMENT RUNS & METRICS (Latest Runs):")
print("-" * 115)
exp_ids = [e.experiment_id for e in experiments]
runs = client.search_runs(experiment_ids=exp_ids, max_results=10)
for run in runs:
    r_id = run.info.run_id
    r_name = run.data.tags.get("mlflow.runName", "Unnamed Run")
    status = run.info.status
    metrics_str = ", ".join([f"{k}: {v:.4f}" for k, v in run.data.metrics.items()])
    params_str = ", ".join([f"{k}: {v}" for k, v in run.data.params.items()])
    tags_str = ", ".join([f"{k}: {v}" for k, v in run.data.tags.items() if not k.startswith("mlflow.")])

    print(f"  * Run ID   : {r_id}")
    print(f"    Name     : {r_name} | Status: {status}")
    print(f"    Metrics  : {metrics_str if metrics_str else 'N/A'}")
    print(f"    Params   : {params_str if params_str else 'N/A'}")
    if tags_str:
        print(f"    Tags     : {tags_str}")
    print("-" * 115)

print("=" * 115 + "\n")
