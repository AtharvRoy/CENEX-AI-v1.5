"""Broker order execution schemas."""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class PlaceOrderRequest(BaseModel):
    """Request to place an order manually."""
    
    portfolio_id: int = Field(..., description="Portfolio ID")
    symbol: str = Field(..., description="Trading symbol")
    exchange: str = Field(default="NSE", description="Exchange (NSE/BSE)")
    transaction_type: str = Field(..., description="BUY or SELL")
    quantity: int = Field(..., gt=0, description="Order quantity")
    order_type: str = Field(default="LIMIT", description="MARKET, LIMIT, SL, SL-M")
    product: str = Field(default="CNC", description="CNC (delivery), MIS (intraday)")
    price: Optional[float] = Field(None, description="Limit price (required for LIMIT)")
    trigger_price: Optional[float] = Field(None, description="Trigger price (for SL orders)")


class PlaceOrderResponse(BaseModel):
    """Response after placing order."""
    
    order_id: str = Field(..., description="Broker order ID")
    trade_id: int = Field(..., description="Internal trade ID")
    status: str = Field(..., description="Order status")
    symbol: str = Field(..., description="Trading symbol")
    transaction_type: str = Field(..., description="BUY/SELL")
    quantity: int = Field(..., description="Order quantity")
    price: Optional[float] = Field(None, description="Order price")
    estimated_cost: float = Field(..., description="Estimated cost/proceeds")


class ExecuteSignalRequest(BaseModel):
    """Request to execute a trading signal."""
    
    portfolio_id: int = Field(..., description="Portfolio ID")
    signal_id: int = Field(..., description="Signal ID to execute")
    quantity: Optional[int] = Field(None, description="Override quantity (auto-calculated if None)")
    product: str = Field(default="CNC", description="CNC (delivery), MIS (intraday)")
    order_type: str = Field(default="LIMIT", description="MARKET or LIMIT")


class ExecuteSignalResponse(BaseModel):
    """Response after executing signal."""
    
    order_id: str = Field(..., description="Broker order ID")
    trade_id: int = Field(..., description="Internal trade ID")
    status: str = Field(..., description="Order status")
    symbol: str = Field(..., description="Trading symbol")
    transaction_type: str = Field(..., description="BUY/SELL")
    quantity: int = Field(..., description="Order quantity")
    price: float = Field(..., description="Order price")
    estimated_cost: float = Field(..., description="Estimated cost/proceeds")
    signal_confidence: float = Field(..., description="Signal confidence score")
    risk_checks_passed: bool = Field(default=True, description="Risk validation status")


class OrderStatusResponse(BaseModel):
    """Order status information."""
    
    order_id: str = Field(..., description="Broker order ID")
    status: str = Field(..., description="Order status")
    tradingsymbol: str = Field(..., description="Trading symbol")
    transaction_type: str = Field(..., description="BUY/SELL")
    order_type: str = Field(..., description="Order type")
    quantity: int = Field(..., description="Total quantity")
    filled_quantity: int = Field(..., description="Filled quantity")
    pending_quantity: int = Field(..., description="Pending quantity")
    price: Optional[float] = Field(None, description="Order price")
    average_price: Optional[float] = Field(None, description="Average fill price")
    order_timestamp: datetime = Field(..., description="Order timestamp")
