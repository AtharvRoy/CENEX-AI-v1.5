"""
Feature Pipeline Service
Orchestrates the feature computation process: fetch OHLCV → compute indicators → detect regime → fetch sentiment.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
import logging
import json

from app.models.market_data import MarketData
from app.services.indicators import technical_indicators
from app.services.regime import regime_detection
from app.services.sentiment import sentiment_analysis

logger = logging.getLogger(__name__)


class FeaturePipeline:
    """Service for computing complete feature vectors for symbols."""
    
    def __init__(self):
        """Initialize the feature pipeline."""
        self._cache = {}  # Simple in-memory cache (should use Redis in production)
        self.cache_ttl = 300  # 5 minutes in seconds
    
    async def compute_features(
        self, 
        symbol: str, 
        exchange: str,
        db: AsyncSession,
        use_cache: bool = True,
        include_sentiment: bool = True
    ) -> Dict[str, Any]:
        """
        Compute complete feature vector for a symbol.
        
        Args:
            symbol: Stock symbol (e.g., "RELIANCE.NS")
            exchange: Exchange (e.g., "NSE")
            db: Database session
            use_cache: Whether to use cached features
            include_sentiment: Whether to include sentiment analysis
        
        Returns:
            Complete feature vector dictionary
        """
        cache_key = f"{symbol}:{exchange}"
        
        # Check cache
        if use_cache and cache_key in self._cache:
            cached_data, cached_time = self._cache[cache_key]
            if (datetime.now() - cached_time).total_seconds() < self.cache_ttl:
                logger.info(f"Returning cached features for {symbol}")
                return cached_data
        
        try:
            # Step 1: Fetch OHLCV data from database
            logger.info(f"Fetching OHLCV data for {symbol}")
            df = await self._fetch_ohlcv(symbol, exchange, db, lookback_days=200)
            
            if df.empty:
                raise ValueError(f"No market data found for {symbol}")
            
            # Step 2: Compute technical indicators
            logger.info(f"Computing technical indicators for {symbol}")
            indicators = technical_indicators.compute_all(df)
            
            # Step 3: Detect market regime
            logger.info(f"Detecting market regime for {symbol}")
            regime = regime_detection.detect_regime(df)
            
            # Step 4: Fetch sentiment (optional)
            sentiment = None
            if include_sentiment:
                try:
                    logger.info(f"Analyzing sentiment for {symbol}")
                    sentiment = sentiment_analysis.analyze_sentiment(symbol, hours=48)
                except Exception as e:
                    logger.error(f"Error analyzing sentiment for {symbol}: {e}")
                    sentiment = {
                        "symbol": symbol,
                        "sentiment_score": 0.0,
                        "sentiment_label": "neutral",
                        "news_count": 0,
                        "error": str(e)
                    }
            
            # Step 5: Assemble feature vector
            feature_vector = self._assemble_feature_vector(
                symbol=symbol,
                exchange=exchange,
                df=df,
                indicators=indicators,
                regime=regime,
                sentiment=sentiment
            )
            
            # Cache the result
            self._cache[cache_key] = (feature_vector, datetime.now())
            
            logger.info(f"Feature computation complete for {symbol}: {len(feature_vector.get('feature_array', []))} features")
            
            return feature_vector
        
        except Exception as e:
            logger.error(f"Error computing features for {symbol}: {e}")
            raise
    
    async def _fetch_ohlcv(
        self, 
        symbol: str, 
        exchange: str, 
        db: AsyncSession, 
        lookback_days: int = 200
    ) -> pd.DataFrame:
        """
        Fetch OHLCV data from TimescaleDB.
        
        Args:
            symbol: Stock symbol
            exchange: Exchange
            db: Database session
            lookback_days: Number of days to look back
        
        Returns:
            DataFrame with OHLCV data
        """
        cutoff_date = datetime.now() - timedelta(days=lookback_days)
        
        # Query market data
        query = select(MarketData).where(
            MarketData.symbol == symbol,
            MarketData.exchange == exchange,
            MarketData.time >= cutoff_date
        ).order_by(MarketData.time)
        
        result = await db.execute(query)
        rows = result.scalars().all()
        
        if not rows:
            return pd.DataFrame()
        
        # Convert to DataFrame
        data = []
        for row in rows:
            data.append({
                'time': row.time,
                'open': row.open,
                'high': row.high,
                'low': row.low,
                'close': row.close,
                'volume': row.volume
            })
        
        df = pd.DataFrame(data)
        df.set_index('time', inplace=True)
        
        return df
    
    def _assemble_feature_vector(
        self,
        symbol: str,
        exchange: str,
        df: pd.DataFrame,
        indicators: Dict[str, Any],
        regime: Dict[str, Any],
        sentiment: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Assemble complete feature vector from all components.
        
        Args:
            symbol: Stock symbol
            exchange: Exchange
            df: OHLCV DataFrame
            indicators: Technical indicators
            regime: Regime detection results
            sentiment: Sentiment analysis results
        
        Returns:
            Complete feature vector
        """
        # Get latest price data
        latest = df.iloc[-1]
        
        # Build feature vector
        feature_vector = {
            "symbol": symbol,
            "exchange": exchange,
            "timestamp": datetime.now().isoformat(),
            "data_timestamp": str(latest.name),  # Last data point timestamp
            
            # Price information
            "price": {
                "open": float(latest['open']),
                "high": float(latest['high']),
                "low": float(latest['low']),
                "close": float(latest['close']),
                "volume": int(latest['volume']),
                "change_pct": indicators.get('price_change_pct', 0.0)
            },
            
            # Technical indicators (grouped)
            "technical": indicators,
            
            # Regime classification
            "regime": regime,
            
            # Sentiment (if available)
            "sentiment": sentiment if sentiment else {
                "sentiment_score": 0.0,
                "sentiment_label": "neutral",
                "news_count": 0
            },
            
            # Metadata
            "metadata": {
                "data_points": len(df),
                "lookback_days": (df.index[-1] - df.index[0]).days,
                "computed_at": datetime.now().isoformat()
            }
        }
        
        # Create flat feature array (for ML models)
        feature_array = self._create_feature_array(indicators, regime, sentiment)
        feature_vector["feature_array"] = feature_array
        feature_vector["feature_count"] = len(feature_array)
        
        return feature_vector
    
    def _create_feature_array(
        self,
        indicators: Dict[str, Any],
        regime: Dict[str, Any],
        sentiment: Optional[Dict[str, Any]]
    ) -> list:
        """
        Create flat feature array for ML models.
        
        Args:
            indicators: Technical indicators
            regime: Regime detection results
            sentiment: Sentiment analysis results
        
        Returns:
            List of feature values
        """
        features = []
        
        # Technical indicators (approximately 60-70 features)
        indicator_keys = [
            # Price
            'price_change_pct',
            
            # Momentum (7 features)
            'rsi_14', 'stoch_k', 'stoch_d', 'roc_10', 'willr_14', 'cci_14', 'mfi_14',
            
            # Trend (18 features)
            'macd', 'macd_signal', 'macd_hist',
            'adx_14', 'plus_di', 'minus_di',
            'aroon_up', 'aroon_down',
            'sar', 'sar_signal',
            'sma_20', 'sma_50', 'ema_12', 'ema_26',
            'price_vs_sma20', 'price_vs_sma50',
            
            # Volatility (11 features)
            'bb_upper', 'bb_middle', 'bb_lower', 'bb_width', 'bb_position',
            'atr_14', 'atr_pct',
            'keltner_upper', 'keltner_lower',
            'hist_vol_20d',
            
            # Volume (10 features)
            'obv', 'obv_change', 'ad_line', 'cmf',
            'vwap_20', 'price_vs_vwap',
            'volume', 'volume_sma_20', 'volume_ratio',
        ]
        
        for key in indicator_keys:
            value = indicators.get(key, 0.0)
            # Handle non-numeric values
            if isinstance(value, (int, float)):
                features.append(float(value))
            else:
                features.append(0.0)
        
        # Regime features (encoded as binary flags - 9 features)
        regime_vol = regime.get('volatility', 'medium_vol')
        features.append(1.0 if regime_vol == 'low_vol' else 0.0)
        features.append(1.0 if regime_vol == 'medium_vol' else 0.0)
        features.append(1.0 if regime_vol == 'high_vol' else 0.0)
        
        regime_trend = regime.get('trend', 'ranging')
        features.append(1.0 if regime_trend == 'trending_up' else 0.0)
        features.append(1.0 if regime_trend == 'trending_down' else 0.0)
        features.append(1.0 if regime_trend == 'trending' else 0.0)
        features.append(1.0 if regime_trend == 'ranging' else 0.0)
        
        # Regime confidence and strength
        features.append(regime.get('confidence', 0.5))
        features.append(regime.get('volatility_percentile', 0.5))
        features.append(regime.get('trend_strength', 25.0) / 50.0)  # Normalize ADX
        
        # Sentiment features (3 features)
        if sentiment:
            features.append(sentiment.get('sentiment_score', 0.0))
            features.append(1.0 if sentiment.get('sentiment_label') == 'bullish' else 0.0)
            features.append(1.0 if sentiment.get('sentiment_label') == 'bearish' else 0.0)
        else:
            features.extend([0.0, 0.0, 0.0])
        
        return features
    
    async def batch_compute(
        self,
        symbols: list[str],
        exchange: str,
        db: AsyncSession,
        include_sentiment: bool = False
    ) -> Dict[str, Dict[str, Any]]:
        """
        Compute features for multiple symbols in batch.
        
        Args:
            symbols: List of stock symbols
            exchange: Exchange
            db: Database session
            include_sentiment: Whether to include sentiment analysis
        
        Returns:
            Dictionary mapping symbols to feature vectors
        """
        results = {}
        
        for symbol in symbols:
            try:
                features = await self.compute_features(
                    symbol=symbol,
                    exchange=exchange,
                    db=db,
                    include_sentiment=include_sentiment
                )
                results[symbol] = features
            except Exception as e:
                logger.error(f"Error computing features for {symbol}: {e}")
                results[symbol] = {
                    "symbol": symbol,
                    "error": str(e)
                }
        
        return results
    
    def clear_cache(self, symbol: Optional[str] = None):
        """
        Clear feature cache.
        
        Args:
            symbol: Specific symbol to clear (if None, clears all)
        """
        if symbol:
            # Clear specific symbol
            keys_to_remove = [k for k in self._cache.keys() if k.startswith(symbol)]
            for key in keys_to_remove:
                del self._cache[key]
        else:
            # Clear all
            self._cache.clear()


# Singleton instance
feature_pipeline = FeaturePipeline()
