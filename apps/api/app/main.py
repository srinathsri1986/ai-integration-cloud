import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import audit, auth, cfo, connectors, flows, health, mappings, orchestrator
from app.core.config import get_settings
from app.core.config_validation import validate_settings_or_raise
from app.core.database import init_db
from app.core.logging import configure_logging

settings = get_settings()
configure_logging(settings.log_level)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    validation = validate_settings_or_raise(settings)
    init_db()
    logger.info(
        "Runtime configuration validated.",
        extra={
            "configPosture": validation.posture,
            "configWarnings": validation.warnings,
        },
    )
    yield


app = FastAPI(
    title="NetSuite CFO Intelligence Orchestrator API",
    version="0.1.0",
    description="MVP API using mock NetSuite data and approved query templates.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT"],
    allow_headers=["Authorization", "Content-Type"],
    expose_headers=["Set-Cookie"],
)

app.include_router(health.router)
app.include_router(auth.router, prefix="/api/v1")
app.include_router(cfo.router, prefix="/api/v1")
app.include_router(orchestrator.router, prefix="/api/v1")
app.include_router(audit.router, prefix="/api/v1")
app.include_router(connectors.router, prefix="/api/v1")
app.include_router(flows.router, prefix="/api/v1")
app.include_router(mappings.router, prefix="/api/v1")
