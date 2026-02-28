"""
Celery tasks for Performance Memory (Layer 6 - Self-Learning Loop).

Scheduled tasks:
- Daily: Update signal performance outcomes
- Daily: Mark expired signals
- Weekly: Check retraining triggers
- On-demand: Trigger model retraining
"""

import logging
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.core.celery_app import celery_app
from app.core.config import settings
from app.services.performance_tracker import PerformanceTrackerService
from app.services.performance_analytics import PerformanceAnalyticsService
from app.services.retraining_service import RetrainingService

logger = logging.getLogger(__name__)

# Create async engine for tasks
engine = create_async_engine(settings.DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@celery_app.task(name='app.tasks.performance_tasks.update_signal_performance', bind=True)
def update_signal_performance(self):
    """
    Scheduled task: Update signal performance for all closed trades.
    Runs daily at 5:00 PM IST (after market close).
    """
    async def _update():
        async with AsyncSessionLocal() as session:
            tracker = PerformanceTrackerService(session)
            
            # Compute outcomes for all pending signals
            result = await tracker.compute_all_pending_outcomes()
            
            # Mark expired signals (no trade after 30 days)
            expired_count = await tracker.mark_expired_signals(days_threshold=30)
            
            logger.info(
                f"Performance update completed: "
                f"{result['computed']} outcomes computed, "
                f"{expired_count} signals marked as expired"
            )
            
            return {
                "processed": result["processed"],
                "computed": result["computed"],
                "expired": expired_count,
                "status": "success"
            }
    
    # Run async function
    loop = asyncio.get_event_loop()
    if loop.is_running():
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(asyncio.run, _update())
            result = future.result()
    else:
        result = asyncio.run(_update())
    
    return result


@celery_app.task(name='app.tasks.performance_tasks.check_retraining_triggers', bind=True)
def check_retraining_triggers(self):
    """
    Scheduled task: Check if models need retraining.
    Runs weekly on Sunday at 6:00 PM IST.
    """
    async def _check():
        async with AsyncSessionLocal() as session:
            retraining_service = RetrainingService(session)
            
            # Check all triggers
            trigger_check = await retraining_service.check_retraining_triggers()
            
            # If retraining needed, trigger it
            if trigger_check["should_retrain"]:
                logger.warning("Retraining triggers detected, initiating retraining")
                
                retraining_result = await retraining_service.trigger_retraining(
                    trigger_check["triggers"]
                )
                
                return {
                    "trigger_check": trigger_check,
                    "retraining": retraining_result,
                    "status": "retraining_triggered"
                }
            else:
                logger.info("No retraining needed")
                
                return {
                    "trigger_check": trigger_check,
                    "status": "no_retraining_needed"
                }
    
    loop = asyncio.get_event_loop()
    if loop.is_running():
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(asyncio.run, _check())
            result = future.result()
    else:
        result = asyncio.run(_check())
    
    return result


@celery_app.task(name='app.tasks.performance_tasks.generate_performance_report', bind=True)
def generate_performance_report(self):
    """
    Scheduled task: Generate daily performance report.
    Runs daily at 6:00 PM IST.
    """
    async def _report():
        async with AsyncSessionLocal() as session:
            analytics = PerformanceAnalyticsService(session)
            
            # Get overall metrics (last 30 days)
            overall = await analytics.get_overall_metrics(days=30)
            
            # Get performance by signal type
            by_signal_type = await analytics.get_performance_by_signal_type(days=30)
            
            # Get performance by regime
            by_regime = await analytics.get_performance_by_regime(days=30)
            
            # Get agent performance
            agent_performance = await analytics.analyze_agent_performance(days=30)
            
            # Detect signal decay
            decay_check = await analytics.detect_signal_decay(lookback_days=30)
            
            report = {
                "generated_at": asyncio.get_event_loop().time(),
                "period": "last_30_days",
                "overall_metrics": overall,
                "by_signal_type": by_signal_type,
                "by_regime": by_regime,
                "agent_performance": agent_performance,
                "signal_decay": decay_check,
                "status": "success"
            }
            
            logger.info(
                f"Performance report generated: "
                f"Win rate: {overall['win_rate']:.2%}, "
                f"Avg PnL: {overall['avg_pnl_percent']:.2f}%, "
                f"Total signals: {overall['total_signals']}"
            )
            
            return report
    
    loop = asyncio.get_event_loop()
    if loop.is_running():
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(asyncio.run, _report())
            result = future.result()
    else:
        result = asyncio.run(_report())
    
    return result


@celery_app.task(name='app.tasks.performance_tasks.retrain_models', bind=True)
def retrain_models(self, model_names: list = None):
    """
    On-demand task: Retrain specified models.
    
    Args:
        model_names: List of model names to retrain (default: all)
    """
    async def _retrain():
        async with AsyncSessionLocal() as session:
            # This would integrate with actual ML training pipeline
            # For now, we'll simulate the process
            
            if model_names is None:
                models = ["quant_agent", "sentiment_agent", "meta_learner"]
            else:
                models = model_names
            
            logger.info(f"Retraining models: {models}")
            
            # In production, this would:
            # 1. Extract features from historical data
            # 2. Train new models
            # 3. Validate on holdout set
            # 4. Run A/B test
            # 5. Deploy if better than old models
            
            return {
                "models_retrained": models,
                "status": "simulated",
                "note": "ML training pipeline to be implemented",
                "timestamp": asyncio.get_event_loop().time()
            }
    
    loop = asyncio.get_event_loop()
    if loop.is_running():
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(asyncio.run, _retrain())
            result = future.result()
    else:
        result = asyncio.run(_retrain())
    
    return result


@celery_app.task(name='app.tasks.performance_tasks.compute_single_outcome', bind=True)
def compute_single_outcome(self, signal_id: int):
    """
    On-demand task: Compute outcome for a single signal.
    
    Args:
        signal_id: Signal ID to compute outcome for
    """
    async def _compute():
        async with AsyncSessionLocal() as session:
            tracker = PerformanceTrackerService(session)
            
            performance = await tracker.compute_signal_outcome(signal_id)
            
            if performance:
                return {
                    "signal_id": signal_id,
                    "outcome": performance.outcome,
                    "pnl_percent": performance.pnl_percent,
                    "status": "success"
                }
            else:
                return {
                    "signal_id": signal_id,
                    "status": "no_outcome",
                    "reason": "Trade not closed or signal not found"
                }
    
    loop = asyncio.get_event_loop()
    if loop.is_running():
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(asyncio.run, _compute())
            result = future.result()
    else:
        result = asyncio.run(_compute())
    
    return result
