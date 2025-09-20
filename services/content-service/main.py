"""
Content Service - FastAPI Application

Main application entry point for the content service.
Handles RSS feed ingestion, content processing, and content management.
"""

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn

from .config import get_settings
from .database import get_db
from .routers import content, sources, health


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan events manager.
    
    Handles startup and shutdown events for the FastAPI application.
    This includes initializing background tasks, RSS feed monitoring,
    and cleanup operations.
    
    Args:
        app: FastAPI application instance
        
    Yields:
        Control to the application during its runtime
    """
    # Startup
    print("Content Service starting up...")
    # TODO: Initialize RSS feed monitoring
    # TODO: Start background tasks
    yield
    # Shutdown
    print("Content Service shutting down...")
    # TODO: Cleanup background tasks


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.
    
    Sets up the FastAPI instance with proper configuration including:
    - Application metadata (title, description, version)
    - CORS middleware for cross-origin requests
    - Router inclusion for different API endpoints
    - Lifespan event handling
    
    Returns:
        FastAPI: Configured FastAPI application instance
    """
    settings = get_settings()
    
    app = FastAPI(
        title="Content Service",
        description="RSS feed ingestion and content management service",
        version="1.0.0",
        lifespan=lifespan
    )
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include routers
    app.include_router(health.router, prefix="/health", tags=["health"])
    app.include_router(content.router, prefix="/content", tags=["content"])
    app.include_router(sources.router, prefix="/sources", tags=["sources"])
    
    return app


app = create_app()


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        log_level="info"
    )