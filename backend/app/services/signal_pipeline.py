"""
Signal Generation Pipeline (End-to-End)
Orchestrates Layers 2-5: Features → Agents → Ensemble → Quality Gate
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.feature_pipeline import feature_pipeline
from app.services.meta_decision_engine import meta_decision_engine
from app.services.signal_quality_engine import signal_quality_engine
from app.models.signal import Signal

logger = logging.getLogger(__name__)


class SignalPipeline:
    """
    End-to-end signal generation pipeline.
    
    Pipeline stages:
    1. Feature extraction (Layer 2)
    2. Multi-agent inference (Layer 3)
    3. Meta ensemble (Layer 4)
    4. Quality filtering (Layer 5)
    5. Signal storage
    """
    
    def __init__(self):
        """Initialize Signal Pipeline."""
        self.stats = {
            "total_generated": 0,
            "passed_quality": 0,
            "failed_quality": 0,
            "errors": 0
        }
    
    async def generate_signal(
        self,
        symbol: str,
        exchange: str,
        db: AsyncSession,
        include_sentiment: bool = True,
        save_to_db: bool = True
    ) -> Dict[str, Any]:
        """
        Generate trading signal for a symbol.
        
        Args:
            symbol: Stock symbol
            exchange: Exchange (e.g., "NSE")
            db: Database session
            include_sentiment: Whether to include sentiment analysis
            save_to_db: Whether to save signal to database
        
        Returns:
            Complete signal with reasoning chain
        """
        try:
            start_time = datetime.now()
            
            logger.info(f"Starting signal generation for {symbol}")
            
            # Stage 1: Feature Extraction (Layer 2)
            logger.info(f"[Stage 1/5] Extracting features for {symbol}...")
            features = await feature_pipeline.compute_features(
                symbol=symbol,
                exchange=exchange,
                db=db,
                include_sentiment=include_sentiment
            )
            
            # Stage 2: Multi-Agent Inference (Layer 3)
            logger.info(f"[Stage 2/5] Running multi-agent inference for {symbol}...")
            # NOTE: This will be implemented by the parallel sub-agent (Sprint 04)
            # For now, we'll use mock agent outputs for testing
            agent_outputs = await self._run_agents(symbol, features, db)
            
            # Stage 3: Meta Ensemble (Layer 4)
            logger.info(f"[Stage 3/5] Ensembling agent predictions for {symbol}...")
            meta_signal = meta_decision_engine.ensemble(agent_outputs, features)
            
            # Stage 4: Quality Filtering (Layer 5)
            logger.info(f"[Stage 4/5] Running quality checks for {symbol}...")
            quality_result = await signal_quality_engine.validate(
                signal=meta_signal,
                symbol=symbol,
                features=features,
                db=db
            )
            
            # Stage 5: Signal Storage
            final_signal = quality_result["final_signal"]
            
            if save_to_db and quality_result["passed"]:
                logger.info(f"[Stage 5/5] Saving signal to database for {symbol}...")
                db_signal = await self._save_signal(
                    symbol=symbol,
                    exchange=exchange,
                    signal=final_signal,
                    features=features,
                    agent_outputs=agent_outputs,
                    meta_signal=meta_signal,
                    quality_result=quality_result,
                    db=db
                )
                signal_id = db_signal.id
            else:
                signal_id = None
                logger.info(f"[Stage 5/5] Signal not saved (quality_passed={quality_result['passed']}, save_to_db={save_to_db})")
            
            # Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds()
            
            # Update stats
            self.stats["total_generated"] += 1
            if quality_result["passed"]:
                self.stats["passed_quality"] += 1
            else:
                self.stats["failed_quality"] += 1
            
            # Build complete response
            result = {
                "status": "success",
                "signal_id": signal_id,
                "symbol": symbol,
                "exchange": exchange,
                
                # Final signal
                "signal": final_signal["signal"],
                "confidence": final_signal.get("confidence", 0.0),
                
                # Quality gate result
                "quality_passed": quality_result["passed"],
                "quality_checks": quality_result["checks"],
                
                # Reasoning chain (full transparency)
                "reasoning_chain": {
                    "features": {
                        "regime": features.get("regime", {}),
                        "price": features.get("price", {}),
                        "technical_summary": {
                            "rsi": features.get("technical", {}).get("rsi_14"),
                            "macd": features.get("technical", {}).get("macd"),
                            "atr_pct": features.get("technical", {}).get("atr_pct"),
                            "bb_position": features.get("technical", {}).get("bb_position"),
                        },
                        "sentiment": features.get("sentiment", {})
                    },
                    "agent_outputs": agent_outputs,
                    "meta_ensemble": meta_signal,
                    "quality_checks": quality_result["details"]
                },
                
                # Metadata
                "processing_time_seconds": processing_time,
                "generated_at": datetime.now().isoformat()
            }
            
            logger.info(f"Signal generation complete for {symbol}: {final_signal['signal']} (confidence={final_signal.get('confidence', 0):.2f}, quality_passed={quality_result['passed']})")
            
            return result
        
        except Exception as e:
            logger.error(f"Error generating signal for {symbol}: {e}")
            self.stats["errors"] += 1
            
            return {
                "status": "error",
                "symbol": symbol,
                "exchange": exchange,
                "error": str(e),
                "signal": "ERROR",
                "confidence": 0.0,
                "generated_at": datetime.now().isoformat()
            }
    
    async def _run_agents(
        self,
        symbol: str,
        features: Dict[str, Any],
        db: AsyncSession
    ) -> Dict[str, Dict[str, Any]]:
        """
        Run multi-agent inference (Layer 3).
        
        NOTE: This is a placeholder. The actual implementation will come from
        Sprint 04 (Multi-Agent Intelligence) which is being built in parallel.
        
        For now, we generate mock agent outputs based on features.
        
        Args:
            symbol: Stock symbol
            features: Feature vector
            db: Database session
        
        Returns:
            Agent outputs dictionary
        """
        try:
            # TODO: Replace with actual agent orchestrator when Sprint 04 is complete
            # from app.services.agent_orchestrator import agent_orchestrator
            # return await agent_orchestrator.run_agents(symbol, features)
            
            # Mock implementation for testing
            logger.warning("Using mock agent outputs (Sprint 04 not integrated yet)")
            
            technical = features.get("technical", {})
            regime = features.get("regime", {})
            sentiment = features.get("sentiment", {})
            
            # Generate mock agent outputs based on actual features
            mock_outputs = {
                "quant": self._mock_quant_agent(technical),
                "sentiment": self._mock_sentiment_agent(sentiment),
                "regime": self._mock_regime_agent(regime),
                "risk": self._mock_risk_agent(technical, regime)
            }
            
            return mock_outputs
        
        except Exception as e:
            logger.error(f"Error running agents: {e}")
            # Return neutral signals on error
            return {
                "quant": {"signal": "HOLD", "confidence": 0.5, "reasoning": "Error"},
                "sentiment": {"signal": "HOLD", "confidence": 0.5, "reasoning": "Error"},
                "regime": {"signal": "HOLD", "confidence": 0.5, "reasoning": "Error"},
                "risk": {"signal": "APPROVE", "confidence": 0.5, "reasoning": "Error"}
            }
    
    def _mock_quant_agent(self, technical: Dict[str, Any]) -> Dict[str, Any]:
        """Mock quantitative agent output."""
        rsi = technical.get("rsi_14", 50)
        macd = technical.get("macd", 0)
        bb_position = technical.get("bb_position", 0.5)
        
        # Simple rules
        if rsi < 30 and macd > 0:
            signal = "BUY"
            confidence = 0.75
        elif rsi > 70 and macd < 0:
            signal = "SELL"
            confidence = 0.75
        elif rsi < 40:
            signal = "BUY"
            confidence = 0.60
        elif rsi > 60:
            signal = "SELL"
            confidence = 0.60
        else:
            signal = "HOLD"
            confidence = 0.55
        
        return {
            "signal": signal,
            "confidence": confidence,
            "reasoning": f"RSI={rsi:.1f}, MACD={macd:.3f}, BB_pos={bb_position:.2f}"
        }
    
    def _mock_sentiment_agent(self, sentiment: Dict[str, Any]) -> Dict[str, Any]:
        """Mock sentiment agent output."""
        score = sentiment.get("sentiment_score", 0.0)
        label = sentiment.get("sentiment_label", "neutral")
        
        if label == "bullish":
            signal = "BUY"
            confidence = min(0.5 + abs(score) * 0.3, 0.85)
        elif label == "bearish":
            signal = "SELL"
            confidence = min(0.5 + abs(score) * 0.3, 0.85)
        else:
            signal = "HOLD"
            confidence = 0.60
        
        return {
            "signal": signal,
            "confidence": confidence,
            "reasoning": f"Sentiment: {label} (score={score:.2f})"
        }
    
    def _mock_regime_agent(self, regime: Dict[str, Any]) -> Dict[str, Any]:
        """Mock regime agent output."""
        regime_label = regime.get("regime_label", "ranging")
        trend = regime.get("trend", "ranging")
        
        if "trending_up" in trend:
            signal = "BUY"
            confidence = 0.70
        elif "trending_down" in trend:
            signal = "SELL"
            confidence = 0.70
        else:
            signal = "HOLD"
            confidence = 0.65
        
        return {
            "signal": signal,
            "confidence": confidence,
            "reasoning": f"Regime: {regime_label}, Trend: {trend}"
        }
    
    def _mock_risk_agent(self, technical: Dict[str, Any], regime: Dict[str, Any]) -> Dict[str, Any]:
        """Mock risk agent output."""
        atr_pct = technical.get("atr_pct", 2.0)
        vol_percentile = regime.get("volatility_percentile", 50)
        
        # Reject if high volatility
        if atr_pct > 5.0 or vol_percentile > 90:
            signal = "REJECT"
            confidence = 0.80
            reasoning = f"High volatility (ATR={atr_pct:.2f}%, vol_pct={vol_percentile})"
        else:
            signal = "APPROVE"
            confidence = 0.85
            reasoning = f"Low risk (ATR={atr_pct:.2f}%, vol_pct={vol_percentile})"
        
        return {
            "signal": signal,
            "confidence": confidence,
            "reasoning": reasoning
        }
    
    async def _save_signal(
        self,
        symbol: str,
        exchange: str,
        signal: Dict[str, Any],
        features: Dict[str, Any],
        agent_outputs: Dict[str, Any],
        meta_signal: Dict[str, Any],
        quality_result: Dict[str, Any],
        db: AsyncSession
    ) -> Signal:
        """
        Save signal to database.
        
        Args:
            symbol: Stock symbol
            exchange: Exchange
            signal: Final signal
            features: Feature vector
            agent_outputs: Agent outputs
            meta_signal: Meta ensemble output
            quality_result: Quality check results
            db: Database session
        
        Returns:
            Saved Signal object
        """
        try:
            # Get current price
            price = features.get("price", {}).get("close", 0.0)
            
            # Calculate entry/target/stoploss (simple logic)
            signal_type = signal["signal"]
            if signal_type in ["BUY", "STRONG_BUY"]:
                price_entry = price
                price_target = price * 1.05  # 5% target
                price_stoploss = price * 0.98  # 2% stop
            elif signal_type in ["SELL", "STRONG_SELL"]:
                price_entry = price
                price_target = price * 0.95  # 5% target
                price_stoploss = price * 1.02  # 2% stop
            else:
                price_entry = None
                price_target = None
                price_stoploss = None
            
            # Build reasoning JSON
            reasoning = {
                "agent_outputs": agent_outputs,
                "meta_ensemble": meta_signal,
                "quality_checks": quality_result["checks"],
                "quality_details": quality_result["details"],
                "feature_summary": {
                    "regime": features.get("regime", {}),
                    "sentiment": features.get("sentiment", {}),
                    "technical_indicators": {
                        "rsi": features.get("technical", {}).get("rsi_14"),
                        "macd": features.get("technical", {}).get("macd"),
                        "atr_pct": features.get("technical", {}).get("atr_pct"),
                    }
                }
            }
            
            # Create Signal object
            db_signal = Signal(
                symbol=symbol,
                exchange=exchange,
                signal_type=signal_type,
                confidence=signal.get("confidence", 0.0),
                price_entry=price_entry,
                price_target=price_target,
                price_stoploss=price_stoploss,
                reasoning=reasoning,
                regime=features.get("regime", {}).get("regime_label")
            )
            
            # Add to session and commit
            db.add(db_signal)
            await db.commit()
            await db.refresh(db_signal)
            
            logger.info(f"Signal saved to database: ID={db_signal.id}, {symbol} {signal_type}")
            
            return db_signal
        
        except Exception as e:
            logger.error(f"Error saving signal to database: {e}")
            await db.rollback()
            raise
    
    async def generate_batch(
        self,
        symbols: list[str],
        exchange: str,
        db: AsyncSession,
        include_sentiment: bool = False  # Disable by default for batch (slower)
    ) -> Dict[str, Any]:
        """
        Generate signals for multiple symbols in batch.
        
        Args:
            symbols: List of symbols
            exchange: Exchange
            db: Database session
            include_sentiment: Whether to include sentiment analysis
        
        Returns:
            Batch results
        """
        results = {}
        
        for symbol in symbols:
            try:
                result = await self.generate_signal(
                    symbol=symbol,
                    exchange=exchange,
                    db=db,
                    include_sentiment=include_sentiment
                )
                results[symbol] = result
            except Exception as e:
                logger.error(f"Error generating signal for {symbol}: {e}")
                results[symbol] = {
                    "status": "error",
                    "error": str(e)
                }
        
        return results
    
    def get_stats(self) -> Dict[str, Any]:
        """Get pipeline statistics."""
        total = self.stats["total_generated"]
        if total > 0:
            quality_pass_rate = self.stats["passed_quality"] / total
        else:
            quality_pass_rate = 0.0
        
        return {
            **self.stats,
            "quality_pass_rate": quality_pass_rate
        }
    
    def reset_stats(self):
        """Reset pipeline statistics."""
        self.stats = {
            "total_generated": 0,
            "passed_quality": 0,
            "failed_quality": 0,
            "errors": 0
        }


# Singleton instance
signal_pipeline = SignalPipeline()
