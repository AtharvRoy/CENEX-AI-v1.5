"""
Broker order execution API endpoints.
Place orders and execute trading signals.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
import logging

from app.core.database import get_db
from app.api.dependencies import get_current_user
from app.models.user import User
from app.models.portfolio import Portfolio
from app.models.signal import Signal
from app.models.trade import Trade
from app.schemas.broker import (
    PlaceOrderRequest,
    PlaceOrderResponse,
    ExecuteSignalRequest,
    ExecuteSignalResponse,
    OrderStatusResponse,
    PositionResponse,
    HoldingResponse,
    MarginResponse,
    PortfolioSyncResponse
)
from app.services.order_execution import OrderExecutionService, RiskValidationError
from app.services.portfolio_sync import PortfolioSyncService


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/broker", tags=["Broker Orders"])


@router.post("/order", response_model=PlaceOrderResponse)
async def place_order(
    request: PlaceOrderRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Place a manual order (not from signal).
    
    Includes full risk validation.
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
    
    if not portfolio.broker or not portfolio.broker_access_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Portfolio not connected to broker"
        )
    
    try:
        # Get broker client
        portfolio_sync = PortfolioSyncService(db)
        broker = await portfolio_sync.get_broker_client(portfolio)
        
        # Place order
        order_id = broker.place_order(
            symbol=request.symbol,
            exchange=request.exchange,
            transaction_type=request.transaction_type,
            quantity=request.quantity,
            order_type=request.order_type,
            product=request.product,
            price=request.price,
            trigger_price=request.trigger_price
        )
        
        # Create trade record
        trade = Trade(
            user_id=current_user.id,
            portfolio_id=portfolio.id,
            signal_id=None,  # Manual order
            symbol=request.symbol,
            trade_type=request.transaction_type,
            quantity=request.quantity,
            entry_price=request.price or 0.0,
            status="pending"
        )
        
        db.add(trade)
        await db.commit()
        await db.refresh(trade)
        
        estimated_cost = request.quantity * (request.price or 0.0)
        
        logger.info(
            f"Placed manual order for user {current_user.id}: "
            f"{request.transaction_type} {request.quantity} {request.symbol}, Order ID: {order_id}"
        )
        
        return PlaceOrderResponse(
            order_id=order_id,
            trade_id=trade.id,
            status="pending",
            symbol=request.symbol,
            transaction_type=request.transaction_type,
            quantity=request.quantity,
            price=request.price,
            estimated_cost=estimated_cost
        )
        
    except Exception as e:
        logger.error(f"Failed to place order: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to place order: {str(e)}"
        )


@router.post("/signals/{signal_id}/execute", response_model=ExecuteSignalResponse)
async def execute_signal(
    signal_id: int,
    request: ExecuteSignalRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Execute a trading signal.
    
    Includes automatic position sizing and full risk validation.
    """
    # Verify signal exists
    signal_result = await db.execute(
        select(Signal).where(Signal.id == signal_id)
    )
    signal = signal_result.scalar_one_or_none()
    
    if not signal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Signal {signal_id} not found"
        )
    
    # Verify portfolio belongs to user
    portfolio_result = await db.execute(
        select(Portfolio).where(
            Portfolio.id == request.portfolio_id,
            Portfolio.user_id == current_user.id
        )
    )
    portfolio = portfolio_result.scalar_one_or_none()
    
    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio not found"
        )
    
    if not portfolio.broker or not portfolio.broker_access_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Portfolio not connected to broker. Connect broker first."
        )
    
    try:
        # Execute with risk validation
        order_service = OrderExecutionService(db)
        result = await order_service.execute_signal(
            user_id=current_user.id,
            portfolio_id=request.portfolio_id,
            signal_id=signal_id,
            quantity=request.quantity,
            product=request.product,
            order_type=request.order_type
        )
        
        logger.info(
            f"Executed signal {signal_id} for user {current_user.id}: "
            f"Order ID {result['order_id']}, Trade ID {result['trade_id']}"
        )
        
        return ExecuteSignalResponse(
            order_id=result["order_id"],
            trade_id=result["trade_id"],
            status=result["status"],
            symbol=result["symbol"],
            transaction_type=result["transaction_type"],
            quantity=result["quantity"],
            price=result["price"],
            estimated_cost=result["estimated_cost"],
            signal_confidence=signal.confidence,
            risk_checks_passed=True
        )
        
    except RiskValidationError as e:
        logger.warning(f"Risk validation failed for signal {signal_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Risk validation failed: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Failed to execute signal {signal_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to execute signal: {str(e)}"
        )


@router.get("/orders", response_model=List[OrderStatusResponse])
async def get_orders(
    portfolio_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get today's orders from broker.
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
    
    if not portfolio.broker or not portfolio.broker_access_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Portfolio not connected to broker"
        )
    
    try:
        # Get broker client
        portfolio_sync = PortfolioSyncService(db)
        broker = await portfolio_sync.get_broker_client(portfolio)
        
        # Fetch orders
        orders = broker.get_orders()
        
        # Convert to response format
        order_responses = []
        for order in orders:
            order_responses.append(OrderStatusResponse(
                order_id=order.get("order_id", ""),
                status=order.get("status", ""),
                tradingsymbol=order.get("tradingsymbol", ""),
                transaction_type=order.get("transaction_type", ""),
                order_type=order.get("order_type", ""),
                quantity=order.get("quantity", 0),
                filled_quantity=order.get("filled_quantity", 0),
                pending_quantity=order.get("pending_quantity", 0),
                price=order.get("price"),
                average_price=order.get("average_price"),
                order_timestamp=order.get("order_timestamp")
            ))
        
        return order_responses
        
    except Exception as e:
        logger.error(f"Failed to fetch orders: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to fetch orders: {str(e)}"
        )


@router.get("/positions", response_model=List[PositionResponse])
async def get_positions(
    portfolio_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get current positions from broker.
    """
    # Verify portfolio
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
    
    try:
        portfolio_sync = PortfolioSyncService(db)
        positions_data = await portfolio_sync.sync_positions(portfolio_id)
        
        # Convert to response format
        positions = []
        for pos in positions_data["net_positions"]:
            positions.append(PositionResponse(
                tradingsymbol=pos.get("tradingsymbol", ""),
                exchange=pos.get("exchange", ""),
                product=pos.get("product", ""),
                quantity=pos.get("quantity", 0),
                average_price=pos.get("average_price", 0.0),
                last_price=pos.get("last_price", 0.0),
                pnl=pos.get("pnl", 0.0),
                value=pos.get("value", 0.0)
            ))
        
        return positions
        
    except Exception as e:
        logger.error(f"Failed to fetch positions: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to fetch positions: {str(e)}"
        )


@router.get("/holdings", response_model=List[HoldingResponse])
async def get_holdings(
    portfolio_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get long-term holdings from broker.
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
    
    try:
        portfolio_sync = PortfolioSyncService(db)
        holdings_data = await portfolio_sync.sync_holdings(portfolio_id)
        
        # Convert to response format
        holdings = []
        for holding in holdings_data["holdings"]:
            holdings.append(HoldingResponse(
                tradingsymbol=holding.get("tradingsymbol", ""),
                exchange=holding.get("exchange", ""),
                quantity=holding.get("quantity", 0),
                average_price=holding.get("average_price", 0.0),
                last_price=holding.get("last_price", 0.0),
                pnl=holding.get("pnl", 0.0),
                day_change=holding.get("day_change", 0.0),
                day_change_percentage=holding.get("day_change_percentage", 0.0)
            ))
        
        return holdings
        
    except Exception as e:
        logger.error(f"Failed to fetch holdings: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to fetch holdings: {str(e)}"
        )


@router.get("/portfolio/sync", response_model=PortfolioSyncResponse)
async def sync_portfolio(
    portfolio_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Full portfolio sync - positions, holdings, and margins.
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
    
    try:
        portfolio_sync = PortfolioSyncService(db)
        sync_data = await portfolio_sync.sync_full_portfolio(portfolio_id)
        
        # Build response
        positions = [
            PositionResponse(**{k: v for k, v in pos.items() if k in PositionResponse.model_fields})
            for pos in sync_data["positions"]["net_positions"]
        ]
        
        holdings = [
            HoldingResponse(**{k: v for k, v in h.items() if k in HoldingResponse.model_fields})
            for h in sync_data["holdings"]["holdings"]
        ]
        
        margin = MarginResponse(
            available_cash=sync_data["margins"]["available_cash"],
            used_margin=sync_data["margins"]["used_margin"],
            net=sync_data["margins"]["equity"].get("net", 0.0)
        )
        
        total_portfolio_value = (
            sync_data["holdings"]["total_value"] + 
            sync_data["margins"]["available_cash"]
        )
        
        return PortfolioSyncResponse(
            positions=positions,
            holdings=holdings,
            margin=margin,
            total_position_pnl=sync_data["positions"]["total_pnl"],
            total_holding_pnl=sync_data["holdings"]["total_pnl"],
            total_portfolio_value=total_portfolio_value,
            synced_at=sync_data["synced_at"]
        )
        
    except Exception as e:
        logger.error(f"Failed to sync portfolio: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to sync portfolio: {str(e)}"
        )
