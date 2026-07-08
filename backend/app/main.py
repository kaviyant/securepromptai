import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from app.config.settings import settings
from app.database.connection import connect_to_mongo, close_mongo_connection
from app.middleware.rate_limit import RateLimitingMiddleware
from app.middleware.logging import AuditLoggingMiddleware
from app.middleware.prometheus import PrometheusMiddleware
from app.api.routers import auth, security, llm, system, reports, metrics, mlops

# 1. Logging Setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("secureprompt")

# 2. FastAPI Lifespan Handler
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup and shutdown tasks.
    """
    # Startup actions
    await connect_to_mongo()
    yield
    # Shutdown actions
    await close_mongo_connection()

# Instantiate App
app = FastAPI(
    title=settings.APP_NAME,
    description="Enterprise prompt scanner, compliance auditor, and PII sanitizer backend with complete MLOps platform.",
    version="1.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# 3. CORS Configuration
# Allows requests from extensions (which run on chrome-extension:// origins)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 4. Custom Middlewares Registration
# Prometheus timing and metrics collector
app.add_middleware(PrometheusMiddleware)
# Sliding Window rate limiter: Max 150 requests per minute
app.add_middleware(RateLimitingMiddleware, requests_limit=150, window_seconds=60)
# Timing and metrics audit logger
app.add_middleware(AuditLoggingMiddleware)

# 5. Router Registrations
app.include_router(auth.router)
app.include_router(security.router)
app.include_router(llm.router)
app.include_router(system.router)
app.include_router(reports.router)
app.include_router(metrics.router)
app.include_router(mlops.router)

# 6. Global Error Exception Overrides
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Simplifies and formats validation error details.
    """
    logger.error(f"Validation failure: {exc.errors()}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": "Request body validation failed.",
            "errors": exc.errors()
        }
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Catches all unhandled exceptions to prevent server info leaks.
    """
    logger.critical(f"Unhandled Exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "An unexpected internal server error occurred. Please contact the administrator."
        }
    )

from fastapi.staticfiles import StaticFiles
import os

# Serve Admin Dashboard front-end static files
static_dir = os.path.abspath("backend/static")
os.makedirs(static_dir, exist_ok=True)
app.mount("/admin", StaticFiles(directory=static_dir, html=True), name="static_admin")

@app.get("/")
async def root():
    return {
        "message": "Welcome to SecurePrompt AI Backend APIs. Access /docs for Swagger UI documentation.",
        "status": "online"
    }
