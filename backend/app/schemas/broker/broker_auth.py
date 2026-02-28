"""Broker authentication schemas."""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class BrokerConnectRequest(BaseModel):
    """Request to connect broker account."""
    
    broker: str = Field(..., description="Broker name (zerodha, upstox, angel_one)")
    request_token: str = Field(..., description="OAuth request token from callback")
    portfolio_id: int = Field(..., description="Portfolio ID to connect")


class BrokerConnectResponse(BaseModel):
    """Response after connecting broker."""
    
    status: str = Field(..., description="Connection status")
    portfolio_id: int = Field(..., description="Portfolio ID")
    broker: str = Field(..., description="Broker name")
    broker_user_id: Optional[str] = Field(None, description="Broker user ID")
    user_name: Optional[str] = Field(None, description="Broker account name")
    available_margin: Optional[float] = Field(None, description="Available margin/cash")
    connected_at: datetime = Field(..., description="Connection timestamp")


class BrokerCallbackRequest(BaseModel):
    """OAuth callback parameters."""
    
    request_token: str = Field(..., description="Request token")
    status: str = Field(..., description="OAuth status (success/error)")


class BrokerDisconnectResponse(BaseModel):
    """Response after disconnecting broker."""
    
    status: str = Field(..., description="Disconnection status")
    portfolio_id: int = Field(..., description="Portfolio ID")
    message: str = Field(..., description="Status message")
