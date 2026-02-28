"""
Performance Dashboard API Endpoints (Layer 6 - Performance Memory)

Endpoints for accessing signal performance analytics, agent metrics,
and self-learning system intelligence.
"""

import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.performance_tracker import PerformanceTrackerService
from app.services.performance_analytics import PerformanceAnalyticsService
from app.services.signal_intelligence import SignalIntelligenceService
from app.services.retraining_service import RetrainingService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/performance", tags=["performance"])


@router.get("/summary")
async def get_performance_summary(
    days: Optional[int] = Query(None, description="Number of days to look back (None = all time)"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get overall system performance summary.
    
    Returns:
        - Total signals
        - Win rate
        - Average PnL%
        - Sharpe ratio
        - Max drawdown
        - Breakdown by outcome
        - Breakdown by signal type
        - Breakdown by regime
    """
    try:
        analytics = PerformanceAnalyticsService(db)
        
        # Get overall metrics
        overall = await analytics.get_overall_metrics(days=days)
        
        # Get breakdowns
        by_signal_type = await analytics.get_performance_by_signal_type(days=days)
        by_regime = await analytics.get_performance_by_regime(days=days)
        
        return {
            "overall": overall,
            "by_signal_type": by_signal_type,
            "by_regime": by_regime,
            "period_days": days
        }
    except Exception as e:
        logger.error(f"Error getting performance summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/signals")
async def get_signal_metrics(
    symbol: Optional[str] = Query(None, description="Filter by symbol"),
    days: Optional[int] = Query(30, description="Number of days to look back"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get signal-level performance metrics.
    
    Returns performance grouped by symbol if no symbol specified,
    or detailed metrics for a specific symbol.
    """
    try:
        analytics = PerformanceAnalyticsService(db)
        
        if symbol:
            # Get specific symbol performance
            intelligence_service = SignalIntelligenceService(db)
            intelligence = await intelligence_service.get_symbol_intelligence(
                symbol=symbol,
                days=days
            )
            return intelligence
        else:
            # Get all symbols performance
            by_symbol = await analytics.get_performance_by_symbol(days=days)
            return {
                "by_symbol": by_symbol,
                "period_days": days
            }
    except Exception as e:
        logger.error(f"Error getting signal metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agents")
async def get_agent_performance(
    days: Optional[int] = Query(30, description="Number of days to look back"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get agent-level accuracy metrics.
    
    Returns:
        - Accuracy for quant agent
        - Accuracy for sentiment agent
        - Accuracy for regime agent
        - Total predictions per agent
    """
    try:
        analytics = PerformanceAnalyticsService(db)
        
        agent_performance = await analytics.analyze_agent_performance(days=days)
        
        return {
            "agents": agent_performance,
            "period_days": days
        }
    except Exception as e:
        logger.error(f"Error getting agent performance: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/regimes")
async def get_regime_performance(
    days: Optional[int] = Query(30, description="Number of days to look back"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get regime-specific win rates and performance.
    
    Returns metrics for each detected market regime.
    """
    try:
        analytics = PerformanceAnalyticsService(db)
        
        by_regime = await analytics.get_performance_by_regime(days=days)
        
        return {
            "by_regime": by_regime,
            "period_days": days
        }
    except Exception as e:
        logger.error(f"Error getting regime performance: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/regimes/{regime}/intelligence")
async def get_regime_intelligence(
    regime: str,
    days: Optional[int] = Query(90, description="Number of days to look back"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get intelligence for a specific market regime.
    
    Returns:
        - Best performing signal types in this regime
        - Top performing symbols in this regime
        - Adaptive thresholds for this regime
    """
    try:
        intelligence_service = SignalIntelligenceService(db)
        
        intelligence = await intelligence_service.get_regime_intelligence(
            regime=regime,
            days=days
        )
        
        return intelligence
    except Exception as e:
        logger.error(f"Error getting regime intelligence: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/symbols/{symbol}")
async def get_symbol_performance(
    symbol: str,
    days: Optional[int] = Query(90, description="Number of days to look back"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get comprehensive performance data for a specific symbol.
    
    Returns:
        - Performance by signal type
        - Performance by regime
        - Performance by confidence level
        - Best performing configuration
        - Recommendations for signal adjustments
    """
    try:
        intelligence_service = SignalIntelligenceService(db)
        
        # Get symbol intelligence
        intelligence = await intelligence_service.get_symbol_intelligence(
            symbol=symbol,
            days=days
        )
        
        # Get recommendations
        recommendations = await intelligence_service.recommend_signal_adjustments(
            symbol=symbol
        )
        
        return {
            "intelligence": intelligence,
            "recommendations": recommendations
        }
    except Exception as e:
        logger.error(f"Error getting symbol performance: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/decay")
async def check_signal_decay(
    symbol: Optional[str] = Query(None, description="Filter by symbol"),
    signal_type: Optional[str] = Query(None, description="Filter by signal type"),
    lookback_days: Optional[int] = Query(30, description="Days to analyze"),
    db: AsyncSession = Depends(get_db)
):
    """
    Check if signal quality is degrading over time.
    
    Returns:
        - Whether signals are decaying
        - Win rate
        - Average PnL
        - Recommendations
    """
    try:
        analytics = PerformanceAnalyticsService(db)
        
        decay_analysis = await analytics.detect_signal_decay(
            symbol=symbol,
            signal_type=signal_type,
            lookback_days=lookback_days
        )
        
        return decay_analysis
    except Exception as e:
        logger.error(f"Error checking signal decay: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trend")
async def get_performance_trend(
    days: Optional[int] = Query(90, description="Total days to analyze"),
    window_days: Optional[int] = Query(30, description="Rolling window size"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get performance trend over time using rolling windows.
    
    Returns list of metrics for each time window.
    """
    try:
        analytics = PerformanceAnalyticsService(db)
        
        trend = await analytics.get_performance_trend(
            days=days,
            window_days=window_days
        )
        
        return {
            "trend": trend,
            "total_days": days,
            "window_days": window_days
        }
    except Exception as e:
        logger.error(f"Error getting performance trend: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/retraining/status")
async def get_retraining_status(
    db: AsyncSession = Depends(get_db)
):
    """
    Get current model retraining status.
    
    Returns:
        - Last training date
        - Last training regime
        - Training samples used
        - New data available
        - Whether ready for retraining
    """
    try:
        retraining_service = RetrainingService(db)
        
        status = await retraining_service.get_training_status()
        
        return status
    except Exception as e:
        logger.error(f"Error getting retraining status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/retraining/check")
async def check_retraining_triggers_endpoint(
    db: AsyncSession = Depends(get_db)
):
    """
    Manually check if retraining triggers are activated.
    
    Returns:
        - Whether retraining is needed
        - List of activated triggers
        - Trigger details
    """
    try:
        retraining_service = RetrainingService(db)
        
        trigger_check = await retraining_service.check_retraining_triggers()
        
        return trigger_check
    except Exception as e:
        logger.error(f"Error checking retraining triggers: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/retraining/trigger")
async def trigger_retraining_endpoint(
    db: AsyncSession = Depends(get_db)
):
    """
    Manually trigger model retraining.
    
    This will check triggers and initiate retraining if needed.
    """
    try:
        retraining_service = RetrainingService(db)
        
        # Check triggers
        trigger_check = await retraining_service.check_retraining_triggers()
        
        if trigger_check["should_retrain"]:
            # Trigger retraining
            result = await retraining_service.trigger_retraining(
                trigger_check["triggers"]
            )
            return result
        else:
            return {
                "status": "no_retraining_needed",
                "trigger_check": trigger_check
            }
    except Exception as e:
        logger.error(f"Error triggering retraining: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/intelligence/agents")
async def get_agent_intelligence(
    days: Optional[int] = Query(90, description="Number of days to look back"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get intelligence on which agents perform best in which conditions.
    
    Returns:
        - Agent accuracy by regime
        - Best regime for each agent
        - Worst regime for each agent
    """
    try:
        intelligence_service = SignalIntelligenceService(db)
        
        intelligence = await intelligence_service.get_agent_intelligence(days=days)
        
        return {
            "agent_intelligence": intelligence,
            "period_days": days
        }
    except Exception as e:
        logger.error(f"Error getting agent intelligence: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/outcomes/compute")
async def compute_pending_outcomes(
    db: AsyncSession = Depends(get_db)
):
    """
    Manually trigger computation of all pending signal outcomes.
    
    This is normally done automatically by scheduled tasks.
    """
    try:
        tracker = PerformanceTrackerService(db)
        
        result = await tracker.compute_all_pending_outcomes()
        
        return result
    except Exception as e:
        logger.error(f"Error computing outcomes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/outcomes/compute/{signal_id}")
async def compute_signal_outcome(
    signal_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Manually compute outcome for a specific signal.
    """
    try:
        tracker = PerformanceTrackerService(db)
        
        performance = await tracker.compute_signal_outcome(signal_id)
        
        if performance:
            return {
                "signal_id": signal_id,
                "outcome": performance.outcome,
                "pnl_percent": performance.pnl_percent,
                "days_held": performance.days_held,
                "status": "success"
            }
        else:
            return {
                "signal_id": signal_id,
                "status": "no_outcome",
                "reason": "Trade not closed or signal not found"
            }
    except Exception as e:
        logger.error(f"Error computing signal outcome: {e}")
        raise HTTPException(status_code=500, detail=str(e))
