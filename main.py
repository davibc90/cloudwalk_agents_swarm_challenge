"""
    Main entry point for the FastAPI application.

    This module initializes the FastAPI application, configures the application 
    lifespan (startup and shutdown events), sets up logging, and registers 
    the available routers.

    Routers:
        - Invoke Agents Team (routes.invoke_route)
        - Ingest Data (routes.ingest_data_route)

    Logging:
        A custom logger is configured to capture application events.

    Lifespan:
        On startup: Logs "Application starting..."
        On shutdown: Logs "Application finishing..."
"""

from fastapi import FastAPI
from contextlib import asynccontextmanager
from utils.logger_utils import setup_logger

logger = setup_logger(__name__)

# Import routers
from routes.invoke_route import router as invoke_team_router
from routes.ingest_data_route import router as ingest_router

# Define the lifespan using an asynccontextmanager
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Application starting...")
    yield
    logger.info("Application finishing...")

# Initialize the FastAPI application with the defined lifespan
app = FastAPI(lifespan=lifespan)

# Register the routers
app.include_router(invoke_team_router, tags=["Invoke Agents Team"])
app.include_router(ingest_router, tags=["Ingest Data"])