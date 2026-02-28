"""
Cenex AI FastAPI Application
Main entry point for the backend API.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import init_db
from app.api import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Handles startup and shutdown events.
    """
    # Startup
    print("🚀 Starting Cenex AI Backend...")
    print(f"📊 Environment: {settings.ENVIRONMENT}")
    print(f"🔐 Debug mode: {settings.DEBUG}")
    
    # Initialize database tables (for development only)
    if settings.ENVIRONMENT == "development":
        print("🗄️  Initializing database tables...")
        await init_db()
        print("✅ Database initialized")
    
    yield
    
    # Shutdown
    print("👋 Shutting down Cenex AI Backend...")


# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    description="Institutional-grade AI financial intelligence and smart brokerage platform",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router)


@app.get("/")
async def root():
    """Root endpoint - health check."""
    return {
        "app": settings.APP_NAME,
        "version": "0.1.0",
        "status": "operational",
        "environment": settings.ENVIRONMENT,
        "docs": "/docs",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    return {
        "status": "healthy",
        "environment": settings.ENVIRONMENT,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
    )
