"""
API endpoints for feature engineering (Layer 2).
Provides technical indicators, regime detection, sentiment analysis, and complete feature vectors.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from datetime import datetime
import logging

from app.core.database import get_db
from app.services.feature_pipeline import feature_pipeline
from app.services.indicators import technical_indicators
from app.services.regime import regime_detection
from app.services.sentiment import sentiment_analysis
from app.schemas.features import (
    FeatureVector,
    IndicatorsResponse,
    RegimeResponse,
    SentimentResponse,
    SupportResistance,
    BatchFeaturesRequest,
    BatchFeaturesResponse,
    RegimeStatsResponse,
    HMMTrainingRequest,
    HMMTrainingResponse
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["features"])


@router.get("/features/{symbol}", response_model=FeatureVector)
async def get_features(
    symbol: str,
    exchange: str = Query(default="NSE", description="Exchange (NSE, BSE)"),
    use_cache: bool = Query(default=True, description="Use cached features if available"),
    include_sentiment: bool = Query(default=True, description="Include sentiment analysis"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get complete feature vector for a symbol.
    
    This endpoint computes:
    - Technical indicators (60+ features)
    - Market regime classification
    - Sentiment analysis (optional)
    - Flat feature array for ML models (80-100 dimensions)
    
    Features are cached for 5 minutes for performance.
    """
    try:
        features = await feature_pipeline.compute_features(
            symbol=symbol,
            exchange=exchange,
            db=db,
            use_cache=use_cache,
            include_sentiment=include_sentiment
        )
        return features
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error computing features for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"Error computing features: {str(e)}")


@router.post("/features/batch", response_model=BatchFeaturesResponse)
async def batch_features(
    request: BatchFeaturesRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Compute features for multiple symbols in batch.
    
    Maximum 50 symbols per request.
    Sentiment analysis can be enabled but will increase computation time.
    """
    try:
        results = await feature_pipeline.batch_compute(
            symbols=request.symbols,
            exchange=request.exchange,
            db=db,
            include_sentiment=request.include_sentiment
        )
        
        return {
            "results": results,
            "computed_at": datetime.now().isoformat(),
            "count": len(results)
        }
    except Exception as e:
        logger.error(f"Error in batch feature computation: {e}")
        raise HTTPException(status_code=500, detail=f"Error computing batch features: {str(e)}")


@router.get("/indicators/{symbol}", response_model=IndicatorsResponse)
async def get_indicators(
    symbol: str,
    exchange: str = Query(default="NSE"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get technical indicators only (without regime or sentiment).
    
    Returns:
    - Momentum indicators (RSI, Stochastic, ROC, Williams %R, CCI)
    - Trend indicators (MACD, ADX, Aroon, SAR, Moving Averages)
    - Volatility indicators (Bollinger Bands, ATR, Keltner Channels)
    - Volume indicators (OBV, AD Line, CMF, MFI, VWAP)
    """
    try:
        # Fetch OHLCV data
        from datetime import timedelta
        df = await feature_pipeline._fetch_ohlcv(symbol, exchange, db, lookback_days=200)
        
        if df.empty:
            raise HTTPException(status_code=404, detail=f"No data found for {symbol}")
        
        # Compute indicators
        indicators = technical_indicators.compute_all(df)
        
        return {
            "symbol": symbol,
            "timestamp": datetime.now().isoformat(),
            "indicators": indicators
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error computing indicators for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"Error computing indicators: {str(e)}")


@router.get("/indicators/{symbol}/support-resistance", response_model=SupportResistance)
async def get_support_resistance(
    symbol: str,
    exchange: str = Query(default="NSE"),
    window: int = Query(default=20, ge=10, le=50, description="Lookback window for pivot detection"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get support and resistance levels based on pivot points.
    """
    try:
        # Fetch OHLCV data
        df = await feature_pipeline._fetch_ohlcv(symbol, exchange, db, lookback_days=200)
        
        if df.empty:
            raise HTTPException(status_code=404, detail=f"No data found for {symbol}")
        
        # Compute support/resistance
        levels = technical_indicators.compute_support_resistance(df, window=window)
        
        return levels
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error computing support/resistance for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/regime/{symbol}", response_model=RegimeResponse)
async def get_regime(
    symbol: str,
    exchange: str = Query(default="NSE"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get market regime classification for a symbol.
    
    Returns:
    - Volatility regime (low_vol, medium_vol, high_vol)
    - Trend regime (trending_up, trending_down, trending, ranging)
    - Combined regime (e.g., "low_vol_trending")
    - Confidence score (0-1)
    - HMM state (if model is trained)
    """
    try:
        # Fetch OHLCV data
        df = await feature_pipeline._fetch_ohlcv(symbol, exchange, db, lookback_days=200)
        
        if df.empty:
            raise HTTPException(status_code=404, detail=f"No data found for {symbol}")
        
        # Detect regime
        regime = regime_detection.detect_regime(df)
        
        return {
            "symbol": symbol,
            "timestamp": datetime.now().isoformat(),
            "regime": regime
        }
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error detecting regime for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"Error detecting regime: {str(e)}")


@router.post("/regime/{symbol}/train-hmm", response_model=HMMTrainingResponse)
async def train_hmm(
    symbol: str,
    request: HMMTrainingRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Train Hidden Markov Model for regime classification.
    
    Requires at least 500 data points (approximately 2 years of daily data).
    The model will classify the market into n_states regimes (default 3: bull, bear, sideways).
    """
    try:
        # Fetch OHLCV data (need more history for HMM)
        df = await feature_pipeline._fetch_ohlcv(symbol, request.exchange, db, lookback_days=1000)
        
        if df.empty:
            raise HTTPException(status_code=404, detail=f"No data found for {symbol}")
        
        if len(df) < 500:
            raise HTTPException(
                status_code=400, 
                detail=f"Insufficient data for HMM training: {len(df)} bars (need at least 500)"
            )
        
        # Train HMM
        training_result = regime_detection.train_hmm(df, n_states=request.n_states)
        
        return {
            "symbol": symbol,
            **training_result,
            "computed_at": datetime.now().isoformat()
        }
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error training HMM for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"Error training HMM: {str(e)}")


@router.get("/sentiment/{symbol}", response_model=SentimentResponse)
async def get_sentiment(
    symbol: str,
    hours: int = Query(default=48, ge=6, le=168, description="Hours to look back for news"),
):
    """
    Get sentiment analysis for a symbol based on recent news.
    
    Analyzes news headlines from:
    - MoneyControl
    - Economic Times
    - Business Standard
    
    Uses FinBERT (Financial BERT) for sentiment classification.
    Returns sentiment score from -1 (bearish) to +1 (bullish).
    """
    try:
        # Load sentiment model if not already loaded
        if not sentiment_analysis.model_loaded:
            sentiment_analysis.load_model()
        
        # Analyze sentiment
        sentiment = sentiment_analysis.analyze_sentiment(symbol, hours=hours)
        
        return {
            "symbol": symbol,
            "timestamp": datetime.now().isoformat(),
            "sentiment": sentiment
        }
    except Exception as e:
        logger.error(f"Error analyzing sentiment for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=f"Error analyzing sentiment: {str(e)}")


@router.delete("/cache")
async def clear_cache(
    symbol: Optional[str] = Query(default=None, description="Specific symbol to clear (or all if not provided)")
):
    """
    Clear feature cache.
    
    Use this endpoint to force recomputation of features.
    """
    try:
        feature_pipeline.clear_cache(symbol=symbol)
        sentiment_analysis.clear_cache()
        
        return {
            "status": "success",
            "message": f"Cache cleared for {symbol if symbol else 'all symbols'}",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        raise HTTPException(status_code=500, detail=f"Error clearing cache: {str(e)}")


@router.get("/health")
async def health_check():
    """
    Health check endpoint for feature services.
    """
    return {
        "status": "healthy",
        "services": {
            "indicators": "ok",
            "regime": "ok",
            "sentiment": "loaded" if sentiment_analysis.model_loaded else "not_loaded",
            "pipeline": "ok"
        },
        "timestamp": datetime.now().isoformat()
    }
