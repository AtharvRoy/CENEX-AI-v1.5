"""
Agent API Endpoints
API routes for multi-agent intelligence system.
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from pydantic import BaseModel, Field

from app.core.database import get_db
from app.services.agent_orchestrator import AgentOrchestrator
from app.agents.base_agent import AgentOutput

router = APIRouter(prefix="/api/agents", tags=["agents"])

# Initialize orchestrator
orchestrator = AgentOrchestrator()


# Request/Response Models

class AgentAnalysisRequest(BaseModel):
    """Request schema for agent analysis."""
    symbol: str = Field(..., description="Stock symbol (e.g., RELIANCE.NS)")
    exchange: str = Field(default="NSE", description="Exchange")
    include_sentiment: bool = Field(default=True, description="Include sentiment analysis")
    portfolio_value: float = Field(default=100000.0, description="Portfolio value for risk calculation")
    entry_price: Optional[float] = Field(None, description="Entry price for risk calculation")
    target_price: Optional[float] = Field(None, description="Target price for risk calculation")


class SingleAgentRequest(BaseModel):
    """Request schema for single agent analysis."""
    symbol: str = Field(..., description="Stock symbol")
    exchange: str = Field(default="NSE", description="Exchange")
    portfolio_value: Optional[float] = Field(default=100000.0, description="Portfolio value (risk agent only)")
    entry_price: Optional[float] = Field(None, description="Entry price (risk agent only)")
    target_price: Optional[float] = Field(None, description="Target price (risk agent only)")


class BatchAnalysisRequest(BaseModel):
    """Request schema for batch analysis."""
    symbols: List[str] = Field(..., min_items=1, max_items=50, description="List of stock symbols")
    exchange: str = Field(default="NSE", description="Exchange")
    include_sentiment: bool = Field(default=False, description="Include sentiment (slower for batch)")
    max_concurrent: int = Field(default=5, ge=1, le=10, description="Max concurrent analyses")


# API Endpoints

@router.post("/analyze")
async def analyze_symbol(
    request: AgentAnalysisRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Run all agents on a symbol and return comprehensive analysis.
    
    This endpoint orchestrates all 4 agents (Quant, Sentiment, Regime, Risk)
    and returns their outputs along with feature summaries.
    """
    try:
        result = await orchestrator.analyze_symbol(
            symbol=request.symbol,
            exchange=request.exchange,
            db=db,
            include_sentiment=request.include_sentiment,
            portfolio_value=request.portfolio_value,
            entry_price=request.entry_price,
            target_price=request.target_price
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@router.post("/analyze/batch")
async def analyze_batch(
    request: BatchAnalysisRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Analyze multiple symbols in parallel.
    
    Useful for screening multiple stocks simultaneously.
    Sentiment analysis is disabled by default for performance.
    """
    try:
        result = await orchestrator.analyze_multiple_symbols(
            symbols=request.symbols,
            exchange=request.exchange,
            db=db,
            include_sentiment=request.include_sentiment,
            max_concurrent=request.max_concurrent
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Batch analysis failed: {str(e)}")


@router.get("/{agent_name}/{symbol}")
async def get_single_agent_analysis(
    agent_name: str,
    symbol: str,
    exchange: str = "NSE",
    portfolio_value: float = 100000.0,
    entry_price: Optional[float] = None,
    target_price: Optional[float] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Run a single agent analysis.
    
    Agent names:
    - quant: Quantitative analysis
    - sentiment: Sentiment analysis
    - regime: Market regime strategies
    - risk: Risk assessment
    """
    valid_agents = ["quant", "sentiment", "regime", "risk"]
    if agent_name not in valid_agents:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid agent name. Must be one of: {valid_agents}"
        )
    
    try:
        result = await orchestrator.get_single_agent_analysis(
            agent_name=agent_name,
            symbol=symbol,
            exchange=exchange,
            db=db,
            portfolio_value=portfolio_value,
            entry_price=entry_price,
            target_price=target_price
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent analysis failed: {str(e)}")


@router.get("/info")
async def get_agent_info():
    """
    Get information about all agents.
    
    Returns metadata about each agent including version and model status.
    """
    try:
        info = orchestrator.get_agent_info()
        return {
            "agents": info,
            "orchestrator_version": "1.0",
            "total_agents": len(info)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get agent info: {str(e)}")


@router.post("/admin/retrain")
async def retrain_models(
    background_tasks: BackgroundTasks,
    agent_name: Optional[str] = None
):
    """
    Trigger model retraining (admin only).
    
    Args:
        agent_name: Specific agent to retrain (quant/sentiment), or None for all
    
    Note: This is a placeholder. In production, implement proper admin auth
    and background job queue (Celery).
    """
    # TODO: Add admin authentication
    
    if agent_name and agent_name not in ["quant", "sentiment"]:
        raise HTTPException(
            status_code=400,
            detail="Only 'quant' and 'sentiment' agents support retraining"
        )
    
    # Add training task to background
    def retrain_task():
        import subprocess
        if agent_name == "quant" or agent_name is None:
            subprocess.run(["python", "app/ml/train_quant_agent.py"])
        if agent_name == "sentiment" or agent_name is None:
            subprocess.run(["python", "app/ml/train_sentiment_agent.py"])
    
    background_tasks.add_task(retrain_task)
    
    return {
        "message": "Retraining started",
        "agent": agent_name or "all",
        "status": "background_task_queued"
    }


@router.get("/health")
async def health_check():
    """
    Health check endpoint for agent system.
    """
    try:
        info = orchestrator.get_agent_info()
        return {
            "status": "healthy",
            "agents": info,
            "timestamp": "2026-02-28T14:00:00Z"
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Agent system unhealthy: {str(e)}")
