"""
Quant Agent Training Pipeline
Train LightGBM classifier for quantitative signal generation.
"""

import os
import sys
import logging
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, Any, Tuple
from datetime import datetime, timedelta
import asyncio

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import async_session
from app.services.feature_pipeline import FeaturePipeline

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class QuantAgentTrainer:
    """Trainer for Quant Agent LightGBM model."""
    
    FEATURE_COLS = [
        'rsi_14', 'rsi_28',
        'macd', 'macd_signal', 'macd_hist',
        'adx_14',
        'bb_upper', 'bb_middle', 'bb_lower', 'bb_width',
        'atr_14',
        'obv_pct',
        'vwap_distance',
        'volume_sma_ratio',
        'returns_5d', 'returns_20d',
        'volatility_20d',
        'momentum_10d',
    ]
    
    def __init__(self, lookahead_days: int = 5):
        """
        Initialize trainer.
        
        Args:
            lookahead_days: Days to look ahead for labeling
        """
        self.lookahead_days = lookahead_days
        self.feature_pipeline = FeaturePipeline()
    
    def generate_labels(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Generate labels based on future returns.
        
        Labels:
        - STRONG_BUY (4): >5% gain
        - BUY (3): 2-5% gain
        - HOLD (2): -2% to +2%
        - SELL (1): -5% to -2%
        - STRONG_SELL (0): <-5% loss
        
        Args:
            df: DataFrame with price data
        
        Returns:
            DataFrame with labels
        """
        # Compute future returns
        df['future_return'] = df['close'].pct_change(self.lookahead_days).shift(-self.lookahead_days)
        
        # Classify returns
        def classify_return(ret):
            if pd.isna(ret):
                return None
            elif ret > 0.05:
                return 4  # STRONG_BUY
            elif ret > 0.02:
                return 3  # BUY
            elif ret > -0.02:
                return 2  # HOLD
            elif ret > -0.05:
                return 1  # SELL
            else:
                return 0  # STRONG_SELL
        
        df['label'] = df['future_return'].apply(classify_return)
        
        # Drop rows without labels
        df_labeled = df.dropna(subset=['label'])
        
        return df_labeled
    
    async def prepare_training_data(
        self,
        symbols: list,
        exchange: str,
        db: AsyncSession
    ) -> Tuple[pd.DataFrame, pd.Series]:
        """
        Prepare training data from historical features.
        
        Args:
            symbols: List of symbols to train on
            exchange: Exchange name
            db: Database session
        
        Returns:
            (X, y) tuple of features and labels
        """
        all_features = []
        all_labels = []
        
        for symbol in symbols:
            try:
                logger.info(f"Processing {symbol}")
                
                # Get features
                features = await self.feature_pipeline.compute_features(
                    symbol=symbol,
                    exchange=exchange,
                    db=db,
                    include_sentiment=False  # Quant agent doesn't use sentiment
                )
                
                # Extract technical indicators
                technical = features.get('technical', {})
                
                # Build feature vector
                feature_vector = {}
                for col in self.FEATURE_COLS:
                    feature_vector[col] = technical.get(col, 0.0)
                
                # Get price for labeling
                price = features.get('price', {}).get('close')
                if price is None:
                    continue
                
                # For training, we need historical data to generate labels
                # This is simplified - in production, fetch historical OHLCV
                # and compute features + labels for each time period
                
                # Placeholder: assume we have the data
                # In reality, you'd query market_data table for historical data
                
                all_features.append(feature_vector)
                
            except Exception as e:
                logger.error(f"Error processing {symbol}: {e}")
                continue
        
        # Convert to DataFrame
        X = pd.DataFrame(all_features)
        
        # For now, create synthetic labels (replace with real historical labels)
        # In production, use generate_labels() on historical data
        y = pd.Series([2] * len(X))  # Placeholder: all HOLD
        
        return X, y
    
    def train_model(
        self,
        X: pd.DataFrame,
        y: pd.Series,
        use_optuna: bool = False,
        n_trials: int = 50
    ) -> Any:
        """
        Train LightGBM model.
        
        Args:
            X: Feature matrix
            y: Labels
            use_optuna: Whether to use Optuna for hyperparameter tuning
            n_trials: Number of Optuna trials
        
        Returns:
            Trained model
        """
        try:
            import lightgbm as lgb
            from sklearn.model_selection import train_test_split
            from sklearn.metrics import classification_report, accuracy_score
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42, stratify=y
            )
            
            logger.info(f"Training set: {len(X_train)} samples")
            logger.info(f"Test set: {len(X_test)} samples")
            logger.info(f"Label distribution: {y.value_counts().to_dict()}")
            
            if use_optuna:
                logger.info("Starting hyperparameter tuning with Optuna")
                model = self._train_with_optuna(X_train, y_train, X_test, y_test, n_trials)
            else:
                logger.info("Training with default parameters")
                model = self._train_default(X_train, y_train, X_test, y_test)
            
            # Evaluate
            y_pred = model.predict(X_test)
            accuracy = accuracy_score(y_test, y_pred)
            
            logger.info(f"Test accuracy: {accuracy:.4f}")
            logger.info("\nClassification Report:")
            logger.info(classification_report(y_test, y_pred))
            
            return model
        
        except ImportError as e:
            logger.error(f"Missing required library: {e}")
            logger.error("Install with: pip install lightgbm scikit-learn optuna")
            raise
    
    def _train_default(self, X_train, y_train, X_test, y_test):
        """Train with default parameters."""
        import lightgbm as lgb
        
        params = {
            'objective': 'multiclass',
            'num_class': 5,
            'metric': 'multi_logloss',
            'boosting_type': 'gbdt',
            'num_leaves': 31,
            'learning_rate': 0.05,
            'feature_fraction': 0.8,
            'bagging_fraction': 0.8,
            'bagging_freq': 5,
            'verbose': -1
        }
        
        train_data = lgb.Dataset(X_train, label=y_train)
        test_data = lgb.Dataset(X_test, label=y_test, reference=train_data)
        
        model = lgb.train(
            params,
            train_data,
            num_boost_round=200,
            valid_sets=[test_data],
            callbacks=[lgb.early_stopping(stopping_rounds=20)]
        )
        
        return model
    
    def _train_with_optuna(self, X_train, y_train, X_test, y_test, n_trials):
        """Train with Optuna hyperparameter tuning."""
        import lightgbm as lgb
        import optuna
        
        def objective(trial):
            params = {
                'objective': 'multiclass',
                'num_class': 5,
                'metric': 'multi_logloss',
                'boosting_type': 'gbdt',
                'num_leaves': trial.suggest_int('num_leaves', 20, 50),
                'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.1),
                'feature_fraction': trial.suggest_float('feature_fraction', 0.6, 1.0),
                'bagging_fraction': trial.suggest_float('bagging_fraction', 0.6, 1.0),
                'bagging_freq': trial.suggest_int('bagging_freq', 1, 10),
                'min_child_samples': trial.suggest_int('min_child_samples', 10, 50),
                'verbose': -1
            }
            
            train_data = lgb.Dataset(X_train, label=y_train)
            test_data = lgb.Dataset(X_test, label=y_test, reference=train_data)
            
            model = lgb.train(
                params,
                train_data,
                num_boost_round=200,
                valid_sets=[test_data],
                callbacks=[lgb.early_stopping(stopping_rounds=20)]
            )
            
            y_pred = model.predict(X_test)
            y_pred_class = np.argmax(y_pred, axis=1)
            
            from sklearn.metrics import accuracy_score
            accuracy = accuracy_score(y_test, y_pred_class)
            
            return accuracy
        
        study = optuna.create_study(direction='maximize')
        study.optimize(objective, n_trials=n_trials)
        
        logger.info(f"Best trial accuracy: {study.best_trial.value:.4f}")
        logger.info(f"Best parameters: {study.best_trial.params}")
        
        # Train final model with best parameters
        best_params = study.best_trial.params
        best_params.update({
            'objective': 'multiclass',
            'num_class': 5,
            'metric': 'multi_logloss',
            'boosting_type': 'gbdt',
            'verbose': -1
        })
        
        train_data = lgb.Dataset(X_train, label=y_train)
        model = lgb.train(best_params, train_data, num_boost_round=200)
        
        return model
    
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
            model_path = model_dir / "quant_agent_v1.pkl"
        
        import joblib
        joblib.dump(model, model_path)
        
        logger.info(f"Model saved to {model_path}")
        
        # Save metadata
        metadata = {
            "model_type": "lightgbm",
            "version": "1.0",
            "trained_at": datetime.now().isoformat(),
            "features": self.FEATURE_COLS,
            "lookahead_days": self.lookahead_days
        }
        
        metadata_path = Path(model_path).parent / "quant_agent_metadata.json"
        import json
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        logger.info(f"Metadata saved to {metadata_path}")


async def main():
    """Main training pipeline."""
    # Training symbols (NSE top stocks)
    symbols = [
        "RELIANCE.NS",
        "TCS.NS",
        "HDFCBANK.NS",
        "INFY.NS",
        "HINDUNILVR.NS",
        "ICICIBANK.NS",
        "SBIN.NS",
        "BHARTIARTL.NS",
        "ITC.NS",
        "KOTAKBANK.NS"
    ]
    
    trainer = QuantAgentTrainer(lookahead_days=5)
    
    async with async_session() as db:
        logger.info("Preparing training data...")
        X, y = await trainer.prepare_training_data(symbols, "NSE", db)
        
        logger.info(f"Training data shape: {X.shape}")
        logger.info(f"Labels shape: {y.shape}")
        
        if len(X) < 10:
            logger.error("Insufficient training data. Need historical market data first.")
            logger.info("Run data ingestion pipeline to populate database with historical data.")
            return
        
        logger.info("Training model...")
        model = trainer.train_model(X, y, use_optuna=False)
        
        logger.info("Saving model...")
        trainer.save_model(model)
        
        logger.info("Training complete!")


if __name__ == "__main__":
    asyncio.run(main())
