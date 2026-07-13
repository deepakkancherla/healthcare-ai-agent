import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, status

from app.api.routes.chat import router as chat_router
from app.api.schemas import ServiceStatusResponse
from app.config import APP_NAME, APP_VERSION, configure_logging


configure_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    logger.info("Starting %s API version %s.", APP_NAME, APP_VERSION)
    yield
    logger.info("Stopping %s API.", APP_NAME)


app = FastAPI(
    title=APP_NAME,
    description="REST API for the Healthcare AI Agent.",
    version=APP_VERSION,
    lifespan=lifespan,
)

app.include_router(chat_router)


@app.get(
    "/",
    response_model=ServiceStatusResponse,
    status_code=status.HTTP_200_OK,
    tags=["health"],
)
def service_status() -> ServiceStatusResponse:
    return ServiceStatusResponse(
        service=APP_NAME,
        status="running",
        version=APP_VERSION,
    )
