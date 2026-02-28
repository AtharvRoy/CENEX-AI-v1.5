"""
Abstract base class for broker integrations.
Defines the standard interface that all broker implementations must follow.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from datetime import datetime


class BaseBroker(ABC):
    """
    Abstract broker interface for trading operations.
    All broker implementations (Zerodha, Upstox, Angel One) must implement these methods.
    """
    
    def __init__(self, api_key: str, api_secret: str):
        """
        Initialize broker client.
        
        Args:
            api_key: Broker API key
            api_secret: Broker API secret
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.access_token: Optional[str] = None
    
    @abstractmethod
    def get_login_url(self) -> str:
        """
        Generate OAuth login URL for user authentication.
        
        Returns:
            Login URL to redirect user to broker's auth page
        """
        pass
    
    @abstractmethod
    def generate_session(self, request_token: str) -> Dict[str, Any]:
        """
        Exchange request token for access token.
        
        Args:
            request_token: Request token from OAuth callback
        
        Returns:
            Session data containing access_token, user_id, etc.
        """
        pass
    
    @abstractmethod
    def set_access_token(self, access_token: str) -> None:
        """
        Set access token for authenticated API calls.
        
        Args:
            access_token: Valid access token
        """
        pass
    
    @abstractmethod
    def get_profile(self) -> Dict[str, Any]:
        """
        Get user profile information.
        
        Returns:
            User profile data (name, email, broker_user_id, etc.)
        """
        pass
    
    @abstractmethod
    def get_margins(self) -> Dict[str, Any]:
        """
        Get available margin/funds.
        
        Returns:
            Margin data with available cash, used margin, etc.
        """
        pass
    
    @abstractmethod
    def get_positions(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get current positions.
        
        Returns:
            Dictionary with 'net' and 'day' positions
        """
        pass
    
    @abstractmethod
    def get_holdings(self) -> List[Dict[str, Any]]:
        """
        Get long-term holdings.
        
        Returns:
            List of holdings with symbol, quantity, average_price, etc.
        """
        pass
    
    @abstractmethod
    def place_order(
        self,
        symbol: str,
        exchange: str,
        transaction_type: str,
        quantity: int,
        order_type: str,
        product: str,
        price: Optional[float] = None,
        trigger_price: Optional[float] = None,
        **kwargs
    ) -> str:
        """
        Place a trade order.
        
        Args:
            symbol: Trading symbol (e.g., "RELIANCE")
            exchange: Exchange name (e.g., "NSE", "BSE")
            transaction_type: "BUY" or "SELL"
            quantity: Order quantity
            order_type: "MARKET", "LIMIT", "SL", "SL-M"
            product: "CNC" (delivery), "MIS" (intraday), "NRML" (F&O)
            price: Limit price (required for LIMIT orders)
            trigger_price: Trigger price (required for SL orders)
        
        Returns:
            Order ID
        """
        pass
    
    @abstractmethod
    def modify_order(
        self,
        order_id: str,
        quantity: Optional[int] = None,
        price: Optional[float] = None,
        order_type: Optional[str] = None,
        trigger_price: Optional[float] = None,
        **kwargs
    ) -> str:
        """
        Modify an existing order.
        
        Args:
            order_id: Order ID to modify
            quantity: New quantity (optional)
            price: New price (optional)
            order_type: New order type (optional)
            trigger_price: New trigger price (optional)
        
        Returns:
            Order ID
        """
        pass
    
    @abstractmethod
    def cancel_order(self, order_id: str, variety: str = "regular") -> str:
        """
        Cancel an order.
        
        Args:
            order_id: Order ID to cancel
            variety: Order variety (regular, amo, co, iceberg)
        
        Returns:
            Order ID
        """
        pass
    
    @abstractmethod
    def get_orders(self) -> List[Dict[str, Any]]:
        """
        Get all orders for the day.
        
        Returns:
            List of orders with status, filled quantity, etc.
        """
        pass
    
    @abstractmethod
    def get_order_history(self, order_id: str) -> List[Dict[str, Any]]:
        """
        Get order history and trades.
        
        Args:
            order_id: Order ID
        
        Returns:
            List of order state changes
        """
        pass
    
    @abstractmethod
    def get_trades(self) -> List[Dict[str, Any]]:
        """
        Get all executed trades for the day.
        
        Returns:
            List of executed trades
        """
        pass
    
    @abstractmethod
    def get_ltp(self, symbols: List[str], exchange: str = "NSE") -> Dict[str, float]:
        """
        Get last traded price for symbols.
        
        Args:
            symbols: List of trading symbols
            exchange: Exchange name
        
        Returns:
            Dictionary mapping symbol to last price
        """
        pass
    
    @abstractmethod
    def get_quote(self, symbols: List[str], exchange: str = "NSE") -> Dict[str, Dict[str, Any]]:
        """
        Get detailed quote data for symbols.
        
        Args:
            symbols: List of trading symbols
            exchange: Exchange name
        
        Returns:
            Dictionary mapping symbol to quote data (OHLC, volume, etc.)
        """
        pass
    
    def normalize_symbol(self, symbol: str, exchange: str = "NSE") -> str:
        """
        Normalize symbol format for the broker.
        Subclasses can override if needed.
        
        Args:
            symbol: Raw symbol (e.g., "RELIANCE.NS")
            exchange: Exchange name
        
        Returns:
            Broker-specific symbol format
        """
        # Remove common suffixes
        symbol = symbol.replace(".NS", "").replace(".BO", "").upper()
        return symbol
