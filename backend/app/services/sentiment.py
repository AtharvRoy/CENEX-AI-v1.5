"""
Sentiment Analysis Service
Scrapes financial news and performs sentiment analysis using FinBERT.
"""

import feedparser
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import logging
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch
import re
import hashlib

logger = logging.getLogger(__name__)


class SentimentAnalysis:
    """Service for sentiment analysis of financial news."""
    
    def __init__(self):
        """Initialize the sentiment analysis service."""
        self.model = None
        self.tokenizer = None
        self.model_loaded = False
        self._cache = {}  # Simple in-memory cache for headlines
        
        # RSS feed sources for Indian markets
        self.rss_feeds = [
            "https://www.moneycontrol.com/rss/latestnews.xml",
            "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",
            "https://www.business-standard.com/rss/markets-106.rss",
        ]
    
    def load_model(self):
        """Load FinBERT model for sentiment analysis."""
        if self.model_loaded:
            return
        
        try:
            logger.info("Loading FinBERT model...")
            self.tokenizer = AutoTokenizer.from_pretrained("ProsusAI/finbert")
            self.model = AutoModelForSequenceClassification.from_pretrained("ProsusAI/finbert")
            self.model.eval()  # Set to evaluation mode
            self.model_loaded = True
            logger.info("FinBERT model loaded successfully")
        except Exception as e:
            logger.error(f"Error loading FinBERT model: {e}")
            raise
    
    def analyze_sentiment(self, symbol: str, hours: int = 48) -> Dict[str, Any]:
        """
        Analyze sentiment for a given symbol based on recent news.
        
        Args:
            symbol: Stock symbol (e.g., "RELIANCE", "TCS")
            hours: Number of hours to look back for news
        
        Returns:
            Dictionary with sentiment score and metadata
        """
        # Ensure model is loaded
        if not self.model_loaded:
            self.load_model()
        
        # Extract company name from symbol (remove .NS suffix if present)
        company_name = symbol.replace(".NS", "").replace(".BO", "")
        
        # Fetch news headlines
        headlines = self.fetch_news(company_name, hours=hours)
        
        if not headlines:
            return {
                "symbol": symbol,
                "sentiment_score": 0.0,
                "sentiment_label": "neutral",
                "news_count": 0,
                "freshness_hours": hours,
                "headlines": [],
                "error": "No news found"
            }
        
        # Analyze sentiment of headlines
        sentiment_scores = []
        analyzed_headlines = []
        
        for headline in headlines:
            try:
                score, label, confidence = self._analyze_text(headline['title'])
                sentiment_scores.append(score)
                analyzed_headlines.append({
                    "title": headline['title'],
                    "sentiment": score,
                    "label": label,
                    "confidence": confidence,
                    "published": headline.get('published', ''),
                    "link": headline.get('link', '')
                })
            except Exception as e:
                logger.error(f"Error analyzing headline: {e}")
                continue
        
        # Calculate overall sentiment
        if sentiment_scores:
            avg_sentiment = sum(sentiment_scores) / len(sentiment_scores)
            sentiment_label = self._get_sentiment_label(avg_sentiment)
        else:
            avg_sentiment = 0.0
            sentiment_label = "neutral"
        
        return {
            "symbol": symbol,
            "sentiment_score": float(avg_sentiment),
            "sentiment_label": sentiment_label,
            "news_count": len(headlines),
            "analyzed_count": len(sentiment_scores),
            "freshness_hours": hours,
            "headlines": analyzed_headlines[:10]  # Return top 10 for brevity
        }
    
    def _analyze_text(self, text: str) -> tuple[float, str, float]:
        """
        Analyze sentiment of a single text using FinBERT.
        
        Args:
            text: Text to analyze
        
        Returns:
            Tuple of (sentiment_score, label, confidence)
        """
        # Check cache
        text_hash = hashlib.md5(text.encode()).hexdigest()
        if text_hash in self._cache:
            return self._cache[text_hash]
        
        # Tokenize and analyze
        inputs = self.tokenizer(text, return_tensors="pt", truncation=True, max_length=512, padding=True)
        
        with torch.no_grad():
            outputs = self.model(**inputs)
            probs = torch.nn.functional.softmax(outputs.logits, dim=-1)
        
        # FinBERT outputs: [negative, neutral, positive]
        negative_prob = probs[0][0].item()
        neutral_prob = probs[0][1].item()
        positive_prob = probs[0][2].item()
        
        # Calculate sentiment score (-1 to +1)
        sentiment_score = positive_prob - negative_prob
        
        # Determine label
        max_prob = max(negative_prob, neutral_prob, positive_prob)
        if max_prob == positive_prob:
            label = "positive"
        elif max_prob == negative_prob:
            label = "negative"
        else:
            label = "neutral"
        
        result = (sentiment_score, label, max_prob)
        
        # Cache result
        self._cache[text_hash] = result
        
        return result
    
    def _get_sentiment_label(self, score: float) -> str:
        """Convert sentiment score to label."""
        if score > 0.2:
            return "bullish"
        elif score < -0.2:
            return "bearish"
        else:
            return "neutral"
    
    def fetch_news(self, query: str, hours: int = 48) -> List[Dict[str, Any]]:
        """
        Fetch news headlines from RSS feeds and web sources.
        
        Args:
            query: Search query (company name or symbol)
            hours: Number of hours to look back
        
        Returns:
            List of news headline dictionaries
        """
        headlines = []
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        # Fetch from RSS feeds
        for feed_url in self.rss_feeds:
            try:
                headlines.extend(self._fetch_rss_feed(feed_url, query, cutoff_time))
            except Exception as e:
                logger.error(f"Error fetching RSS feed {feed_url}: {e}")
                continue
        
        # Deduplicate headlines
        unique_headlines = []
        seen_titles = set()
        
        for headline in headlines:
            title_clean = re.sub(r'\s+', ' ', headline['title'].lower().strip())
            if title_clean not in seen_titles:
                seen_titles.add(title_clean)
                unique_headlines.append(headline)
        
        return unique_headlines
    
    def _fetch_rss_feed(self, feed_url: str, query: str, cutoff_time: datetime) -> List[Dict[str, Any]]:
        """
        Fetch headlines from a single RSS feed.
        
        Args:
            feed_url: RSS feed URL
            query: Search query to filter headlines
            cutoff_time: Only return headlines after this time
        
        Returns:
            List of headline dictionaries
        """
        headlines = []
        
        try:
            feed = feedparser.parse(feed_url)
            
            for entry in feed.entries:
                # Check if query appears in title or summary
                title = entry.get('title', '')
                summary = entry.get('summary', '')
                
                if not self._matches_query(title + ' ' + summary, query):
                    continue
                
                # Parse published date
                published_date = None
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    published_date = datetime(*entry.published_parsed[:6])
                
                # Filter by time
                if published_date and published_date < cutoff_time:
                    continue
                
                headlines.append({
                    'title': title,
                    'summary': summary,
                    'link': entry.get('link', ''),
                    'published': published_date.isoformat() if published_date else '',
                    'source': feed.feed.get('title', 'Unknown')
                })
        
        except Exception as e:
            logger.error(f"Error parsing RSS feed: {e}")
        
        return headlines
    
    def _matches_query(self, text: str, query: str) -> bool:
        """
        Check if text matches the search query.
        
        Args:
            text: Text to search in
            query: Query string
        
        Returns:
            True if query matches
        """
        text_lower = text.lower()
        query_lower = query.lower()
        
        # Direct match
        if query_lower in text_lower:
            return True
        
        # Handle common company name variations
        # e.g., "TCS" -> "Tata Consultancy", "RELIANCE" -> "Reliance Industries"
        company_aliases = {
            'tcs': ['tata consultancy', 'tata consulting'],
            'reliance': ['reliance industries', 'ril'],
            'infy': ['infosys'],
            'hdfc': ['hdfc bank'],
            'sbin': ['state bank', 'sbi'],
            'icici': ['icici bank'],
            'bharti': ['bharti airtel', 'airtel'],
        }
        
        for alias_key, aliases in company_aliases.items():
            if alias_key in query_lower:
                for alias in aliases:
                    if alias in text_lower:
                        return True
        
        return False
    
    def batch_analyze(self, symbols: List[str], hours: int = 48) -> Dict[str, Dict[str, Any]]:
        """
        Analyze sentiment for multiple symbols in batch.
        
        Args:
            symbols: List of stock symbols
            hours: Number of hours to look back for news
        
        Returns:
            Dictionary mapping symbols to sentiment results
        """
        results = {}
        
        for symbol in symbols:
            try:
                results[symbol] = self.analyze_sentiment(symbol, hours=hours)
            except Exception as e:
                logger.error(f"Error analyzing sentiment for {symbol}: {e}")
                results[symbol] = {
                    "symbol": symbol,
                    "sentiment_score": 0.0,
                    "sentiment_label": "neutral",
                    "news_count": 0,
                    "error": str(e)
                }
        
        return results
    
    def clear_cache(self):
        """Clear the sentiment cache."""
        self._cache.clear()


# Singleton instance
sentiment_analysis = SentimentAnalysis()
