# IMPORTANT: Import paths FIRST to set up data containment before any ML libraries load
import backend.app.core.paths

from fastapi import FastAPI
from backend.app.core.config import settings
from backend.app.core.logger import logger
from backend.app.services.startup_check import run_startup_checks
from backend.app.api.routes import router

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting OpenReel API (Device: {settings.DEVICE})")
    run_startup_checks()
    yield

app = FastAPI(
    title="OpenReel API",
    description="Backend for OpenReel",
    version="0.1.0",
    lifespan=lifespan
)

app.include_router(router)
