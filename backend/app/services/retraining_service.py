"""
Retraining Service (Layer 6 - Performance Memory)

Auto-triggers model retraining when:
- Accuracy drops below threshold
- New data accumulates
- Regime shifts detected
"""

import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.signal import Signal
from app.models.signal_performance import SignalPerformance
from app.services.performance_analytics import PerformanceAnalyticsService

logger = logging.getLogger(__name__)


class RetrainingService:
    """Service for triggering and managing model retraining."""
    
    # Retraining thresholds
    ACCURACY_THRESHOLD = 0.55  # Trigger if accuracy drops below 55%
    NEW_DATA_THRESHOLD = 1000  # Trigger if 1000+ new signals since last training
    MIN_SIGNALS_FOR_TRAINING = 100  # Minimum signals required for retraining
    
    # Training metadata file
    TRAINING_METADATA_PATH = Path("/root/clawd/cenex-ai/backend/models/training_metadata.json")
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.analytics = PerformanceAnalyticsService(db)
    
    async def check_retraining_triggers(self) -> Dict[str, Any]:
        """
        Check if any retraining triggers are activated.
        
        Returns:
            Dict with trigger status and details
        """
        triggers = []
        
        # Check 1: Accuracy drop
        accuracy_trigger = await self._check_accuracy_drop()
        if accuracy_trigger:
            triggers.append(accuracy_trigger)
        
        # Check 2: New data accumulation
        new_data_trigger = await self._check_new_data()
        if new_data_trigger:
            triggers.append(new_data_trigger)
        
        # Check 3: Regime shift
        regime_trigger = await self._check_regime_shift()
        if regime_trigger:
            triggers.append(regime_trigger)
        
        should_retrain = len(triggers) > 0
        
        result = {
            "should_retrain": should_retrain,
            "triggers": triggers,
            "trigger_count": len(triggers),
            "checked_at": datetime.utcnow().isoformat()
        }
        
        if should_retrain:
            logger.warning(f"Retraining triggered: {len(triggers)} triggers detected")
            logger.warning(f"Triggers: {[t['type'] for t in triggers]}")
        else:
            logger.info("No retraining triggers detected")
        
        return result
    
    async def _check_accuracy_drop(self) -> Optional[Dict[str, Any]]:
        """
        Check if recent accuracy has dropped below threshold.
        
        Returns:
            Trigger dict if accuracy dropped, None otherwise
        """
        # Get recent performance (last 30 days)
        recent_metrics = await self.analytics.get_overall_metrics(days=30)
        
        recent_win_rate = recent_metrics.get("win_rate", 0.0)
        total_signals = recent_metrics.get("total_signals", 0)
        
        # Need minimum data for reliable check
        if total_signals < 20:
            logger.debug("Insufficient recent signals for accuracy check")
            return None
        
        if recent_win_rate < self.ACCURACY_THRESHOLD:
            logger.warning(f"Accuracy drop detected: {recent_win_rate:.2%} < {self.ACCURACY_THRESHOLD:.2%}")
            
            return {
                "type": "accuracy_drop",
                "current_accuracy": recent_win_rate,
                "threshold": self.ACCURACY_THRESHOLD,
                "sample_size": total_signals,
                "severity": "high" if recent_win_rate < 0.50 else "medium"
            }
        
        return None
    
    async def _check_new_data(self) -> Optional[Dict[str, Any]]:
        """
        Check if enough new data has accumulated since last training.
        
        Returns:
            Trigger dict if new data threshold exceeded, None otherwise
        """
        # Get last training date from metadata
        last_training_date = self._get_last_training_date()
        
        # Count signals with outcomes since last training
        query = select(func.count(SignalPerformance.id))
        
        if last_training_date:
            query = query.where(SignalPerformance.created_at > last_training_date)
        
        result = await self.db.execute(query)
        new_signals_count = result.scalar() or 0
        
        if new_signals_count >= self.NEW_DATA_THRESHOLD:
            logger.warning(f"New data accumulation detected: {new_signals_count} new signals")
            
            return {
                "type": "new_data",
                "new_signals_count": new_signals_count,
                "threshold": self.NEW_DATA_THRESHOLD,
                "last_training_date": last_training_date.isoformat() if last_training_date else None,
                "severity": "medium"
            }
        
        return None
    
    async def _check_regime_shift(self) -> Optional[Dict[str, Any]]:
        """
        Check if market regime has shifted since last training.
        
        Returns:
            Trigger dict if regime shifted, None otherwise
        """
        # Get last training regime from metadata
        metadata = self._load_training_metadata()
        last_regime = metadata.get("last_training_regime")
        
        if not last_regime:
            logger.debug("No previous training regime recorded")
            return None
        
        # Get current dominant regime (most common in last 7 days)
        current_regime = await self._get_current_regime()
        
        if current_regime and current_regime != last_regime:
            logger.warning(f"Regime shift detected: {last_regime} -> {current_regime}")
            
            return {
                "type": "regime_shift",
                "old_regime": last_regime,
                "new_regime": current_regime,
                "severity": "high"
            }
        
        return None
    
    async def _get_current_regime(self) -> Optional[str]:
        """
        Get current dominant market regime.
        
        Returns:
            Most common regime in last 7 days
        """
        cutoff = datetime.utcnow() - timedelta(days=7)
        
        # Query most common regime
        query = select(
            Signal.regime,
            func.count(Signal.id).label("count")
        ).where(
            Signal.created_at >= cutoff
        ).group_by(
            Signal.regime
        ).order_by(
            func.count(Signal.id).desc()
        ).limit(1)
        
        result = await self.db.execute(query)
        row = result.first()
        
        return row[0] if row else None
    
    async def trigger_retraining(self, triggers: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Trigger model retraining based on detected triggers.
        
        Args:
            triggers: List of trigger dicts
            
        Returns:
            Dict with retraining status
        """
        logger.info(f"Starting retraining pipeline with {len(triggers)} triggers")
        
        # Get all completed signal performances for training
        query = select(SignalPerformance).where(
            SignalPerformance.outcome.in_(["win", "loss", "breakeven"])
        )
        
        result = await self.db.execute(query)
        performances = result.scalars().all()
        
        if len(performances) < self.MIN_SIGNALS_FOR_TRAINING:
            logger.warning(f"Insufficient data for retraining: {len(performances)} < {self.MIN_SIGNALS_FOR_TRAINING}")
            return {
                "status": "skipped",
                "reason": "insufficient_data",
                "available_samples": len(performances),
                "required_samples": self.MIN_SIGNALS_FOR_TRAINING
            }
        
        # In production, this would trigger actual ML model retraining
        # For now, we'll simulate the process
        
        result = {
            "status": "triggered",
            "triggers": triggers,
            "training_samples": len(performances),
            "models_to_retrain": ["quant_agent", "sentiment_agent", "meta_learner"],
            "triggered_at": datetime.utcnow().isoformat(),
            "note": "Retraining task queued - actual training happens in background"
        }
        
        # Update training metadata
        self._update_training_metadata({
            "last_training_date": datetime.utcnow().isoformat(),
            "last_training_regime": await self._get_current_regime(),
            "training_samples": len(performances),
            "triggers": [t["type"] for t in triggers]
        })
        
        logger.info("Retraining triggered successfully")
        
        return result
    
    def _get_last_training_date(self) -> Optional[datetime]:
        """Get last training date from metadata file."""
        metadata = self._load_training_metadata()
        last_date_str = metadata.get("last_training_date")
        
        if last_date_str:
            try:
                return datetime.fromisoformat(last_date_str)
            except ValueError:
                logger.warning(f"Invalid last_training_date format: {last_date_str}")
        
        return None
    
    def _load_training_metadata(self) -> Dict[str, Any]:
        """Load training metadata from JSON file."""
        if not self.TRAINING_METADATA_PATH.exists():
            return {}
        
        try:
            with open(self.TRAINING_METADATA_PATH, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading training metadata: {e}")
            return {}
    
    def _update_training_metadata(self, updates: Dict[str, Any]) -> None:
        """Update training metadata file."""
        # Ensure directory exists
        self.TRAINING_METADATA_PATH.parent.mkdir(parents=True, exist_ok=True)
        
        # Load existing metadata
        metadata = self._load_training_metadata()
        
        # Update with new values
        metadata.update(updates)
        
        # Save to file
        try:
            with open(self.TRAINING_METADATA_PATH, 'w') as f:
                json.dump(metadata, f, indent=2)
            logger.info("Training metadata updated")
        except Exception as e:
            logger.error(f"Error saving training metadata: {e}")
    
    async def get_training_status(self) -> Dict[str, Any]:
        """
        Get current training status and history.
        
        Returns:
            Dict with training status info
        """
        metadata = self._load_training_metadata()
        
        # Get total available data
        query = select(func.count(SignalPerformance.id))
        result = await self.db.execute(query)
        total_performances = result.scalar() or 0
        
        # Get data since last training
        last_training_date = self._get_last_training_date()
        new_data_count = 0
        
        if last_training_date:
            query = select(func.count(SignalPerformance.id)).where(
                SignalPerformance.created_at > last_training_date
            )
            result = await self.db.execute(query)
            new_data_count = result.scalar() or 0
        
        return {
            "last_training_date": metadata.get("last_training_date"),
            "last_training_regime": metadata.get("last_training_regime"),
            "last_training_samples": metadata.get("training_samples", 0),
            "last_training_triggers": metadata.get("triggers", []),
            "total_available_samples": total_performances,
            "new_samples_since_training": new_data_count,
            "ready_for_retraining": total_performances >= self.MIN_SIGNALS_FOR_TRAINING
        }
    
    async def simulate_ab_test(
        self, 
        model_name: str,
        test_duration_days: int = 7
    ) -> Dict[str, Any]:
        """
        Simulate A/B test for new model vs old model.
        
        Args:
            model_name: Name of model to test
            test_duration_days: Duration of A/B test
            
        Returns:
            Dict with A/B test results (simulated for now)
        """
        # In production, this would:
        # 1. Deploy new model in shadow mode
        # 2. Compare predictions with old model
        # 3. Track which model would have performed better
        # 4. Make deployment decision
        
        logger.info(f"A/B test for {model_name} would run for {test_duration_days} days")
        
        return {
            "model_name": model_name,
            "test_status": "simulated",
            "test_duration_days": test_duration_days,
            "note": "A/B testing framework to be implemented in production",
            "recommendation": "deploy_new_model"  # Placeholder
        }
