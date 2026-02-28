"""API router configuration."""

from fastapi import APIRouter
from app.api.endpoints import auth, signals, portfolio, market, broker_auth, broker_orders
from app.api import features, agents

# Create main API router
api_router = APIRouter(prefix="/api")

# Include all endpoint routers
api_router.include_router(auth.router)
api_router.include_router(signals.router)
api_router.include_router(portfolio.router)
api_router.include_router(market.router)
api_router.include_router(broker_auth.router)
api_router.include_router(broker_orders.router)
api_router.include_router(features.router)
api_router.include_router(agents.router)

__all__ = ["api_router"]
