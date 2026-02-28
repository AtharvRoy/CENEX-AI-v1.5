"""
Zerodha Kite API client implementation.
Implements the BaseBroker interface using the official kiteconnect SDK.
"""

from typing import Dict, List, Optional, Any
from kiteconnect import KiteConnect
from kiteconnect.exceptions import KiteException
import logging

from .base_broker import BaseBroker


logger = logging.getLogger(__name__)


class ZerodhaClient(BaseBroker):
    """
    Zerodha Kite API implementation.
    
    Docs: https://kite.trade/docs/connect/v3/
    """
    
    # Exchange mappings
    EXCHANGE_NSE = "NSE"
    EXCHANGE_BSE = "BSE"
    
    # Transaction types
    TRANSACTION_TYPE_BUY = "BUY"
    TRANSACTION_TYPE_SELL = "SELL"
    
    # Order types
    ORDER_TYPE_MARKET = "MARKET"
    ORDER_TYPE_LIMIT = "LIMIT"
    ORDER_TYPE_SL = "SL"
    ORDER_TYPE_SL_M = "SL-M"
    
    # Product types
    PRODUCT_CNC = "CNC"  # Cash & Carry (delivery)
    PRODUCT_MIS = "MIS"  # Margin Intraday Square-off
    PRODUCT_NRML = "NRML"  # Normal (F&O)
    
    # Order varieties
    VARIETY_REGULAR = "regular"
    VARIETY_AMO = "amo"
    VARIETY_CO = "co"
    VARIETY_ICEBERG = "iceberg"
    
    def __init__(self, api_key: str, api_secret: str):
        """
        Initialize Zerodha Kite client.
        
        Args:
            api_key: Kite Connect API key
            api_secret: Kite Connect API secret
        """
        super().__init__(api_key, api_secret)
        self.kite = KiteConnect(api_key=api_key)
        logger.info("Initialized Zerodha Kite client")
    
    def get_login_url(self) -> str:
        """Generate OAuth login URL."""
        return self.kite.login_url()
    
    def generate_session(self, request_token: str) -> Dict[str, Any]:
        """
        Exchange request token for access token.
        
        Args:
            request_token: Request token from OAuth callback
        
        Returns:
            Session data with access_token, user_id, etc.
        """
        try:
            data = self.kite.generate_session(request_token, api_secret=self.api_secret)
            self.access_token = data["access_token"]
            self.kite.set_access_token(self.access_token)
            logger.info(f"Generated session for user: {data.get('user_id')}")
            return data
        except KiteException as e:
            logger.error(f"Failed to generate session: {e}")
            raise
    
    def set_access_token(self, access_token: str) -> None:
        """Set access token for authenticated requests."""
        self.access_token = access_token
        self.kite.set_access_token(access_token)
        logger.debug("Access token set")
    
    def get_profile(self) -> Dict[str, Any]:
        """
        Get user profile.
        
        Returns:
            {
                'user_id': 'AB1234',
                'user_name': 'John Doe',
                'email': 'john@example.com',
                'broker': 'ZERODHA',
                'exchanges': ['NSE', 'BSE', 'NFO', ...],
                'products': ['CNC', 'MIS', 'NRML'],
                'order_types': ['MARKET', 'LIMIT', 'SL', 'SL-M']
            }
        """
        try:
            return self.kite.profile()
        except KiteException as e:
            logger.error(f"Failed to get profile: {e}")
            raise
    
    def get_margins(self) -> Dict[str, Any]:
        """
        Get available margins.
        
        Returns:
            {
                'equity': {
                    'enabled': True,
                    'net': 100000.0,
                    'available': {
                        'adhoc_margin': 0.0,
                        'cash': 50000.0,
                        'collateral': 0.0,
                        'intraday_payin': 0.0
                    },
                    'utilised': {
                        'debits': 50000.0,
                        'exposure': 25000.0,
                        'm2m_realised': 0.0,
                        'm2m_unrealised': 0.0,
                        'option_premium': 0.0,
                        'payout': 0.0,
                        'span': 25000.0,
                        'holding_sales': 0.0,
                        'turnover': 0.0,
                        'liquid_collateral': 0.0,
                        'stock_collateral': 0.0
                    }
                },
                'commodity': {...}
            }
        """
        try:
            return self.kite.margins()
        except KiteException as e:
            logger.error(f"Failed to get margins: {e}")
            raise
    
    def get_positions(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get current positions.
        
        Returns:
            {
                'net': [
                    {
                        'tradingsymbol': 'RELIANCE',
                        'exchange': 'NSE',
                        'product': 'CNC',
                        'quantity': 10,
                        'overnight_quantity': 0,
                        'multiplier': 1,
                        'average_price': 2850.0,
                        'close_price': 2860.0,
                        'last_price': 2865.0,
                        'value': 28500.0,
                        'pnl': 150.0,
                        'm2m': 150.0,
                        'unrealised': 150.0,
                        'realised': 0.0,
                        'buy_quantity': 10,
                        'buy_price': 2850.0,
                        'buy_value': 28500.0,
                        'buy_m2m': 150.0,
                        'sell_quantity': 0,
                        'sell_price': 0.0,
                        'sell_value': 0.0,
                        'sell_m2m': 0.0,
                        'day_buy_quantity': 10,
                        'day_buy_price': 2850.0,
                        'day_buy_value': 28500.0,
                        'day_sell_quantity': 0,
                        'day_sell_price': 0.0,
                        'day_sell_value': 0.0
                    }
                ],
                'day': [...]
            }
        """
        try:
            return self.kite.positions()
        except KiteException as e:
            logger.error(f"Failed to get positions: {e}")
            raise
    
    def get_holdings(self) -> List[Dict[str, Any]]:
        """
        Get long-term holdings.
        
        Returns:
            [
                {
                    'tradingsymbol': 'INFY',
                    'exchange': 'NSE',
                    'isin': 'INE009A01021',
                    'quantity': 50,
                    't1_quantity': 0,
                    'realised_quantity': 50,
                    'authorised_quantity': 0,
                    'authorised_date': None,
                    'opening_quantity': 50,
                    'collateral_quantity': 0,
                    'collateral_type': '',
                    'discrepancy': False,
                    'average_price': 1450.0,
                    'last_price': 1500.0,
                    'close_price': 1495.0,
                    'pnl': 2500.0,
                    'day_change': 5.0,
                    'day_change_percentage': 0.33
                }
            ]
        """
        try:
            return self.kite.holdings()
        except KiteException as e:
            logger.error(f"Failed to get holdings: {e}")
            raise
    
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
        variety: str = "regular",
        validity: str = "DAY",
        disclosed_quantity: Optional[int] = None,
        tag: Optional[str] = None
    ) -> str:
        """
        Place an order.
        
        Args:
            symbol: Trading symbol (e.g., "RELIANCE")
            exchange: Exchange (NSE, BSE)
            transaction_type: BUY or SELL
            quantity: Order quantity
            order_type: MARKET, LIMIT, SL, SL-M
            product: CNC, MIS, NRML
            price: Limit price (required for LIMIT, SL)
            trigger_price: Trigger price (required for SL, SL-M)
            variety: regular, amo, co, iceberg
            validity: DAY, IOC
            disclosed_quantity: Disclosed quantity for iceberg orders
            tag: Custom order tag (max 20 chars)
        
        Returns:
            Order ID
        """
        try:
            symbol = self.normalize_symbol(symbol, exchange)
            
            order_params = {
                "variety": variety,
                "exchange": exchange,
                "tradingsymbol": symbol,
                "transaction_type": transaction_type,
                "quantity": quantity,
                "product": product,
                "order_type": order_type,
                "validity": validity
            }
            
            # Add optional parameters
            if price is not None:
                order_params["price"] = price
            if trigger_price is not None:
                order_params["trigger_price"] = trigger_price
            if disclosed_quantity is not None:
                order_params["disclosed_quantity"] = disclosed_quantity
            if tag is not None:
                order_params["tag"] = tag[:20]  # Max 20 chars
            
            order_id = self.kite.place_order(**order_params)
            logger.info(f"Placed order {order_id}: {transaction_type} {quantity} {symbol} @ {price or 'MARKET'}")
            return order_id
        except KiteException as e:
            logger.error(f"Failed to place order: {e}")
            raise
    
    def modify_order(
        self,
        order_id: str,
        variety: str = "regular",
        quantity: Optional[int] = None,
        price: Optional[float] = None,
        order_type: Optional[str] = None,
        trigger_price: Optional[float] = None,
        validity: Optional[str] = None,
        disclosed_quantity: Optional[int] = None
    ) -> str:
        """Modify an existing order."""
        try:
            modify_params = {
                "variety": variety,
                "order_id": order_id
            }
            
            if quantity is not None:
                modify_params["quantity"] = quantity
            if price is not None:
                modify_params["price"] = price
            if order_type is not None:
                modify_params["order_type"] = order_type
            if trigger_price is not None:
                modify_params["trigger_price"] = trigger_price
            if validity is not None:
                modify_params["validity"] = validity
            if disclosed_quantity is not None:
                modify_params["disclosed_quantity"] = disclosed_quantity
            
            result_order_id = self.kite.modify_order(**modify_params)
            logger.info(f"Modified order {order_id}")
            return result_order_id
        except KiteException as e:
            logger.error(f"Failed to modify order {order_id}: {e}")
            raise
    
    def cancel_order(self, order_id: str, variety: str = "regular") -> str:
        """Cancel an order."""
        try:
            result_order_id = self.kite.cancel_order(variety=variety, order_id=order_id)
            logger.info(f"Cancelled order {order_id}")
            return result_order_id
        except KiteException as e:
            logger.error(f"Failed to cancel order {order_id}: {e}")
            raise
    
    def get_orders(self) -> List[Dict[str, Any]]:
        """
        Get all orders for the day.
        
        Returns:
            List of orders with status, filled_quantity, pending_quantity, etc.
        """
        try:
            return self.kite.orders()
        except KiteException as e:
            logger.error(f"Failed to get orders: {e}")
            raise
    
    def get_order_history(self, order_id: str) -> List[Dict[str, Any]]:
        """Get order history (state changes)."""
        try:
            return self.kite.order_history(order_id=order_id)
        except KiteException as e:
            logger.error(f"Failed to get order history for {order_id}: {e}")
            raise
    
    def get_trades(self) -> List[Dict[str, Any]]:
        """Get all executed trades for the day."""
        try:
            return self.kite.trades()
        except KiteException as e:
            logger.error(f"Failed to get trades: {e}")
            raise
    
    def get_ltp(self, symbols: List[str], exchange: str = "NSE") -> Dict[str, float]:
        """
        Get last traded price.
        
        Args:
            symbols: List of symbols
            exchange: Exchange name
        
        Returns:
            {'NSE:RELIANCE': 2865.0, 'NSE:INFY': 1500.0}
        """
        try:
            # Format: "EXCHANGE:SYMBOL"
            instruments = [f"{exchange}:{self.normalize_symbol(s, exchange)}" for s in symbols]
            data = self.kite.ltp(instruments)
            
            # Extract LTP
            result = {}
            for instrument, quote in data.items():
                result[instrument] = quote.get("last_price", 0.0)
            
            return result
        except KiteException as e:
            logger.error(f"Failed to get LTP: {e}")
            raise
    
    def get_quote(self, symbols: List[str], exchange: str = "NSE") -> Dict[str, Dict[str, Any]]:
        """
        Get detailed quote.
        
        Returns:
            {
                'NSE:RELIANCE': {
                    'instrument_token': 738561,
                    'timestamp': datetime,
                    'last_price': 2865.0,
                    'last_quantity': 1,
                    'last_trade_time': datetime,
                    'average_price': 2860.0,
                    'volume': 1234567,
                    'buy_quantity': 50000,
                    'sell_quantity': 45000,
                    'ohlc': {
                        'open': 2850.0,
                        'high': 2870.0,
                        'low': 2845.0,
                        'close': 2860.0
                    },
                    'net_change': 5.0,
                    'oi': 0,
                    'oi_day_high': 0,
                    'oi_day_low': 0,
                    'depth': {...}
                }
            }
        """
        try:
            instruments = [f"{exchange}:{self.normalize_symbol(s, exchange)}" for s in symbols]
            return self.kite.quote(instruments)
        except KiteException as e:
            logger.error(f"Failed to get quote: {e}")
            raise
    
    def get_instruments(self, exchange: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get list of tradable instruments.
        
        Args:
            exchange: Filter by exchange (NSE, BSE, NFO, etc.)
        
        Returns:
            List of instruments with token, symbol, name, expiry, strike, etc.
        """
        try:
            return self.kite.instruments(exchange=exchange)
        except KiteException as e:
            logger.error(f"Failed to get instruments: {e}")
            raise
