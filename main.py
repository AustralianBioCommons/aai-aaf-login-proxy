from fastapi.middleware.cors import CORSMiddleware
from proxy.dependencies import get_config
from utils.metrics import setup_metrics
import time

from starlette.requests import Request

from fastapi import FastAPI
from contextlib import asynccontextmanager
from loguru import logger

from cache.scheduler import setup_scheduler
from proxy.router import router as proxy_router
from utils import get_project_version

APP_VERSION = get_project_version()


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler = setup_scheduler()
    try:
        yield
    finally:
        logger.info("Shutting down scheduler...")
        scheduler.shutdown(wait=False)


def get_allowed_origins() -> list[str]:
    config = get_config()
    return config.allowed_origins


app = FastAPI(lifespan=lifespan, version=APP_VERSION)
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_allowed_origins(),
    allow_credentials=False,
    allow_methods=("GET",),
    allow_headers=("*",),
)

app.include_router(proxy_router, prefix="")


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """
    Add our own request logging that runs through loguru
    """
    start_time = time.perf_counter()
    response = await call_next(request)
    response_time = time.perf_counter() - start_time
    logger.info(
        f"{request.method} {request.url.path} {response.status_code} {response_time:.3f}s"
    )
    return response


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}


@app.get("/")
async def default():
    return {"message": "BioCommons Access login proxy", "version": APP_VERSION}


# Only enabled if ENABLED_METRICS env var is set
METRICS = setup_metrics(app)
