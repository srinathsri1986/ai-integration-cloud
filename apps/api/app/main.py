from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import audit, cfo, connectors, flows, health, orchestrator
from app.core.config import get_settings
from app.core.logging import configure_logging

settings = get_settings()
configure_logging(settings.log_level)

app = FastAPI(
    title="NetSuite CFO Intelligence Orchestrator API",
    version="0.1.0",
    description="MVP API using mock NetSuite data and approved query templates.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(health.router)
app.include_router(cfo.router, prefix="/api/v1")
app.include_router(orchestrator.router, prefix="/api/v1")
app.include_router(audit.router, prefix="/api/v1")
app.include_router(connectors.router, prefix="/api/v1")
app.include_router(flows.router, prefix="/api/v1")
