from fastapi import APIRouter, Response
from app.middleware.prometheus import REGISTRY, generate_latest, CONTENT_TYPE_LATEST, PrometheusMetrics

router = APIRouter()

@router.get("/metrics")
async def get_metrics():
    """
    Exposes raw Prometheus metrics for collection/scraping.
    Triggers dynamic updates for container CPU and memory usage.
    """
    # Fetch current CPU and Memory states
    PrometheusMetrics.update_system_resources()
    
    # Return formatted metrics text
    return Response(
        content=generate_latest(REGISTRY),
        media_type=CONTENT_TYPE_LATEST
    )
