import time

from starlette.requests import Request

from fastapi import FastAPI
from contextlib import asynccontextmanager
from loguru import logger

from cache.scheduler import setup_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler = setup_scheduler()
    try:
        yield
    finally:
        logger.info("Shutting down scheduler...")
        scheduler.shutdown(wait=False)


app = FastAPI(lifespan=lifespan)


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
