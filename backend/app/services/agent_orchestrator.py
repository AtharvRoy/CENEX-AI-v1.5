"""
Agent Orchestrator Service
Coordinates all agents and aggregates their outputs.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents import QuantAgent, SentimentAgent, RegimeAgent, RiskAgent
from app.agents.base_agent import AgentOutput
from app.services.feature_pipeline import FeaturePipeline

logger = logging.getLogger(__name__)


class AgentOrchestrator:
    """
    Orchestrates all market analysis agents.
    
    Runs agents in parallel and aggregates their outputs.
    """
    
    def __init__(self):
        """Initialize the orchestrator with all agents."""
        self.quant_agent = QuantAgent()
        self.sentiment_agent = SentimentAgent()
        self.regime_agent = RegimeAgent()
        self.risk_agent = RiskAgent()
        
        self.feature_pipeline = FeaturePipeline()
        
        logger.info("Agent orchestrator initialized with 4 agents")
    
    async def analyze_symbol(
        self,
        symbol: str,
        exchange: str,
        db: AsyncSession,
        include_sentiment: bool = True,
        portfolio_value: float = 100000.0,
        entry_price: Optional[float] = None,
        target_price: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Run all agents on a symbol and return aggregated analysis.
        
        Args:
            symbol: Stock symbol
            exchange: Exchange (e.g., "NSE")
            db: Database session
            include_sentiment: Whether to include sentiment analysis
            portfolio_value: Portfolio value for risk calculation
            entry_price: Entry price for risk calculation
            target_price: Target price for risk calculation
        
        Returns:
            Dictionary with all agent outputs
        """
        try:
            # Step 1: Compute features
            logger.info(f"Computing features for {symbol}")
            features = await self.feature_pipeline.compute_features(
                symbol=symbol,
                exchange=exchange,
                db=db,
                include_sentiment=include_sentiment
            )
            
            # Step 2: Run all analysis agents in parallel
            logger.info(f"Running analysis agents for {symbol}")
            agent_tasks = [
                self.quant_agent.analyze(symbol, features),
                self.sentiment_agent.analyze(symbol, features) if include_sentiment else self._skip_sentiment(symbol),
                self.regime_agent.analyze(symbol, features),
            ]
            
            analysis_results = await asyncio.gather(*agent_tasks, return_exceptions=True)
            
            quant_output, sentiment_output, regime_output = analysis_results
            
            # Handle exceptions
            quant_output = self._handle_exception(quant_output, "quant", symbol)
            sentiment_output = self._handle_exception(sentiment_output, "sentiment", symbol)
            regime_output = self._handle_exception(regime_output, "regime", symbol)
            
            # Step 3: Run risk agent separately (needs price info)
            logger.info(f"Running risk agent for {symbol}")
            risk_output = await self.risk_agent.analyze(
                symbol=symbol,
                features=features,
                entry_price=entry_price,
                target_price=target_price,
                portfolio_value=portfolio_value
            )
            
            # Step 4: Aggregate outputs
            result = {
                "symbol": symbol,
                "exchange": exchange,
                "timestamp": datetime.now().isoformat(),
                "agents": {
                    "quant": quant_output.dict() if quant_output else None,
                    "sentiment": sentiment_output.dict() if sentiment_output else None,
                    "regime": regime_output.dict() if regime_output else None,
                    "risk": risk_output.dict() if risk_output else None,
                },
                "features_summary": {
                    "price": features.get("price"),
                    "regime": features.get("regime", {}).get("combined"),
                    "sentiment_score": features.get("sentiment", {}).get("sentiment_score") if include_sentiment else None,
                },
                "execution_time_ms": self._calculate_execution_time(),
            }
            
            logger.info(f"Agent orchestration completed for {symbol}")
            return result
        
        except Exception as e:
            logger.error(f"Error in agent orchestration for {symbol}: {e}")
            raise
    
    async def analyze_multiple_symbols(
        self,
        symbols: List[str],
        exchange: str,
        db: AsyncSession,
        include_sentiment: bool = False,  # Default False for batch to reduce load
        max_concurrent: int = 5
    ) -> Dict[str, Any]:
        """
        Analyze multiple symbols in parallel with concurrency limit.
        
        Args:
            symbols: List of stock symbols
            exchange: Exchange
            db: Database session
            include_sentiment: Whether to include sentiment
            max_concurrent: Maximum concurrent analyses
        
        Returns:
            Dictionary with results for each symbol
        """
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def analyze_with_semaphore(symbol: str):
            async with semaphore:
                try:
                    return await self.analyze_symbol(
                        symbol=symbol,
                        exchange=exchange,
                        db=db,
                        include_sentiment=include_sentiment
                    )
                except Exception as e:
                    logger.error(f"Error analyzing {symbol}: {e}")
                    return {
                        "symbol": symbol,
                        "error": str(e),
                        "timestamp": datetime.now().isoformat()
                    }
        
        tasks = [analyze_with_semaphore(symbol) for symbol in symbols]
        results = await asyncio.gather(*tasks)
        
        return {
            "symbols": symbols,
            "count": len(symbols),
            "results": {res["symbol"]: res for res in results},
            "timestamp": datetime.now().isoformat()
        }
    
    async def get_single_agent_analysis(
        self,
        agent_name: str,
        symbol: str,
        exchange: str,
        db: AsyncSession,
        **kwargs
    ) -> AgentOutput:
        """
        Run a single agent analysis.
        
        Args:
            agent_name: Name of agent ("quant", "sentiment", "regime", "risk")
            symbol: Stock symbol
            exchange: Exchange
            db: Database session
            **kwargs: Additional agent-specific parameters
        
        Returns:
            AgentOutput from specified agent
        """
        # Compute features
        include_sentiment = agent_name == "sentiment"
        features = await self.feature_pipeline.compute_features(
            symbol=symbol,
            exchange=exchange,
            db=db,
            include_sentiment=include_sentiment
        )
        
        # Route to appropriate agent
        if agent_name == "quant":
            return await self.quant_agent.analyze(symbol, features)
        elif agent_name == "sentiment":
            return await self.sentiment_agent.analyze(symbol, features)
        elif agent_name == "regime":
            return await self.regime_agent.analyze(symbol, features)
        elif agent_name == "risk":
            portfolio_value = kwargs.get("portfolio_value", 100000.0)
            entry_price = kwargs.get("entry_price")
            target_price = kwargs.get("target_price")
            return await self.risk_agent.analyze(
                symbol=symbol,
                features=features,
                portfolio_value=portfolio_value,
                entry_price=entry_price,
                target_price=target_price
            )
        else:
            raise ValueError(f"Unknown agent: {agent_name}")
    
    def get_agent_info(self) -> Dict[str, Any]:
        """
        Get information about all agents.
        
        Returns:
            Dictionary with agent metadata
        """
        return {
            "quant": self.quant_agent.get_info(),
            "sentiment": self.sentiment_agent.get_info(),
            "regime": self.regime_agent.get_info(),
            "risk": self.risk_agent.get_info(),
        }
    
    async def _skip_sentiment(self, symbol: str) -> AgentOutput:
        """
        Create a skip output for sentiment when not requested.
        
        Args:
            symbol: Stock symbol
        
        Returns:
            AgentOutput with NO_SIGNAL
        """
        from app.agents.base_agent import SignalType
        return AgentOutput(
            agent_name="sentiment",
            symbol=symbol,
            signal=SignalType.NO_SIGNAL,
            confidence=0.0,
            reasoning={"reason": "Sentiment analysis not requested"}
        )
    
    def _handle_exception(
        self, 
        result: Any, 
        agent_name: str, 
        symbol: str
    ) -> Optional[AgentOutput]:
        """
        Handle exceptions from agent execution.
        
        Args:
            result: Result or exception from agent
            agent_name: Name of agent
            symbol: Stock symbol
        
        Returns:
            AgentOutput or None
        """
        if isinstance(result, Exception):
            logger.error(f"Exception in {agent_name} agent for {symbol}: {result}")
            from app.agents.base_agent import SignalType
            return AgentOutput(
                agent_name=agent_name,
                symbol=symbol,
                signal=SignalType.NO_SIGNAL,
                confidence=0.0,
                reasoning={"error": str(result)}
            )
        return result
    
    def _calculate_execution_time(self) -> int:
        """
        Calculate execution time (placeholder).
        
        Returns:
            Execution time in milliseconds
        """
        # In production, track actual execution time
        return 0
