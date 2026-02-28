"""
Portfolio endpoints (stubs for now - will be implemented in Sprint 03+).
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.models import User, Portfolio
from app.api.dependencies import get_current_user


router = APIRouter(prefix="/portfolio", tags=["Portfolio"])


@router.get("/")
async def list_portfolios(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List user's portfolios.
    
    **Status**: Stub endpoint - returns empty list for now.
    **Coming in Sprint 03**: Portfolio management and tracking.
    """
    result = await db.execute(
        select(Portfolio).where(Portfolio.user_id == current_user.id)
    )
    portfolios = result.scalars().all()
    
    return {
        "portfolios": portfolios,
        "total": len(portfolios)
    }


@router.get("/{portfolio_id}")
async def get_portfolio(
    portfolio_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get a specific portfolio by ID.
    
    **Status**: Stub endpoint.
    """
    result = await db.execute(
        select(Portfolio).where(
            Portfolio.id == portfolio_id,
            Portfolio.user_id == current_user.id
        )
    )
    portfolio = result.scalar_one_or_none()
    
    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found"
        )
    
    return portfolio
