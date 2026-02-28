"""
Sentiment Agent Training Pipeline
Train logistic regression for sentiment → signal mapping.
"""

import os
import sys
import logging
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Tuple
from datetime import datetime
import asyncio

sys.path.append(str(Path(__file__).parent.parent.parent))

from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import async_session
from app.services.sentiment import sentiment_analysis

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class SentimentAgentTrainer:
    """Trainer for Sentiment Agent logistic regression model."""
    
    def __init__(self):
        """Initialize trainer."""
        pass
    
    def generate_synthetic_training_data(self, n_samples: int = 1000) -> Tuple[pd.DataFrame, pd.Series]:
        """
        Generate synthetic training data for sentiment model.
        
        In production, this would use historical sentiment + price movement data.
        
        Args:
            n_samples: Number of samples to generate
        
        Returns:
            (X, y) tuple of features and labels
        """
        np.random.seed(42)
        
        # Synthetic sentiment scores
        sentiment_scores = np.random.randn(n_samples) * 0.3
        
        # Synthetic news counts (Poisson distribution)
        news_counts = np.random.poisson(3, n_samples)
        
        # Synthetic freshness (0 to 48 hours)
        freshness_hours = np.random.uniform(0, 48, n_samples)
        
        # Create features
        X = pd.DataFrame({
            'sentiment_score': sentiment_scores,
            'news_count_normalized': np.minimum(news_counts / 10.0, 1.0),
            'freshness_normalized': np.maximum(0, 1.0 - freshness_hours / 48.0)
        })
        
        # Generate labels based on sentiment with noise
        def generate_label(row):
            sentiment = row['sentiment_score']
            noise = np.random.randn() * 0.1
            
            if sentiment + noise > 0.2:
                return 2  # BUY
            elif sentiment + noise < -0.2:
                return 0  # SELL
            else:
                return 1  # HOLD
        
        y = X.apply(generate_label, axis=1)
        
        logger.info(f"Generated {n_samples} synthetic training samples")
        logger.info(f"Label distribution: {y.value_counts().to_dict()}")
        
        return X, y
    
    def train_model(self, X: pd.DataFrame, y: pd.Series) -> Any:
        """
        Train logistic regression model.
        
        Args:
            X: Feature matrix
            y: Labels (0=SELL, 1=HOLD, 2=BUY)
        
        Returns:
            Trained model
        """
        try:
            from sklearn.linear_model import LogisticRegression
            from sklearn.model_selection import train_test_split
            from sklearn.metrics import classification_report, accuracy_score
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42, stratify=y
            )
            
            logger.info(f"Training set: {len(X_train)} samples")
            logger.info(f"Test set: {len(X_test)} samples")
            
            # Train model
            model = LogisticRegression(
                multi_class='multinomial',
                solver='lbfgs',
                max_iter=1000,
                random_state=42
            )
            
            model.fit(X_train, y_train)
            
            # Evaluate
            y_pred = model.predict(X_test)
            accuracy = accuracy_score(y_test, y_pred)
            
            logger.info(f"Test accuracy: {accuracy:.4f}")
            logger.info("\nClassification Report:")
            logger.info(classification_report(
                y_test, 
                y_pred,
                target_names=['SELL', 'HOLD', 'BUY']
            ))
            
            # Feature importance (coefficients)
            logger.info("\nFeature Coefficients:")
            for i, feature in enumerate(X.columns):
                logger.info(f"{feature}: {model.coef_[:, i]}")
            
            return model
        
        except ImportError as e:
            logger.error(f"Missing required library: {e}")
            logger.error("Install with: pip install scikit-learn")
            raise
    
    def save_model(self, model: Any, model_path: str = None):
        """
        Save trained model.
        
        Args:
            model: Trained model
            model_path: Path to save model
        """
        if model_path is None:
            model_dir = Path(__file__).parent.parent.parent / "models"
            model_dir.mkdir(exist_ok=True)
            model_path = model_dir / "sentiment_agent_v1.pkl"
        
        import joblib
        joblib.dump(model, model_path)
        
        logger.info(f"Model saved to {model_path}")
        
        # Save metadata
        metadata = {
            "model_type": "logistic_regression",
            "version": "1.0",
            "trained_at": datetime.now().isoformat(),
            "features": [
                "sentiment_score",
                "news_count_normalized",
                "freshness_normalized"
            ],
            "labels": ["SELL", "HOLD", "BUY"]
        }
        
        metadata_path = Path(model_path).parent / "sentiment_agent_metadata.json"
        import json
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        logger.info(f"Metadata saved to {metadata_path}")


def main():
    """Main training pipeline."""
    trainer = SentimentAgentTrainer()
    
    logger.info("Generating training data...")
    X, y = trainer.generate_synthetic_training_data(n_samples=1000)
    
    logger.info("Training model...")
    model = trainer.train_model(X, y)
    
    logger.info("Saving model...")
    trainer.save_model(model)
    
    logger.info("Training complete!")


if __name__ == "__main__":
    main()
