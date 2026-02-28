"""
Broker authentication API endpoints.
OAuth2 flow for connecting broker accounts.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
import logging

from app.core.database import get_db
from app.api.dependencies import get_current_user
from app.models.user import User
from app.models.portfolio import Portfolio
from app.schemas.broker import (
    BrokerConnectRequest,
    BrokerConnectResponse,
    BrokerCallbackRequest,
    BrokerDisconnectResponse
)
from app.services.brokers.zerodha_client import ZerodhaClient
from app.services.brokers.encryption import token_encryption
from app.core.config import settings


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/broker", tags=["Broker Authentication"])


@router.get("/zerodha/login")
async def initiate_zerodha_oauth(
    portfolio_id: int = Query(..., description="Portfolio ID to connect"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Initiate Zerodha OAuth flow.
    
    Returns login URL to redirect user to Zerodha's auth page.
    """
    # Verify portfolio belongs to user
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
    
    # Get Zerodha API credentials
    api_key = getattr(settings, "ZERODHA_API_KEY", None)
    api_secret = getattr(settings, "ZERODHA_API_SECRET", None)
    
    if not api_key or not api_secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Zerodha API credentials not configured"
        )
    
    # Generate login URL
    kite = ZerodhaClient(api_key=api_key, api_secret=api_secret)
    login_url = kite.get_login_url()
    
    logger.info(f"Generated Zerodha login URL for portfolio {portfolio_id}")
    
    return {
        "login_url": login_url,
        "portfolio_id": portfolio_id,
        "broker": "zerodha",
        "instructions": "Redirect user to login_url. After authentication, Zerodha will redirect to your callback URL with request_token."
    }


@router.post("/connect", response_model=BrokerConnectResponse)
async def connect_broker(
    request: BrokerConnectRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Connect broker account using OAuth request token.
    
    Call this endpoint after receiving request_token from OAuth callback.
    """
    # Verify portfolio belongs to user
    result = await db.execute(
        select(Portfolio).where(
            Portfolio.id == request.portfolio_id,
            Portfolio.user_id == current_user.id
        )
    )
    portfolio = result.scalar_one_or_none()
    
    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found"
        )
    
    # Currently only Zerodha supported
    if request.broker != "zerodha":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Broker '{request.broker}' not supported yet"
        )
    
    # Get API credentials
    api_key = getattr(settings, "ZERODHA_API_KEY", None)
    api_secret = getattr(settings, "ZERODHA_API_SECRET", None)
    
    if not api_key or not api_secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Zerodha API credentials not configured"
        )
    
    try:
        # Initialize client and generate session
        kite = ZerodhaClient(api_key=api_key, api_secret=api_secret)
        session_data = kite.generate_session(request.request_token)
        
        access_token = session_data.get("access_token")
        user_id = session_data.get("user_id")
        user_name = session_data.get("user_name")
        
        # Encrypt and store access token
        encrypted_token = token_encryption.encrypt(access_token)
        
        # Update portfolio
        portfolio.broker = "zerodha"
        portfolio.broker_access_token = encrypted_token
        
        await db.commit()
        
        # Get available margin
        kite.set_access_token(access_token)
        margins = kite.get_margins()
        available_margin = margins.get("equity", {}).get("available", {}).get("cash", 0.0)
        
        logger.info(
            f"Connected Zerodha account for portfolio {portfolio.id}, "
            f"User: {user_name} ({user_id})"
        )
        
        return BrokerConnectResponse(
            status="connected",
            portfolio_id=portfolio.id,
            broker="zerodha",
            broker_user_id=user_id,
            user_name=user_name,
            available_margin=available_margin,
            connected_at=portfolio.created_at
        )
        
    except Exception as e:
        logger.error(f"Failed to connect broker: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to connect broker: {str(e)}"
        )


@router.post("/disconnect", response_model=BrokerDisconnectResponse)
async def disconnect_broker(
    portfolio_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Disconnect broker account from portfolio.
    
    Removes stored access token.
    """
    # Verify portfolio belongs to user
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
    
    # Clear broker connection
    portfolio.broker = None
    portfolio.broker_access_token = None
    
    await db.commit()
    
    logger.info(f"Disconnected broker from portfolio {portfolio_id}")
    
    return BrokerDisconnectResponse(
        status="disconnected",
        portfolio_id=portfolio_id,
        message="Broker account disconnected successfully"
    )


@router.get("/status")
async def get_broker_status(
    portfolio_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get broker connection status for portfolio.
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
    
    is_connected = bool(portfolio.broker and portfolio.broker_access_token)
    
    return {
        "portfolio_id": portfolio_id,
        "broker": portfolio.broker,
        "is_connected": is_connected,
        "status": "connected" if is_connected else "not_connected"
    }
