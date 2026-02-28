"""
Meta-Learner Training Pipeline
Trains the ensemble meta-model on historical agent predictions.
"""

import numpy as np
import pandas as pd
import logging
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
from datetime import datetime, timedelta
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
import joblib

from app.services.meta_decision_engine import meta_decision_engine

logger = logging.getLogger(__name__)


class MetaLearnerTrainer:
    """Training pipeline for meta-learner ensemble model."""
    
    def __init__(self):
        """Initialize MetaLearnerTrainer."""
        self.model_dir = Path("backend/models")
        self.model_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_synthetic_training_data(
        self,
        n_samples: int = 1000,
        noise_level: float = 0.1
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Generate synthetic training data for meta-learner.
        
        This is used for initial training when no historical data exists.
        In production, replace with actual agent predictions + outcomes.
        
        Args:
            n_samples: Number of samples to generate
            noise_level: Amount of random noise (0-1)
        
        Returns:
            (agent_predictions, true_outcomes)
        """
        logger.info(f"Generating {n_samples} synthetic training samples...")
        
        np.random.seed(42)
        
        agent_predictions = []
        true_outcomes = []
        
        for _ in range(n_samples):
            # Generate true market direction (0=STRONG_SELL, 1=SELL, 2=HOLD, 3=BUY, 4=STRONG_BUY)
            true_outcome = np.random.choice([0, 1, 2, 3, 4], p=[0.1, 0.2, 0.4, 0.2, 0.1])
            
            # Generate agent predictions (with some accuracy)
            agent_preds = []
            
            for agent_idx in range(4):  # 4 agents
                # Agent has base accuracy + some noise
                if np.random.random() > noise_level:
                    # Predict close to true outcome
                    signal_value = true_outcome + np.random.choice([-1, 0, 1], p=[0.2, 0.6, 0.2])
                    signal_value = np.clip(signal_value, 0, 4)
                else:
                    # Random prediction
                    signal_value = np.random.choice([0, 1, 2, 3, 4])
                
                # Convert to centered value (-2 to +2)
                signal_value_centered = signal_value - 2
                
                # Generate confidence (higher for correct predictions)
                if signal_value == true_outcome:
                    confidence = np.random.uniform(0.7, 0.95)
                else:
                    confidence = np.random.uniform(0.5, 0.75)
                
                agent_preds.extend([signal_value_centered, confidence])
            
            agent_predictions.append(agent_preds)
            true_outcomes.append(true_outcome)
        
        return np.array(agent_predictions), np.array(true_outcomes)
    
    def load_historical_data(
        self,
        filepath: Optional[str] = None
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Load historical agent predictions and outcomes from file.
        
        Expected format: CSV with columns:
        - quant_signal, quant_confidence
        - sentiment_signal, sentiment_confidence
        - regime_signal, regime_confidence
        - risk_signal, risk_confidence
        - outcome (0-4)
        
        Args:
            filepath: Path to CSV file
        
        Returns:
            (agent_predictions, true_outcomes)
        """
        if filepath is None:
            filepath = "backend/data/historical_agent_predictions.csv"
        
        try:
            df = pd.read_csv(filepath)
            
            # Extract agent predictions
            agent_cols = [
                "quant_signal", "quant_confidence",
                "sentiment_signal", "sentiment_confidence",
                "regime_signal", "regime_confidence",
                "risk_signal", "risk_confidence"
            ]
            
            agent_predictions = df[agent_cols].values
            true_outcomes = df["outcome"].values
            
            logger.info(f"Loaded {len(df)} historical samples from {filepath}")
            
            return agent_predictions, true_outcomes
        
        except FileNotFoundError:
            logger.warning(f"Historical data file not found: {filepath}")
            raise
        except Exception as e:
            logger.error(f"Error loading historical data: {e}")
            raise
    
    def train(
        self,
        agent_predictions: np.ndarray,
        true_outcomes: np.ndarray,
        test_size: float = 0.2,
        cross_validate: bool = True,
        model_version: str = "v1"
    ) -> Dict[str, Any]:
        """
        Train meta-learner model.
        
        Args:
            agent_predictions: Shape (n_samples, 8) - encoded agent signals
            true_outcomes: Shape (n_samples,) - actual outcomes (0-4)
            test_size: Fraction of data for testing
            cross_validate: Whether to perform cross-validation
            model_version: Model version tag
        
        Returns:
            Training results and metrics
        """
        try:
            logger.info("Starting meta-learner training...")
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                agent_predictions,
                true_outcomes,
                test_size=test_size,
                random_state=42,
                stratify=true_outcomes
            )
            
            logger.info(f"Training samples: {len(X_train)}, Test samples: {len(X_test)}")
            
            # Train model
            model_path = f"backend/models/meta_learner_{model_version}.pkl"
            training_result = meta_decision_engine.train_meta_learner(
                agent_predictions=X_train,
                true_outcomes=y_train,
                save_path=model_path
            )
            
            if training_result["status"] != "success":
                return training_result
            
            # Evaluate on test set
            logger.info("Evaluating on test set...")
            
            # Reload model
            meta_decision_engine.reload_model()
            
            # Predict on test set
            test_predictions = []
            for i in range(len(X_test)):
                # Encode as agent outputs format
                agent_outputs = self._decode_agent_predictions(X_test[i])
                result = meta_decision_engine.ensemble(agent_outputs)
                predicted_signal = result["signal"]
                
                # Map signal to outcome
                signal_to_outcome = {
                    "STRONG_SELL": 0,
                    "SELL": 1,
                    "HOLD": 2,
                    "BUY": 3,
                    "STRONG_BUY": 4,
                    "NO_SIGNAL": 2  # Default to HOLD
                }
                predicted_outcome = signal_to_outcome.get(predicted_signal, 2)
                test_predictions.append(predicted_outcome)
            
            test_predictions = np.array(test_predictions)
            
            # Calculate metrics
            test_accuracy = accuracy_score(y_test, test_predictions)
            
            # Classification report
            report = classification_report(
                y_test,
                test_predictions,
                target_names=["STRONG_SELL", "SELL", "HOLD", "BUY", "STRONG_BUY"],
                output_dict=True
            )
            
            # Confusion matrix
            conf_matrix = confusion_matrix(y_test, test_predictions)
            
            # Cross-validation
            cv_scores = None
            if cross_validate:
                logger.info("Performing cross-validation...")
                from sklearn.linear_model import LogisticRegression
                from sklearn.calibration import CalibratedClassifierCV
                
                base_model = LogisticRegression(
                    multi_class='multinomial',
                    max_iter=1000,
                    random_state=42,
                    class_weight='balanced'
                )
                meta_model = CalibratedClassifierCV(base_model, method='sigmoid', cv=5)
                
                cv_scores = cross_val_score(
                    meta_model,
                    agent_predictions,
                    true_outcomes,
                    cv=5,
                    scoring='accuracy'
                )
                
                logger.info(f"Cross-validation accuracy: {cv_scores.mean():.3f} (+/- {cv_scores.std():.3f})")
            
            # Compile results
            results = {
                "status": "success",
                "model_version": model_version,
                "model_path": model_path,
                "training_samples": len(X_train),
                "test_samples": len(X_test),
                "train_accuracy": training_result["train_accuracy"],
                "test_accuracy": float(test_accuracy),
                "classification_report": report,
                "confusion_matrix": conf_matrix.tolist(),
                "cv_scores": cv_scores.tolist() if cv_scores is not None else None,
                "cv_mean": float(cv_scores.mean()) if cv_scores is not None else None,
                "cv_std": float(cv_scores.std()) if cv_scores is not None else None,
                "trained_at": datetime.now().isoformat()
            }
            
            # Save training report
            report_path = f"backend/models/meta_learner_{model_version}_report.json"
            import json
            with open(report_path, 'w') as f:
                json.dump(results, f, indent=2)
            
            logger.info(f"Training complete! Test accuracy: {test_accuracy:.3f}")
            logger.info(f"Model saved to: {model_path}")
            logger.info(f"Report saved to: {report_path}")
            
            return results
        
        except Exception as e:
            logger.error(f"Error training meta-learner: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def _decode_agent_predictions(self, encoded_features: np.ndarray) -> Dict[str, Dict[str, Any]]:
        """
        Decode numerical features back to agent outputs format.
        
        Args:
            encoded_features: Numpy array of shape (8,)
        
        Returns:
            Agent outputs dictionary
        """
        agents = ["quant", "sentiment", "regime", "risk"]
        signal_map = {
            -2: "STRONG_SELL",
            -1: "SELL",
            0: "HOLD",
            1: "BUY",
            2: "STRONG_BUY"
        }
        
        agent_outputs = {}
        
        for i, agent_name in enumerate(agents):
            signal_value = encoded_features[i * 2]
            confidence = encoded_features[i * 2 + 1]
            
            if agent_name == "risk":
                signal = "APPROVE" if signal_value > 0 else "REJECT"
            else:
                signal = signal_map.get(int(round(signal_value)), "HOLD")
            
            agent_outputs[agent_name] = {
                "signal": signal,
                "confidence": float(confidence)
            }
        
        return agent_outputs
    
    def retrain_with_new_data(
        self,
        new_predictions: np.ndarray,
        new_outcomes: np.ndarray,
        model_version: str = "v2"
    ) -> Dict[str, Any]:
        """
        Retrain meta-learner with new data (incremental learning).
        
        Args:
            new_predictions: New agent predictions
            new_outcomes: New outcomes
            model_version: New model version tag
        
        Returns:
            Training results
        """
        logger.info("Retraining meta-learner with new data...")
        
        # In a production system, you would:
        # 1. Load old training data
        # 2. Combine with new data
        # 3. Retrain model
        
        # For now, just train on new data
        return self.train(
            agent_predictions=new_predictions,
            true_outcomes=new_outcomes,
            model_version=model_version
        )


# Standalone training script
if __name__ == "__main__":
    """
    Run this script to train the meta-learner:
    
    python -m app.ml.train_meta_learner
    """
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    trainer = MetaLearnerTrainer()
    
    # Try to load historical data, fallback to synthetic
    try:
        logger.info("Attempting to load historical data...")
        X, y = trainer.load_historical_data()
    except Exception as e:
        logger.warning(f"Could not load historical data: {e}")
        logger.info("Generating synthetic training data...")
        X, y = trainer.generate_synthetic_training_data(n_samples=2000)
    
    # Train model
    results = trainer.train(
        agent_predictions=X,
        true_outcomes=y,
        cross_validate=True,
        model_version="v1"
    )
    
    if results["status"] == "success":
        print("\n" + "="*60)
        print("META-LEARNER TRAINING COMPLETE")
        print("="*60)
        print(f"Model: {results['model_path']}")
        print(f"Train Accuracy: {results['train_accuracy']:.3f}")
        print(f"Test Accuracy: {results['test_accuracy']:.3f}")
        if results['cv_mean']:
            print(f"CV Accuracy: {results['cv_mean']:.3f} (+/- {results['cv_std']:.3f})")
        print("="*60)
    else:
        print(f"\nTraining failed: {results.get('error')}")
