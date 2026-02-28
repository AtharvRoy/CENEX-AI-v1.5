"""
Pydantic schemas for Signal API requests and responses.
"""

from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class SignalBase(BaseModel):
    """Base signal schema."""
    symbol: str = Field(..., description="Stock symbol (e.g., RELIANCE)")
    exchange: str = Field(..., description="Exchange (NSE, BSE)")
    signal_type: str = Field(..., description="STRONG_BUY, BUY, HOLD, SELL, STRONG_SELL, NO_SIGNAL")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score (0-1)")
    regime: Optional[str] = Field(None, description="Market regime (high_vol, low_vol, trending, ranging)")


class SignalCreate(SignalBase):
    """Schema for creating a new signal."""
    price_entry: Optional[float] = None
    price_target: Optional[float] = None
    price_stoploss: Optional[float] = None
    reasoning: Optional[Dict[str, Any]] = None


class SignalResponse(SignalBase):
    """Schema for signal response."""
    id: int
    price_entry: Optional[float]
    price_target: Optional[float]
    price_stoploss: Optional[float]
    reasoning: Optional[Dict[str, Any]]
    created_at: datetime
    
    class Config:
        from_attributes = True


class SignalList(BaseModel):
    """Schema for paginated signal list."""
    signals: list[SignalResponse]
    total: int
    page: int
    page_size: int
