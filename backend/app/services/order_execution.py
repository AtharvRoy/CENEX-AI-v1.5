"""
Order execution service with risk management (OMS/RMS).
Handles signal-to-order conversion with margin validation, position limits, and risk checks.
"""

from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from datetime import datetime, timedelta
from decimal import Decimal
import logging

from app.models.portfolio import Portfolio
from app.models.trade import Trade
from app.models.signal import Signal
from app.services.portfolio_sync import PortfolioSyncService
from app.services.brokers.base_broker import BaseBroker


logger = logging.getLogger(__name__)


class RiskValidationError(Exception):
    """Raised when risk validation fails."""
    pass


class OrderExecutionService:
    """
    Order execution with risk management.
    
    Risk checks:
    1. Margin validation (sufficient funds)
    2. Position size limits (max % per symbol)
    3. Daily loss limits (max loss per day)
    4. Open position limits (max concurrent positions)
    """
    
    # Risk parameters (can be moved to config/user settings)
    MAX_POSITION_SIZE_PCT = 0.10  # Max 10% of portfolio per position
    MAX_DAILY_LOSS_PCT = 0.05     # Max 5% daily loss
    MAX_OPEN_POSITIONS = 20       # Max concurrent positions
    MIN_AVAILABLE_MARGIN_PCT = 0.10  # Keep 10% margin buffer
    
    def __init__(self, db: AsyncSession):
        """
        Initialize order execution service.
        
        Args:
            db: Database session
        """
        self.db = db
        self.portfolio_sync = PortfolioSyncService(db)
    
    async def validate_margin(
        self,
        broker: BaseBroker,
        required_amount: float,
        portfolio_id: int
    ) -> None:
        """
        Validate sufficient margin is available.
        
        Args:
            broker: Broker client
            required_amount: Required margin for trade
            portfolio_id: Portfolio ID
        
        Raises:
            RiskValidationError: If insufficient margin
        """
        margins = broker.get_margins()
        equity = margins.get("equity", {})
        available = equity.get("available", {})
        available_cash = available.get("cash", 0.0)
        
        # Check with buffer
        min_required = required_amount / (1 - self.MIN_AVAILABLE_MARGIN_PCT)
        
        if available_cash < min_required:
            raise RiskValidationError(
                f"Insufficient margin. Required: ₹{min_required:.2f}, "
                f"Available: ₹{available_cash:.2f}"
            )
        
        logger.info(
            f"Margin check passed for portfolio {portfolio_id}: "
            f"Required ₹{required_amount:.2f}, Available ₹{available_cash:.2f}"
        )
    
    async def validate_position_size(
        self,
        portfolio_id: int,
        symbol: str,
        trade_value: float
    ) -> None:
        """
        Validate position size doesn't exceed limits.
        
        Args:
            portfolio_id: Portfolio ID
            symbol: Trading symbol
            trade_value: Value of new trade
        
        Raises:
            RiskValidationError: If position size exceeds limit
        """
        # Get total portfolio value
        portfolio_value = await self.portfolio_sync.get_portfolio_value(portfolio_id)
        
        # Check if trade value exceeds max position size
        max_position_value = portfolio_value * self.MAX_POSITION_SIZE_PCT
        
        if trade_value > max_position_value:
            raise RiskValidationError(
                f"Position size exceeds limit. Trade value: ₹{trade_value:.2f}, "
                f"Max allowed: ₹{max_position_value:.2f} ({self.MAX_POSITION_SIZE_PCT*100}% of portfolio)"
            )
        
        logger.info(
            f"Position size check passed: ₹{trade_value:.2f} <= ₹{max_position_value:.2f}"
        )
    
    async def validate_daily_loss_limit(self, user_id: int, portfolio_id: int) -> None:
        """
        Validate daily loss hasn't exceeded limit.
        
        Args:
            user_id: User ID
            portfolio_id: Portfolio ID
        
        Raises:
            RiskValidationError: If daily loss limit exceeded
        """
        # Get today's trades
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        
        result = await self.db.execute(
            select(func.sum(Trade.pnl))
            .where(
                and_(
                    Trade.user_id == user_id,
                    Trade.portfolio_id == portfolio_id,
                    Trade.executed_at >= today_start,
                    Trade.status.in_(["closed", "open"])
                )
            )
        )
        daily_pnl = result.scalar() or 0.0
        
        # Get portfolio value
        portfolio_value = await self.portfolio_sync.get_portfolio_value(portfolio_id)
        
        # Check if daily loss exceeds limit
        max_daily_loss = portfolio_value * self.MAX_DAILY_LOSS_PCT
        
        if daily_pnl < -max_daily_loss:
            raise RiskValidationError(
                f"Daily loss limit exceeded. Current loss: ₹{abs(daily_pnl):.2f}, "
                f"Max allowed: ₹{max_daily_loss:.2f} ({self.MAX_DAILY_LOSS_PCT*100}% of portfolio)"
            )
        
        logger.info(
            f"Daily loss check passed: ₹{daily_pnl:.2f} within limit ₹{max_daily_loss:.2f}"
        )
    
    async def validate_open_positions(self, user_id: int, portfolio_id: int) -> None:
        """
        Validate number of open positions doesn't exceed limit.
        
        Args:
            user_id: User ID
            portfolio_id: Portfolio ID
        
        Raises:
            RiskValidationError: If too many open positions
        """
        result = await self.db.execute(
            select(func.count(Trade.id))
            .where(
                and_(
                    Trade.user_id == user_id,
                    Trade.portfolio_id == portfolio_id,
                    Trade.status == "open"
                )
            )
        )
        open_positions = result.scalar() or 0
        
        if open_positions >= self.MAX_OPEN_POSITIONS:
            raise RiskValidationError(
                f"Too many open positions. Current: {open_positions}, "
                f"Max allowed: {self.MAX_OPEN_POSITIONS}"
            )
        
        logger.info(
            f"Open positions check passed: {open_positions}/{self.MAX_OPEN_POSITIONS}"
        )
    
    async def calculate_position_size(
        self,
        portfolio_id: int,
        signal: Signal,
        risk_per_trade_pct: float = 0.02  # 2% risk per trade
    ) -> int:
        """
        Calculate optimal position size based on risk.
        
        Args:
            portfolio_id: Portfolio ID
            signal: Trading signal
            risk_per_trade_pct: Risk per trade as % of portfolio (default 2%)
        
        Returns:
            Quantity to trade
        """
        # Get portfolio value
        portfolio_value = await self.portfolio_sync.get_portfolio_value(portfolio_id)
        
        # Calculate risk amount
        risk_amount = portfolio_value * risk_per_trade_pct
        
        # Calculate stop loss distance
        if signal.price_entry and signal.price_stoploss:
            stop_loss_distance = abs(signal.price_entry - signal.price_stoploss)
            
            # Position size = Risk amount / Stop loss distance
            if stop_loss_distance > 0:
                quantity = int(risk_amount / stop_loss_distance)
            else:
                # Fallback: 5% of portfolio
                quantity = int((portfolio_value * 0.05) / signal.price_entry)
        else:
            # No stop loss defined, use 5% of portfolio
            if signal.price_entry:
                quantity = int((portfolio_value * 0.05) / signal.price_entry)
            else:
                quantity = 1  # Minimum quantity
        
        # Ensure minimum quantity
        quantity = max(1, quantity)
        
        logger.info(
            f"Calculated position size: {quantity} shares "
            f"(Risk: ₹{risk_amount:.2f}, Portfolio: ₹{portfolio_value:.2f})"
        )
        
        return quantity
    
    async def execute_signal(
        self,
        user_id: int,
        portfolio_id: int,
        signal_id: int,
        quantity: Optional[int] = None,
        product: str = "CNC",  # CNC=delivery, MIS=intraday
        order_type: str = "LIMIT"
    ) -> Dict[str, Any]:
        """
        Execute a trading signal with full risk validation.
        
        Args:
            user_id: User ID
            portfolio_id: Portfolio ID
            signal_id: Signal ID to execute
            quantity: Override quantity (None = auto-calculate)
            product: Order product type (CNC, MIS)
            order_type: Order type (MARKET, LIMIT)
        
        Returns:
            {
                'order_id': '240228000123456',
                'trade_id': 789,
                'status': 'pending',
                'symbol': 'RELIANCE',
                'quantity': 10,
                'price': 2850.0,
                'estimated_cost': 28500.0
            }
        
        Raises:
            RiskValidationError: If risk validation fails
            ValueError: If signal or portfolio not found
        """
        # Get signal
        signal_result = await self.db.execute(
            select(Signal).where(Signal.id == signal_id)
        )
        signal = signal_result.scalar_one_or_none()
        
        if not signal:
            raise ValueError(f"Signal {signal_id} not found")
        
        # Check signal is recent (<5 minutes)
        signal_age = (datetime.utcnow() - signal.created_at).total_seconds()
        if signal_age > 300:  # 5 minutes
            raise RiskValidationError(
                f"Signal is too old ({signal_age:.0f}s). Signals expire after 5 minutes."
            )
        
        # Get portfolio
        portfolio_result = await self.db.execute(
            select(Portfolio).where(Portfolio.id == portfolio_id)
        )
        portfolio = portfolio_result.scalar_one_or_none()
        
        if not portfolio:
            raise ValueError(f"Portfolio {portfolio_id} not found")
        
        if portfolio.user_id != user_id:
            raise ValueError("Portfolio does not belong to user")
        
        # Get broker client
        broker = await self.portfolio_sync.get_broker_client(portfolio)
        
        # Calculate quantity if not provided
        if quantity is None:
            quantity = await self.calculate_position_size(portfolio_id, signal)
        
        # Determine transaction type
        if signal.signal_type in ["STRONG_BUY", "BUY"]:
            transaction_type = "BUY"
        elif signal.signal_type in ["STRONG_SELL", "SELL"]:
            transaction_type = "SELL"
        else:
            raise ValueError(f"Cannot execute signal type: {signal.signal_type}")
        
        # Calculate trade value
        price = signal.price_entry or 0.0
        trade_value = price * quantity
        
        # Risk validation checks
        await self.validate_margin(broker, trade_value, portfolio_id)
        await self.validate_position_size(portfolio_id, signal.symbol, trade_value)
        await self.validate_daily_loss_limit(user_id, portfolio_id)
        await self.validate_open_positions(user_id, portfolio_id)
        
        # All checks passed - place order
        try:
            order_id = broker.place_order(
                symbol=signal.symbol,
                exchange=signal.exchange,
                transaction_type=transaction_type,
                quantity=quantity,
                order_type=order_type,
                product=product,
                price=price if order_type == "LIMIT" else None
            )
            
            # Create trade record
            trade = Trade(
                user_id=user_id,
                portfolio_id=portfolio_id,
                signal_id=signal_id,
                symbol=signal.symbol,
                trade_type=transaction_type,
                quantity=quantity,
                entry_price=price,
                status="pending",
                executed_at=datetime.utcnow()
            )
            
            self.db.add(trade)
            await self.db.commit()
            await self.db.refresh(trade)
            
            logger.info(
                f"Executed signal {signal_id}: {transaction_type} {quantity} {signal.symbol} "
                f"@ ₹{price:.2f}, Order ID: {order_id}, Trade ID: {trade.id}"
            )
            
            return {
                "order_id": order_id,
                "trade_id": trade.id,
                "status": "pending",
                "symbol": signal.symbol,
                "transaction_type": transaction_type,
                "quantity": quantity,
                "price": price,
                "estimated_cost": trade_value,
                "product": product,
                "order_type": order_type
            }
            
        except Exception as e:
            logger.error(f"Failed to execute signal {signal_id}: {e}")
            await self.db.rollback()
            raise
    
    async def update_trade_status(
        self,
        trade_id: int,
        broker_order_id: str,
        broker: BaseBroker
    ) -> None:
        """
        Update trade status based on broker order status.
        
        Args:
            trade_id: Trade ID
            broker_order_id: Broker order ID
            broker: Broker client
        """
        # Get order status from broker
        order_history = broker.get_order_history(broker_order_id)
        
        if not order_history:
            return
        
        latest_order = order_history[-1]
        order_status = latest_order.get("status", "").upper()
        
        # Get trade
        result = await self.db.execute(
            select(Trade).where(Trade.id == trade_id)
        )
        trade = result.scalar_one_or_none()
        
        if not trade:
            return
        
        # Update trade status
        if order_status == "COMPLETE":
            trade.status = "open"
            filled_quantity = latest_order.get("filled_quantity", 0)
            avg_price = latest_order.get("average_price", 0.0)
            
            if filled_quantity > 0:
                trade.quantity = filled_quantity
                trade.entry_price = avg_price
            
            logger.info(f"Trade {trade_id} opened: {filled_quantity} @ ₹{avg_price:.2f}")
        
        elif order_status in ["CANCELLED", "REJECTED"]:
            trade.status = "cancelled"
            logger.info(f"Trade {trade_id} cancelled/rejected")
        
        await self.db.commit()
