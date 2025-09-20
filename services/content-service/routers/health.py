"""
Health check endpoints
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from ..database import get_db
from ..config import get_settings

router = APIRouter()


@router.get("/")
async def health_check():
    """
    Basic health check endpoint.
    
    Provides a simple health status for load balancers and monitoring
    systems. Returns immediately without checking dependencies.
    
    Returns:
        Dict: Basic health status with service identification
    """
    return {"status": "healthy", "service": "content-service"}


@router.get("/detailed")
async def detailed_health_check(db: Session = Depends(get_db)):
    """
    Detailed health check including database connectivity.
    
    Performs comprehensive health checks including database connection
    testing and dependency validation. Used for monitoring and
    debugging purposes.
    
    Args:
        db: Database session dependency for connectivity testing
        
    Returns:
        Dict: Detailed health status including:
            - Overall service status
            - Database connectivity status
            - Service version
            - Individual component health
    """
    try:
        # Test database connection
        db.execute(text("SELECT 1"))
        db_status = "healthy"
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"
    
    return {
        "status": "healthy" if db_status == "healthy" else "unhealthy",
        "service": "content-service",
        "database": db_status,
        "version": "1.0.0"
    }


@router.get("/ready")
async def readiness_check(db: Session = Depends(get_db)):
    """
    Readiness check for Kubernetes and deployment systems.
    
    Validates that the service is ready to receive traffic by
    checking critical dependencies. Used by orchestration systems
    to determine when to route traffic to the service.
    
    Args:
        db: Database session dependency for readiness validation
        
    Returns:
        Dict: Readiness status indicating if service can accept requests
    """
    try:
        # Check if we can connect to database
        db.execute(text("SELECT 1"))
        return {"ready": True}
    except Exception:
        return {"ready": False}