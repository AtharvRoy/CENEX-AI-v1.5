"""
Portfolio sync service - syncs broker portfolio data to database.
Fetches positions, holdings, and margin data from broker API.
"""

from typing import Dict, List, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
import logging

from app.models.portfolio import Portfolio
from app.models.trade import Trade
from app.services.brokers.base_broker import BaseBroker
from app.services.brokers.zerodha_client import ZerodhaClient
from app.services.brokers.encryption import token_encryption


logger = logging.getLogger(__name__)


class PortfolioSyncService:
    """
    Sync user portfolio from broker to database.
    Updates positions, holdings, and margin data.
    """
    
    def __init__(self, db: AsyncSession):
        """
        Initialize portfolio sync service.
        
        Args:
            db: Database session
        """
        self.db = db
    
    async def get_broker_client(self, portfolio: Portfolio) -> BaseBroker:
        """
        Get authenticated broker client for portfolio.
        
        Args:
            portfolio: Portfolio model with broker credentials
        
        Returns:
            Authenticated broker client
        
        Raises:
            ValueError: If broker not supported or not connected
        """
        if not portfolio.broker:
            raise ValueError("Portfolio has no broker configured")
        
        if not portfolio.broker_access_token:
            raise ValueError("Portfolio not connected to broker (no access token)")
        
        # Decrypt access token
        access_token = token_encryption.decrypt(portfolio.broker_access_token)
        
        # Get API credentials from environment/config
        # In production, store these securely (env vars, secrets manager)
        from app.core.config import settings
        
        if portfolio.broker == "zerodha":
            api_key = getattr(settings, "ZERODHA_API_KEY", None)
            api_secret = getattr(settings, "ZERODHA_API_SECRET", None)
            
            if not api_key or not api_secret:
                raise ValueError("Zerodha API credentials not configured")
            
            client = ZerodhaClient(api_key=api_key, api_secret=api_secret)
            client.set_access_token(access_token)
            return client
        
        else:
            raise ValueError(f"Broker '{portfolio.broker}' not supported yet")
    
    async def sync_positions(self, portfolio_id: int) -> Dict[str, Any]:
        """
        Sync current positions from broker.
        
        Args:
            portfolio_id: Portfolio ID
        
        Returns:
            {
                'net_positions': [...],
                'day_positions': [...],
                'total_pnl': 1234.56,
                'synced_at': datetime
            }
        """
        # Get portfolio
        result = await self.db.execute(
            select(Portfolio).where(Portfolio.id == portfolio_id)
        )
        portfolio = result.scalar_one_or_none()
        
        if not portfolio:
            raise ValueError(f"Portfolio {portfolio_id} not found")
        
        # Get broker client
        broker = await self.get_broker_client(portfolio)
        
        # Fetch positions from broker
        positions_data = broker.get_positions()
        
        net_positions = positions_data.get("net", [])
        day_positions = positions_data.get("day", [])
        
        # Calculate total P&L
        total_pnl = sum(pos.get("pnl", 0.0) for pos in net_positions)
        
        logger.info(
            f"Synced positions for portfolio {portfolio_id}: "
            f"{len(net_positions)} net, {len(day_positions)} day, PnL: {total_pnl:.2f}"
        )
        
        return {
            "net_positions": net_positions,
            "day_positions": day_positions,
            "total_pnl": total_pnl,
            "synced_at": datetime.utcnow()
        }
    
    async def sync_holdings(self, portfolio_id: int) -> Dict[str, Any]:
        """
        Sync long-term holdings from broker.
        
        Args:
            portfolio_id: Portfolio ID
        
        Returns:
            {
                'holdings': [...],
                'total_value': 123456.78,
                'total_pnl': 12345.67,
                'synced_at': datetime
            }
        """
        # Get portfolio
        result = await self.db.execute(
            select(Portfolio).where(Portfolio.id == portfolio_id)
        )
        portfolio = result.scalar_one_or_none()
        
        if not portfolio:
            raise ValueError(f"Portfolio {portfolio_id} not found")
        
        # Get broker client
        broker = await self.get_broker_client(portfolio)
        
        # Fetch holdings from broker
        holdings = broker.get_holdings()
        
        # Calculate totals
        total_value = sum(
            h.get("quantity", 0) * h.get("last_price", 0.0) 
            for h in holdings
        )
        total_pnl = sum(h.get("pnl", 0.0) for h in holdings)
        
        logger.info(
            f"Synced holdings for portfolio {portfolio_id}: "
            f"{len(holdings)} holdings, Value: {total_value:.2f}, PnL: {total_pnl:.2f}"
        )
        
        return {
            "holdings": holdings,
            "total_value": total_value,
            "total_pnl": total_pnl,
            "synced_at": datetime.utcnow()
        }
    
    async def sync_margins(self, portfolio_id: int) -> Dict[str, Any]:
        """
        Sync available margin/funds from broker.
        
        Args:
            portfolio_id: Portfolio ID
        
        Returns:
            {
                'equity': {...},
                'commodity': {...},
                'available_cash': 50000.0,
                'used_margin': 25000.0,
                'synced_at': datetime
            }
        """
        # Get portfolio
        result = await self.db.execute(
            select(Portfolio).where(Portfolio.id == portfolio_id)
        )
        portfolio = result.scalar_one_or_none()
        
        if not portfolio:
            raise ValueError(f"Portfolio {portfolio_id} not found")
        
        # Get broker client
        broker = await self.get_broker_client(portfolio)
        
        # Fetch margins from broker
        margins = broker.get_margins()
        
        # Extract key values
        equity = margins.get("equity", {})
        available_cash = equity.get("available", {}).get("cash", 0.0)
        used_margin = equity.get("utilised", {}).get("debits", 0.0)
        
        logger.info(
            f"Synced margins for portfolio {portfolio_id}: "
            f"Available: {available_cash:.2f}, Used: {used_margin:.2f}"
        )
        
        return {
            "equity": equity,
            "commodity": margins.get("commodity", {}),
            "available_cash": available_cash,
            "used_margin": used_margin,
            "synced_at": datetime.utcnow()
        }
    
    async def sync_full_portfolio(self, portfolio_id: int) -> Dict[str, Any]:
        """
        Full portfolio sync - positions, holdings, and margins.
        
        Args:
            portfolio_id: Portfolio ID
        
        Returns:
            Combined sync data
        """
        try:
            positions = await self.sync_positions(portfolio_id)
            holdings = await self.sync_holdings(portfolio_id)
            margins = await self.sync_margins(portfolio_id)
            
            return {
                "positions": positions,
                "holdings": holdings,
                "margins": margins,
                "synced_at": datetime.utcnow()
            }
        except Exception as e:
            logger.error(f"Failed to sync portfolio {portfolio_id}: {e}")
            raise
    
    async def get_portfolio_value(self, portfolio_id: int) -> float:
        """
        Calculate total portfolio value.
        
        Args:
            portfolio_id: Portfolio ID
        
        Returns:
            Total portfolio value (cash + holdings + positions)
        """
        try:
            holdings_data = await self.sync_holdings(portfolio_id)
            margins_data = await self.sync_margins(portfolio_id)
            
            holdings_value = holdings_data["total_value"]
            available_cash = margins_data["available_cash"]
            
            total_value = holdings_value + available_cash
            
            logger.info(
                f"Portfolio {portfolio_id} value: "
                f"Holdings {holdings_value:.2f} + Cash {available_cash:.2f} = {total_value:.2f}"
            )
            
            return total_value
        except Exception as e:
            logger.error(f"Failed to calculate portfolio value: {e}")
            raise
