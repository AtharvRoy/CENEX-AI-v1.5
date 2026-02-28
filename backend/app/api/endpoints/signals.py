"""
Signals endpoints - AI-powered trading signal generation.
Implements Meta Decision Engine + Signal Quality Engine (Layers 4 & 5).
"""

from fastapi import APIRouter, Depends, Query, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional, Dict, Any
from app.core.database import get_db
from app.models import User, Signal
from app.schemas import SignalResponse, SignalList
from app.api.dependencies import get_current_user
from app.services.signal_pipeline import signal_pipeline
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/signals", tags=["Signals"])


@router.get("/", response_model=SignalList)
async def list_signals(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    symbol: str = Query(None, description="Filter by symbol"),
    signal_type: str = Query(None, description="Filter by signal type"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List trading signals (paginated).
    
    **Status**: Stub endpoint - returns empty list for now.
    **Coming in Sprint 02**: Real signal generation from AI agents.
    
    Filters:
    - **symbol**: Filter by stock symbol (e.g., RELIANCE)
    - **signal_type**: Filter by type (STRONG_BUY, BUY, etc.)
    - **page**: Page number (default: 1)
    - **page_size**: Items per page (default: 20, max: 100)
    """
    # Build query
    query = select(Signal)
    
    if symbol:
        query = query.where(Signal.symbol == symbol.upper())
    
    if signal_type:
        query = query.where(Signal.signal_type == signal_type.upper())
    
    query = query.order_by(Signal.created_at.desc())
    
    # Get total count
    count_query = select(func.count()).select_from(Signal)
    if symbol:
        count_query = count_query.where(Signal.symbol == symbol.upper())
    if signal_type:
        count_query = count_query.where(Signal.signal_type == signal_type.upper())
    
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Paginate
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)
    
    result = await db.execute(query)
    signals = result.scalars().all()
    
    return SignalList(
        signals=signals,
        total=total,
        page=page,
        page_size=page_size
    )


@router.get("/{signal_id}", response_model=SignalResponse)
async def get_signal(
    signal_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get a specific signal by ID.
    
    Returns complete signal details including:
    - Signal type and confidence
    - All agent outputs
    - Meta-ensemble decision
    - Quality gate results
    - Feature summary
    """
    result = await db.execute(select(Signal).where(Signal.id == signal_id))
    signal = result.scalar_one_or_none()
    
    if not signal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Signal not found"
        )
    
    return signal


@router.post("/generate/{symbol}")
async def generate_signal(
    symbol: str,
    exchange: str = Query("NSE", description="Exchange (e.g., NSE, BSE)"),
    include_sentiment: bool = Query(True, description="Include sentiment analysis (slower)"),
    save_to_db: bool = Query(True, description="Save signal to database"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Generate a new trading signal for a symbol.
    
    **Pipeline Stages:**
    1. **Feature Extraction (Layer 2)** - Technical indicators, regime detection, sentiment
    2. **Multi-Agent Inference (Layer 3)** - Quant, Sentiment, Regime, Risk agents
    3. **Meta Ensemble (Layer 4)** - Combine agent predictions with logistic regression
    4. **Quality Gate (Layer 5)** - Filter through confidence, volatility, decay, liquidity checks
    5. **Signal Storage** - Save to database if quality gate passes
    
    **Quality Gates:**
    - Confidence threshold (regime-aware)
    - Volatility anomaly detection
    - Signal decay analysis
    - Liquidity check
    - Risk score validation
    
    **Returns:**
    - Final signal (STRONG_BUY, BUY, HOLD, SELL, STRONG_SELL, NO_SIGNAL)
    - Confidence score (0-1)
    - Quality gate results
    - Complete reasoning chain (all agent outputs + ensemble decision)
    
    **Example:**
    ```
    POST /api/signals/generate/RELIANCE?exchange=NSE&include_sentiment=true
    ```
    """
    try:
        logger.info(f"Generating signal for {symbol} ({exchange})")
        
        result = await signal_pipeline.generate_signal(
            symbol=symbol.upper(),
            exchange=exchange.upper(),
            db=db,
            include_sentiment=include_sentiment,
            save_to_db=save_to_db
        )
        
        return result
    
    except Exception as e:
        logger.error(f"Error generating signal for {symbol}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating signal: {str(e)}"
        )


@router.post("/generate/batch")
async def generate_signals_batch(
    symbols: list[str],
    exchange: str = Query("NSE", description="Exchange"),
    include_sentiment: bool = Query(False, description="Include sentiment (slower for batch)"),
    background_tasks: BackgroundTasks = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Generate signals for multiple symbols in batch.
    
    **Note:** Sentiment analysis is disabled by default for batch operations (performance).
    
    **Example:**
    ```json
    POST /api/signals/generate/batch
    {
        "symbols": ["RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK"]
    }
    ```
    """
    try:
        logger.info(f"Generating batch signals for {len(symbols)} symbols")
        
        results = await signal_pipeline.generate_batch(
            symbols=[s.upper() for s in symbols],
            exchange=exchange.upper(),
            db=db,
            include_sentiment=include_sentiment
        )
        
        return {
            "status": "success",
            "total_symbols": len(symbols),
            "results": results
        }
    
    except Exception as e:
        logger.error(f"Error in batch signal generation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating batch signals: {str(e)}"
        )


@router.get("/latest")
async def get_latest_signals(
    limit: int = Query(10, ge=1, le=100, description="Number of signals to return"),
    min_confidence: float = Query(0.0, ge=0.0, le=1.0, description="Minimum confidence"),
    signal_type: Optional[str] = Query(None, description="Filter by signal type"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get latest high-quality trading signals (all symbols).
    
    **Filters:**
    - **limit**: Number of signals (default: 10, max: 100)
    - **min_confidence**: Minimum confidence score (0-1)
    - **signal_type**: Filter by type (STRONG_BUY, BUY, SELL, STRONG_SELL)
    
    **Example:**
    ```
    GET /api/signals/latest?limit=20&min_confidence=0.75&signal_type=BUY
    ```
    """
    try:
        query = select(Signal).order_by(Signal.created_at.desc())
        
        # Apply filters
        if min_confidence > 0:
            query = query.where(Signal.confidence >= min_confidence)
        
        if signal_type:
            query = query.where(Signal.signal_type == signal_type.upper())
        
        # Exclude NO_SIGNAL
        query = query.where(Signal.signal_type != "NO_SIGNAL")
        
        query = query.limit(limit)
        
        result = await db.execute(query)
        signals = result.scalars().all()
        
        return {
            "status": "success",
            "count": len(signals),
            "signals": [
                {
                    "id": sig.id,
                    "symbol": sig.symbol,
                    "signal_type": sig.signal_type,
                    "confidence": sig.confidence,
                    "price_entry": sig.price_entry,
                    "price_target": sig.price_target,
                    "price_stoploss": sig.price_stoploss,
                    "regime": sig.regime,
                    "created_at": sig.created_at.isoformat()
                }
                for sig in signals
            ]
        }
    
    except Exception as e:
        logger.error(f"Error fetching latest signals: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching signals: {str(e)}"
        )


@router.get("/{symbol}/history")
async def get_signal_history(
    symbol: str,
    limit: int = Query(50, ge=1, le=500, description="Number of historical signals"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get signal history for a specific symbol.
    
    **Example:**
    ```
    GET /api/signals/RELIANCE/history?limit=100
    ```
    """
    try:
        query = select(Signal).where(
            Signal.symbol == symbol.upper()
        ).order_by(Signal.created_at.desc()).limit(limit)
        
        result = await db.execute(query)
        signals = result.scalars().all()
        
        return {
            "status": "success",
            "symbol": symbol.upper(),
            "count": len(signals),
            "signals": [
                {
                    "id": sig.id,
                    "signal_type": sig.signal_type,
                    "confidence": sig.confidence,
                    "price_entry": sig.price_entry,
                    "regime": sig.regime,
                    "created_at": sig.created_at.isoformat()
                }
                for sig in signals
            ]
        }
    
    except Exception as e:
        logger.error(f"Error fetching signal history for {symbol}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching signal history: {str(e)}"
        )


@router.get("/stats/pipeline")
async def get_pipeline_stats(
    current_user: User = Depends(get_current_user)
):
    """
    Get signal pipeline statistics.
    
    Returns metrics on:
    - Total signals generated
    - Quality gate pass rate
    - Error rate
    """
    try:
        stats = signal_pipeline.get_stats()
        
        return {
            "status": "success",
            "stats": stats
        }
    
    except Exception as e:
        logger.error(f"Error fetching pipeline stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching stats: {str(e)}"
        )
