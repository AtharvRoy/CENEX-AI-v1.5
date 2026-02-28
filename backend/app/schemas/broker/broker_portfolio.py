"""Broker portfolio sync schemas."""

from pydantic import BaseModel, Field
from typing import List, Dict, Any
from datetime import datetime


class PositionResponse(BaseModel):
    """Position data."""
    
    tradingsymbol: str = Field(..., description="Trading symbol")
    exchange: str = Field(..., description="Exchange")
    product: str = Field(..., description="Product type")
    quantity: int = Field(..., description="Net quantity")
    average_price: float = Field(..., description="Average price")
    last_price: float = Field(..., description="Last traded price")
    pnl: float = Field(..., description="Profit/Loss")
    value: float = Field(..., description="Position value")


class HoldingResponse(BaseModel):
    """Holding data."""
    
    tradingsymbol: str = Field(..., description="Trading symbol")
    exchange: str = Field(..., description="Exchange")
    quantity: int = Field(..., description="Quantity")
    average_price: float = Field(..., description="Average price")
    last_price: float = Field(..., description="Last traded price")
    pnl: float = Field(..., description="Profit/Loss")
    day_change: float = Field(..., description="Day change")
    day_change_percentage: float = Field(..., description="Day change %")


class MarginResponse(BaseModel):
    """Margin/funds data."""
    
    available_cash: float = Field(..., description="Available cash")
    used_margin: float = Field(..., description="Used margin")
    net: float = Field(..., description="Net available")


class PortfolioSyncResponse(BaseModel):
    """Full portfolio sync response."""
    
    positions: List[PositionResponse] = Field(default_factory=list, description="Current positions")
    holdings: List[HoldingResponse] = Field(default_factory=list, description="Long-term holdings")
    margin: MarginResponse = Field(..., description="Margin/funds")
    total_position_pnl: float = Field(..., description="Total position P&L")
    total_holding_pnl: float = Field(..., description="Total holding P&L")
    total_portfolio_value: float = Field(..., description="Total portfolio value")
    synced_at: datetime = Field(..., description="Sync timestamp")
