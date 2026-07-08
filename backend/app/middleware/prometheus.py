import time
import os
import psutil
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry, generate_latest, CONTENT_TYPE_LATEST

# Create a custom registry to isolate our app metrics if needed, or use default
REGISTRY = CollectorRegistry()

# 1. Latency Metric
HTTP_REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    labelnames=["method", "endpoint"],
    registry=REGISTRY
)

# 2. Scanning & ML Model Metrics
PROMPT_SCANS_TOTAL = Counter(
    "secureprompt_scans_total",
    "Total prompts scanned by SecurePrompt AI",
    labelnames=["action", "risk_level", "model"],
    registry=REGISTRY
)

RISK_LEVEL_DISTRIBUTION = Counter(
    "secureprompt_risk_levels_total",
    "Total scanned prompts grouped by security risk level",
    labelnames=["risk_level"],
    registry=REGISTRY
)

MODEL_ACCURACY = Gauge(
    "secureprompt_model_accuracy_ratio",
    "Running accuracy of the prompt firewall classification engine",
    registry=REGISTRY
)

# 3. Model Drift Metrics
MODEL_DRIFT_INDEX = Gauge(
    "secureprompt_model_drift_psi",
    "Calculated Population Stability Index (PSI) drift metric",
    registry=REGISTRY
)

MODEL_DRIFT_ALERT = Gauge(
    "secureprompt_model_drift_alert",
    "Flag indicating whether prompt data distribution drift is detected (1=drift, 0=normal)",
    registry=REGISTRY
)

# 4. System Performance Metrics
SYSTEM_CPU_PERCENT = Gauge(
    "secureprompt_system_cpu_usage",
    "Active CPU consumption percentage of the container",
    registry=REGISTRY
)

SYSTEM_MEMORY_BYTES = Gauge(
    "secureprompt_system_memory_usage_bytes",
    "Active memory usage of the system in bytes",
    registry=REGISTRY
)

class PrometheusMetrics:
    """
    Central helper for updating Prometheus metrics from service endpoints.
    """
    @staticmethod
    def record_scan(action: str, risk_level: str, model: str):
        """
        Increments the prompt scanning counters.
        """
        try:
            PROMPT_SCANS_TOTAL.labels(action=action, risk_level=risk_level, model=model).inc()
            RISK_LEVEL_DISTRIBUTION.labels(risk_level=risk_level).inc()
        except Exception:
            pass

    @staticmethod
    def update_accuracy(accuracy: float):
        """
        Updates the current accuracy rating.
        """
        try:
            MODEL_ACCURACY.set(accuracy)
        except Exception:
            pass

    @staticmethod
    def record_drift(psi_score: float, is_drifted: bool):
        """
        Records model input drift values and toggles drift alarm.
        """
        try:
            MODEL_DRIFT_INDEX.set(psi_score)
            MODEL_DRIFT_ALERT.set(1.0 if is_drifted else 0.0)
        except Exception:
            pass

    @staticmethod
    def update_system_resources():
        """
        Queries system hardware and updates Prometheus gauges.
        """
        try:
            # CPU Percent
            cpu = psutil.cpu_percent(interval=None)
            SYSTEM_CPU_PERCENT.set(cpu)
            
            # Memory usage
            mem = psutil.virtual_memory()
            SYSTEM_MEMORY_BYTES.set(mem.used)
        except Exception:
            pass


class PrometheusMiddleware(BaseHTTPMiddleware):
    """
    HTTP Middleware that measures API latency and counts requests.
    """
    async def dispatch(self, request: Request, call_next) -> Response:
        # Exclude metric scrapes from latency histogram to avoid polluting metrics
        path = request.url.path
        if path == "/metrics":
            return await call_next(request)
            
        start_time = time.time()
        method = request.method
        
        try:
            response = await call_next(request)
            duration = time.time() - start_time
            
            # Record request latency
            HTTP_REQUEST_LATENCY.labels(method=method, endpoint=path).observe(duration)
            return response
            
        except Exception as e:
            duration = time.time() - start_time
            HTTP_REQUEST_LATENCY.labels(method=method, endpoint=path).observe(duration)
            raise e
