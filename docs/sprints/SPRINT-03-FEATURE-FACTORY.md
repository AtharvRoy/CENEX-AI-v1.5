# Sprint 03: Feature Factory (Layer 2)

**Duration:** Week 5-6  
**Owner:** Sub-agent TBD  
**Status:** Not Started  
**Depends On:** Sprint 02 (Data Layer)

## Goals

Build the Feature Factory - technical indicators, regime detection, sentiment analysis, and macro features.

Layer 2 transforms raw OHLCV data into ML-ready features for the multi-agent system.

## Deliverables

### 1. Technical Indicators Service
- `backend/app/services/indicators.py`
  - **Momentum:** RSI, Stochastic, ROC, Williams %R
  - **Trend:** MACD, ADX, Aroon, Parabolic SAR
  - **Volatility:** Bollinger Bands, ATR, Keltner Channels
  - **Volume:** OBV, VWAP, Volume Profile, CMF
  - **Pattern Recognition:** Support/Resistance, Breakouts

### 2. Regime Detection Service
- `backend/app/services/regime.py`
  - **Volatility Regime:** High-vol vs Low-vol (rolling std, ATR percentile)
  - **Trend Regime:** Trending vs Ranging (ADX, price channel)
  - **Hidden Markov Model:** Multi-state regime classification (future)
  - Output: `{regime: "high_vol_trending", confidence: 0.85}`

### 3. Narrative/Sentiment Service
- `backend/app/services/sentiment.py`
  - **News Scraping:** RSS feeds (MoneyControl, ET, Reuters India)
  - **Sentiment Analysis:** FinBERT (HuggingFace Transformers)
  - **Aggregation:** Symbol-level sentiment score (-1 to +1)
  - **Freshness:** Last 24-48 hours of news

### 4. Macro Features Service (Future)
- `backend/app/services/macro.py`
  - **Yield Curve:** 10Y-2Y spread (RBI bonds)
  - **Inflation:** CPI, WPI data
  - **FII/DII Flow:** NSE institutional activity
  - **VIX:** India VIX (volatility index)

### 5. Feature Computation Pipeline
- `backend/app/services/feature_pipeline.py`
  - Fetch OHLCV from TimescaleDB
  - Compute all indicators
  - Detect regime
  - Fetch sentiment (if available)
  - Output: Feature vector (80-100 dimensions)
  - Cache in Redis (5-minute TTL)

### 6. Feature Storage
- **Option A:** Compute on-the-fly (MVP)
- **Option B:** Pre-compute and store in TimescaleDB (continuous table)
- **Decision:** Start with on-the-fly, optimize to pre-compute later

### 7. API Endpoints
- `GET /api/features/{symbol}` - get full feature vector
- `GET /api/indicators/{symbol}` - technical indicators only
- `GET /api/regime/{symbol}` - regime classification
- `GET /api/sentiment/{symbol}` - sentiment analysis

## Tech Stack

- **Indicators:** TA-Lib, pandas-ta (Python wrappers)
- **Sentiment:** Transformers (FinBERT), NLTK
- **News:** feedparser (RSS), BeautifulSoup (scraping)
- **ML:** scikit-learn (regime HMM), numpy, scipy

## Dependencies

```txt
ta-lib>=0.4.28  # Requires system install: apt-get install ta-lib
pandas-ta>=0.3.14b
transformers>=4.36.0
torch>=2.1.0  # CPU version for sentiment
feedparser>=6.0.10
beautifulsoup4>=4.12.0
nltk>=3.8.1
scikit-learn>=1.3.0
scipy>=1.11.0
```

## System Dependencies (Dockerfile)

```dockerfile
# Install TA-Lib system library
RUN apt-get update && apt-get install -y \
    wget \
    build-essential \
    && wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz \
    && tar -xzf ta-lib-0.4.0-src.tar.gz \
    && cd ta-lib/ \
    && ./configure --prefix=/usr \
    && make \
    && make install \
    && cd .. \
    && rm -rf ta-lib ta-lib-0.4.0-src.tar.gz \
    && apt-get clean
```

## Feature Vector Schema

```python
{
    "symbol": "RELIANCE.NS",
    "timestamp": "2026-02-28T14:30:00Z",
    "price": {
        "close": 2850.50,
        "change_pct": 1.2,
        "volume": 5000000
    },
    "technical": {
        "rsi_14": 65.2,
        "macd": 12.5,
        "macd_signal": 10.8,
        "adx_14": 32.1,
        "bb_upper": 2900,
        "bb_lower": 2800,
        "atr_14": 45.2,
        "obv": 125000000,
        "vwap": 2845.0
    },
    "regime": {
        "volatility": "low_vol",
        "trend": "trending",
        "combined": "low_vol_trending",
        "confidence": 0.82
    },
    "sentiment": {
        "score": 0.35,  # -1 (bearish) to +1 (bullish)
        "news_count": 8,
        "freshness_hours": 12
    },
    "computed_at": "2026-02-28T14:31:05Z"
}
```

## Regime Classification Logic

```python
def classify_regime(df):
    """Classify market regime based on volatility and trend."""
    
    # Volatility: rolling 20-day std percentile
    vol_percentile = df['returns'].rolling(20).std().rank(pct=True).iloc[-1]
    
    # Trend: ADX value
    adx = compute_adx(df)
    
    if vol_percentile > 0.7:
        vol_regime = "high_vol"
    elif vol_percentile > 0.3:
        vol_regime = "medium_vol"
    else:
        vol_regime = "low_vol"
    
    if adx > 25:
        trend_regime = "trending"
    else:
        trend_regime = "ranging"
    
    combined = f"{vol_regime}_{trend_regime}"
    confidence = min(vol_percentile, adx / 50)  # Normalized confidence
    
    return {
        "volatility": vol_regime,
        "trend": trend_regime,
        "combined": combined,
        "confidence": confidence
    }
```

## Sentiment Pipeline

```python
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch

# Load FinBERT (one-time)
tokenizer = AutoTokenizer.from_pretrained("ProsusAI/finbert")
model = AutoModelForSequenceClassification.from_pretrained("ProsusAI/finbert")

def analyze_sentiment(headlines: list[str]) -> float:
    """Analyze sentiment of news headlines."""
    
    if not headlines:
        return 0.0
    
    scores = []
    for headline in headlines:
        inputs = tokenizer(headline, return_tensors="pt", truncation=True, max_length=512)
        outputs = model(**inputs)
        probs = torch.nn.functional.softmax(outputs.logits, dim=-1)
        
        # FinBERT output: [negative, neutral, positive]
        sentiment = probs[0][2].item() - probs[0][0].item()  # positive - negative
        scores.append(sentiment)
    
    return sum(scores) / len(scores)  # Average sentiment
```

## Performance Targets

- **Feature computation:** <2 seconds per symbol
- **Indicator calculation:** <500ms for full suite
- **Sentiment analysis:** <3 seconds per symbol (batch if multiple)
- **Cache hit rate:** >70% for recent features

## Testing

- Unit tests: Individual indicator calculations (known inputs → expected outputs)
- Integration tests: Full feature pipeline
- Accuracy tests: Compare TA-Lib output with reference data
- Sentiment tests: Sample headlines with expected sentiment

## Acceptance Criteria

- [ ] All technical indicators compute correctly (validated against known data)
- [ ] Regime classification works for sample symbols
- [ ] Sentiment analysis returns scores for news headlines
- [ ] Feature vector API returns complete data
- [ ] Features cached in Redis for performance
- [ ] Documentation of feature engineering decisions

## Next Sprint

**Sprint 04: Multi-Agent Intelligence (Layer 3)** - Quant, Sentiment, Regime, Risk agents

---

**Assigned to:** Sub-agent (feature-factory)  
**Start Date:** TBD (after Sprint 02)  
**Target Completion:** TBD  
