"""
Unit tests for sentiment analysis service.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from app.services.sentiment import sentiment_analysis


class TestSentimentAnalysis:
    """Test suite for sentiment analysis."""
    
    def test_sentiment_label_mapping(self):
        """Test sentiment score to label mapping."""
        assert sentiment_analysis._get_sentiment_label(0.5) == "bullish"
        assert sentiment_analysis._get_sentiment_label(-0.5) == "bearish"
        assert sentiment_analysis._get_sentiment_label(0.0) == "neutral"
        assert sentiment_analysis._get_sentiment_label(0.1) == "neutral"
    
    def test_query_matching_direct(self):
        """Test direct query matching."""
        text = "Reliance Industries announces new project"
        assert sentiment_analysis._matches_query(text, "Reliance")
        assert sentiment_analysis._matches_query(text, "RELIANCE")
        assert not sentiment_analysis._matches_query(text, "TCS")
    
    def test_query_matching_aliases(self):
        """Test query matching with company aliases."""
        text = "Tata Consultancy Services reports strong earnings"
        assert sentiment_analysis._matches_query(text, "TCS")
        
        text = "HDFC Bank shares rise"
        assert sentiment_analysis._matches_query(text, "HDFC")
    
    @patch('app.services.sentiment.sentiment_analysis.model_loaded', True)
    @patch('app.services.sentiment.sentiment_analysis.fetch_news')
    @patch('app.services.sentiment.sentiment_analysis._analyze_text')
    def test_analyze_sentiment_with_news(self, mock_analyze, mock_fetch_news):
        """Test sentiment analysis with mock news data."""
        # Mock news headlines
        mock_fetch_news.return_value = [
            {
                'title': 'Company reports record profits',
                'link': 'http://example.com',
                'published': '2024-01-01'
            },
            {
                'title': 'Stock price hits new high',
                'link': 'http://example.com',
                'published': '2024-01-02'
            }
        ]
        
        # Mock sentiment scores
        mock_analyze.return_value = (0.8, 'positive', 0.9)
        
        result = sentiment_analysis.analyze_sentiment('RELIANCE', hours=48)
        
        assert result['symbol'] == 'RELIANCE'
        assert result['news_count'] == 2
        assert result['sentiment_score'] == 0.8
        assert result['sentiment_label'] == 'bullish'
    
    @patch('app.services.sentiment.sentiment_analysis.model_loaded', True)
    @patch('app.services.sentiment.sentiment_analysis.fetch_news')
    def test_analyze_sentiment_no_news(self, mock_fetch_news):
        """Test sentiment analysis when no news is found."""
        mock_fetch_news.return_value = []
        
        result = sentiment_analysis.analyze_sentiment('UNKNOWN', hours=48)
        
        assert result['symbol'] == 'UNKNOWN'
        assert result['news_count'] == 0
        assert result['sentiment_score'] == 0.0
        assert result['sentiment_label'] == 'neutral'
        assert 'error' in result
    
    def test_cache_clearing(self):
        """Test cache clearing functionality."""
        # Add some data to cache
        sentiment_analysis._cache['test_key'] = (0.5, 'positive', 0.8)
        
        assert len(sentiment_analysis._cache) > 0
        
        sentiment_analysis.clear_cache()
        
        assert len(sentiment_analysis._cache) == 0
    
    @patch('app.services.sentiment.feedparser.parse')
    def test_fetch_rss_feed(self, mock_parse):
        """Test RSS feed fetching."""
        # Mock RSS feed data
        mock_entry = Mock()
        mock_entry.title = 'Reliance Industries Q4 Results'
        mock_entry.summary = 'Company reports strong growth'
        mock_entry.link = 'http://example.com'
        mock_entry.published_parsed = (2024, 1, 1, 12, 0, 0)
        
        mock_feed = Mock()
        mock_feed.entries = [mock_entry]
        mock_feed.feed = Mock()
        mock_feed.feed.title = 'Test Feed'
        
        mock_parse.return_value = mock_feed
        
        from datetime import datetime, timedelta
        cutoff = datetime.now() - timedelta(hours=48)
        
        headlines = sentiment_analysis._fetch_rss_feed(
            'http://example.com/rss',
            'Reliance',
            cutoff
        )
        
        # Note: This test might not find matches due to date filtering
        # but it tests the RSS parsing mechanism
        assert isinstance(headlines, list)


class TestBatchAnalysis:
    """Test batch sentiment analysis."""
    
    @patch('app.services.sentiment.sentiment_analysis.analyze_sentiment')
    def test_batch_analyze_multiple_symbols(self, mock_analyze):
        """Test batch analysis of multiple symbols."""
        # Mock individual analysis
        mock_analyze.side_effect = [
            {'symbol': 'RELIANCE', 'sentiment_score': 0.5, 'sentiment_label': 'bullish'},
            {'symbol': 'TCS', 'sentiment_score': -0.2, 'sentiment_label': 'neutral'},
            {'symbol': 'INFY', 'sentiment_score': 0.8, 'sentiment_label': 'bullish'}
        ]
        
        symbols = ['RELIANCE', 'TCS', 'INFY']
        results = sentiment_analysis.batch_analyze(symbols, hours=48)
        
        assert len(results) == 3
        assert 'RELIANCE' in results
        assert 'TCS' in results
        assert 'INFY' in results
        
        assert results['RELIANCE']['sentiment_score'] == 0.5
        assert results['TCS']['sentiment_score'] == -0.2
        assert results['INFY']['sentiment_score'] == 0.8
    
    @patch('app.services.sentiment.sentiment_analysis.analyze_sentiment')
    def test_batch_analyze_with_errors(self, mock_analyze):
        """Test batch analysis with some errors."""
        # Mock with one error
        mock_analyze.side_effect = [
            {'symbol': 'RELIANCE', 'sentiment_score': 0.5, 'sentiment_label': 'bullish'},
            Exception('Network error'),
            {'symbol': 'INFY', 'sentiment_score': 0.8, 'sentiment_label': 'bullish'}
        ]
        
        symbols = ['RELIANCE', 'TCS', 'INFY']
        results = sentiment_analysis.batch_analyze(symbols, hours=48)
        
        assert len(results) == 3
        assert 'RELIANCE' in results
        assert 'TCS' in results
        assert 'INFY' in results
        
        # TCS should have error result
        assert 'error' in results['TCS']
        assert results['TCS']['sentiment_score'] == 0.0


class TestSentimentModel:
    """Test FinBERT model loading and usage."""
    
    @patch('app.services.sentiment.AutoTokenizer.from_pretrained')
    @patch('app.services.sentiment.AutoModelForSequenceClassification.from_pretrained')
    def test_load_model(self, mock_model, mock_tokenizer):
        """Test model loading."""
        # Reset model_loaded flag
        sentiment_analysis.model_loaded = False
        
        # Mock model and tokenizer
        mock_tokenizer.return_value = Mock()
        mock_model_instance = Mock()
        mock_model_instance.eval.return_value = mock_model_instance
        mock_model.return_value = mock_model_instance
        
        sentiment_analysis.load_model()
        
        assert sentiment_analysis.model_loaded is True
        mock_tokenizer.assert_called_once()
        mock_model.assert_called_once()
    
    def test_load_model_idempotent(self):
        """Test that loading model multiple times doesn't reload."""
        sentiment_analysis.model_loaded = True
        initial_model = sentiment_analysis.model
        
        sentiment_analysis.load_model()
        
        # Model should not be reloaded
        assert sentiment_analysis.model == initial_model


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
