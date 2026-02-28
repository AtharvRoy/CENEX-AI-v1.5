"""
Base Agent Class
Standard interface for all market analysis agents.
"""

from abc import ABC, abstractmethod
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
from datetime import datetime
from enum import Enum


class SignalType(str, Enum):
    """Standard signal types."""
    STRONG_BUY = "STRONG_BUY"
    BUY = "BUY"
    HOLD = "HOLD"
    SELL = "SELL"
    STRONG_SELL = "STRONG_SELL"
    NO_SIGNAL = "NO_SIGNAL"
    APPROVE = "APPROVE"  # For risk agent
    REJECT = "REJECT"    # For risk agent


class AgentOutput(BaseModel):
    """Standard output schema for all agents."""
    agent_name: str = Field(..., description="Name of the agent (quant, sentiment, regime, risk)")
    symbol: str = Field(..., description="Stock symbol")
    signal: SignalType = Field(..., description="Trading signal")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score (0.0 to 1.0)")
    reasoning: Dict[str, Any] = Field(default_factory=dict, description="Agent-specific reasoning and context")
    timestamp: datetime = Field(default_factory=datetime.now, description="Timestamp of analysis")
    
    class Config:
        json_schema_extra = {
            "example": {
                "agent_name": "quant",
                "symbol": "RELIANCE.NS",
                "signal": "BUY",
                "confidence": 0.78,
                "reasoning": {
                    "top_features": ["rsi_14", "macd", "adx_14"],
                    "feature_importance": {
                        "rsi_14": 0.35,
                        "macd": 0.28,
                        "adx_14": 0.22
                    },
                    "model_version": "v1.0"
                },
                "timestamp": "2026-02-28T14:35:00Z"
            }
        }


class BaseAgent(ABC):
    """Abstract base class for all market analysis agents."""
    
    def __init__(self, name: str, version: str = "1.0"):
        """
        Initialize the agent.
        
        Args:
            name: Name of the agent
            version: Version string
        """
        self.name = name
        self.version = version
        self._model = None
    
    @abstractmethod
    async def analyze(
        self, 
        symbol: str, 
        features: Dict[str, Any],
        **kwargs
    ) -> AgentOutput:
        """
        Analyze market data and generate signal.
        
        Args:
            symbol: Stock symbol
            features: Feature vector from feature pipeline
            **kwargs: Additional agent-specific parameters
        
        Returns:
            AgentOutput with signal, confidence, and reasoning
        """
        pass
    
    @abstractmethod
    def load_model(self, model_path: Optional[str] = None) -> None:
        """
        Load trained model (if applicable).
        
        Args:
            model_path: Path to model file
        """
        pass
    
    def _validate_features(self, features: Dict[str, Any], required_keys: list) -> bool:
        """
        Validate that required feature keys are present.
        
        Args:
            features: Feature dictionary
            required_keys: List of required keys
        
        Returns:
            True if all keys present, False otherwise
        """
        for key in required_keys:
            if key not in features:
                return False
        return True
    
    def get_info(self) -> Dict[str, Any]:
        """
        Get agent information.
        
        Returns:
            Agent metadata
        """
        return {
            "name": self.name,
            "version": self.version,
            "model_loaded": self._model is not None
        }
