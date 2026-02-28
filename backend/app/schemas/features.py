"""
Pydantic schemas for feature engineering endpoints.
"""

from pydantic import BaseModel, Field
from typing import Dict, List, Any, Optional
from datetime import datetime


class PriceData(BaseModel):
    """Price data schema."""
    open: float
    high: float
    low: float
    close: float
    volume: int
    change_pct: float


class RegimeData(BaseModel):
    """Market regime data schema."""
    volatility: str
    volatility_percentile: float
    trend: str
    trend_strength: float
    combined: str
    confidence: float
    hmm_state: Optional[int] = None
    hmm_regime: Optional[str] = None


class SentimentData(BaseModel):
    """Sentiment analysis data schema."""
    sentiment_score: float
    sentiment_label: str
    news_count: int
    analyzed_count: Optional[int] = None
    freshness_hours: Optional[int] = None
    error: Optional[str] = None


class HeadlineData(BaseModel):
    """News headline data schema."""
    title: str
    sentiment: float
    label: str
    confidence: float
    published: str
    link: str


class SentimentDetailData(SentimentData):
    """Detailed sentiment data with headlines."""
    headlines: List[HeadlineData] = []


class FeatureMetadata(BaseModel):
    """Feature computation metadata."""
    data_points: int
    lookback_days: int
    computed_at: str


class FeatureVector(BaseModel):
    """Complete feature vector response."""
    symbol: str
    exchange: str
    timestamp: str
    data_timestamp: str
    price: PriceData
    technical: Dict[str, Any]
    regime: RegimeData
    sentiment: SentimentData
    feature_array: List[float]
    feature_count: int
    metadata: FeatureMetadata


class IndicatorsResponse(BaseModel):
    """Technical indicators response."""
    symbol: str
    timestamp: str
    indicators: Dict[str, Any]


class RegimeResponse(BaseModel):
    """Regime classification response."""
    symbol: str
    timestamp: str
    regime: RegimeData


class SentimentResponse(BaseModel):
    """Sentiment analysis response."""
    symbol: str
    timestamp: str
    sentiment: SentimentDetailData


class SupportResistance(BaseModel):
    """Support and resistance levels."""
    support: List[float]
    resistance: List[float]
    current_price: float


class BatchFeaturesRequest(BaseModel):
    """Request schema for batch feature computation."""
    symbols: List[str] = Field(..., min_items=1, max_items=50)
    exchange: str = "NSE"
    include_sentiment: bool = False


class BatchFeaturesResponse(BaseModel):
    """Response schema for batch feature computation."""
    results: Dict[str, FeatureVector]
    computed_at: str
    count: int


class RegimeStatsResponse(BaseModel):
    """Regime statistics response."""
    symbol: str
    regime_stats: Dict[str, Dict[str, Any]]
    computed_at: str


class HMMTrainingRequest(BaseModel):
    """Request schema for HMM training."""
    symbol: str
    exchange: str = "NSE"
    n_states: int = Field(default=3, ge=2, le=5)


class HMMTrainingResponse(BaseModel):
    """Response schema for HMM training."""
    symbol: str
    n_states: int
    trained: bool
    data_points: int
    state_stats: Dict[str, Dict[str, Any]]
    aic: float
    bic: float
    computed_at: str
