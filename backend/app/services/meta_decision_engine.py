"""
Meta Decision Engine (Layer 4)
Ensemble agent predictions using logistic regression stacking.
"""

import numpy as np
import joblib
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path
from sklearn.linear_model import LogisticRegression
from sklearn.calibration import CalibratedClassifierCV
from datetime import datetime

logger = logging.getLogger(__name__)


class MetaDecisionEngine:
    """
    Meta Decision Engine - Ensemble multiple agent predictions into final signal.
    
    Uses logistic regression stacking with Platt scaling for probability calibration.
    """
    
    # Signal type mappings
    SIGNAL_TYPES = {
        "STRONG_SELL": 0,
        "SELL": 1,
        "HOLD": 2,
        "BUY": 3,
        "STRONG_BUY": 4
    }
    
    SIGNAL_TYPES_REVERSE = {v: k for k, v in SIGNAL_TYPES.items()}
    
    def __init__(self, model_path: Optional[str] = None):
        """
        Initialize Meta Decision Engine.
        
        Args:
            model_path: Path to saved meta-learner model
        """
        self.model = None
        self.model_path = model_path or "backend/models/meta_learner_v1.pkl"
        self._load_model()
    
    def _load_model(self):
        """Load trained meta-learner model if it exists."""
        try:
            model_file = Path(self.model_path)
            if model_file.exists():
                self.model = joblib.load(model_file)
                logger.info(f"Meta-learner model loaded from {self.model_path}")
            else:
                logger.warning(f"Meta-learner model not found at {self.model_path}. Will use fallback voting.")
                self.model = None
        except Exception as e:
            logger.error(f"Error loading meta-learner model: {e}")
            self.model = None
    
    def ensemble(
        self, 
        agent_outputs: Dict[str, Dict[str, Any]],
        features: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Ensemble agent predictions into final signal.
        
        Args:
            agent_outputs: Dictionary of agent outputs
                {
                    "quant": {"signal": "BUY", "confidence": 0.78},
                    "sentiment": {"signal": "BUY", "confidence": 0.65},
                    "regime": {"signal": "HOLD", "confidence": 0.82},
                    "risk": {"signal": "APPROVE", "confidence": 0.85}
                }
            features: Optional feature vector for additional context
        
        Returns:
            Final signal with confidence and probabilities
        """
        try:
            # Encode agent outputs to numerical features
            encoded_features = self._encode_agent_outputs(agent_outputs)
            
            # If model is trained, use it
            if self.model is not None:
                return self._ensemble_with_model(encoded_features, agent_outputs)
            else:
                # Fallback to weighted voting
                return self._ensemble_with_voting(agent_outputs)
        
        except Exception as e:
            logger.error(f"Error in ensemble: {e}")
            # Return safe default
            return {
                "signal": "NO_SIGNAL",
                "confidence": 0.0,
                "probabilities": {},
                "reasoning": f"Ensemble error: {str(e)}",
                "method": "error_fallback"
            }
    
    def _encode_agent_outputs(self, agent_outputs: Dict[str, Dict[str, Any]]) -> np.ndarray:
        """
        Encode agent outputs to numerical feature vector.
        
        Args:
            agent_outputs: Dictionary of agent outputs
        
        Returns:
            Numpy array of encoded features (shape: 1 x n_features)
        """
        features = []
        
        # Expected agents
        agents = ["quant", "sentiment", "regime", "risk"]
        
        for agent_name in agents:
            agent_output = agent_outputs.get(agent_name, {})
            
            # Extract signal and confidence
            signal = agent_output.get("signal", "HOLD")
            confidence = agent_output.get("confidence", 0.0)
            
            # Encode signal as numerical value
            if agent_name == "risk":
                # Risk agent outputs APPROVE/REJECT
                signal_value = 1.0 if signal == "APPROVE" else -1.0
            else:
                # Trading signals
                signal_value = self.SIGNAL_TYPES.get(signal, 2) - 2  # Center around 0 (-2 to +2)
            
            # Add signal value and confidence
            features.append(signal_value)
            features.append(confidence)
        
        # Shape: 1 x 8 (4 agents * 2 features each)
        return np.array(features).reshape(1, -1)
    
    def _ensemble_with_model(
        self, 
        encoded_features: np.ndarray,
        agent_outputs: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Ensemble using trained meta-learner model.
        
        Args:
            encoded_features: Encoded agent outputs
            agent_outputs: Original agent outputs
        
        Returns:
            Final signal with confidence and probabilities
        """
        try:
            # Predict probabilities
            probabilities = self.model.predict_proba(encoded_features)[0]
            
            # Predict class
            prediction = self.model.predict(encoded_features)[0]
            
            # Get confidence (max probability)
            confidence = float(probabilities.max())
            
            # Map prediction to signal type
            final_signal = self.SIGNAL_TYPES_REVERSE.get(prediction, "HOLD")
            
            # Build probability distribution
            prob_dist = {
                signal_type: float(probabilities[idx])
                for idx, signal_type in enumerate(self.SIGNAL_TYPES.keys())
            }
            
            # Check risk approval
            risk_output = agent_outputs.get("risk", {})
            risk_approved = risk_output.get("signal") == "APPROVE"
            
            if not risk_approved and final_signal in ["BUY", "STRONG_BUY"]:
                # Risk rejected - downgrade signal
                logger.warning(f"Risk agent rejected signal. Downgrading to NO_SIGNAL.")
                return {
                    "signal": "NO_SIGNAL",
                    "confidence": 0.0,
                    "probabilities": prob_dist,
                    "reasoning": "Risk agent rejected signal",
                    "method": "meta_model_with_risk_veto",
                    "original_signal": final_signal,
                    "original_confidence": confidence
                }
            
            return {
                "signal": final_signal,
                "confidence": confidence,
                "probabilities": prob_dist,
                "reasoning": "Meta-learner ensemble prediction",
                "method": "meta_model"
            }
        
        except Exception as e:
            logger.error(f"Error in model ensemble: {e}")
            return self._ensemble_with_voting(agent_outputs)
    
    def _ensemble_with_voting(self, agent_outputs: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        Fallback ensemble using weighted voting.
        
        Args:
            agent_outputs: Dictionary of agent outputs
        
        Returns:
            Final signal with confidence
        """
        try:
            # Agent weights (can be tuned)
            weights = {
                "quant": 0.35,      # Quantitative analysis
                "sentiment": 0.20,  # Sentiment analysis
                "regime": 0.25,     # Regime detection
                "risk": 0.20        # Risk management
            }
            
            # Collect weighted votes
            vote_scores = {signal: 0.0 for signal in self.SIGNAL_TYPES.keys()}
            total_weight = 0.0
            
            for agent_name, agent_output in agent_outputs.items():
                if agent_name not in weights:
                    continue
                
                signal = agent_output.get("signal", "HOLD")
                confidence = agent_output.get("confidence", 0.0)
                weight = weights[agent_name]
                
                # Handle risk agent (APPROVE/REJECT)
                if agent_name == "risk":
                    if signal != "APPROVE":
                        # Risk veto - return NO_SIGNAL
                        return {
                            "signal": "NO_SIGNAL",
                            "confidence": 0.0,
                            "probabilities": {},
                            "reasoning": "Risk agent rejected signal",
                            "method": "voting_with_risk_veto"
                        }
                    continue  # Risk doesn't vote for signal type
                
                # Add weighted vote
                if signal in vote_scores:
                    vote_scores[signal] += weight * confidence
                    total_weight += weight
            
            # Normalize scores
            if total_weight > 0:
                for signal in vote_scores:
                    vote_scores[signal] /= total_weight
            
            # Find winning signal
            winning_signal = max(vote_scores, key=vote_scores.get)
            winning_confidence = vote_scores[winning_signal]
            
            return {
                "signal": winning_signal,
                "confidence": winning_confidence,
                "probabilities": vote_scores,
                "reasoning": "Weighted voting ensemble",
                "method": "voting"
            }
        
        except Exception as e:
            logger.error(f"Error in voting ensemble: {e}")
            return {
                "signal": "NO_SIGNAL",
                "confidence": 0.0,
                "probabilities": {},
                "reasoning": f"Voting error: {str(e)}",
                "method": "error_fallback"
            }
    
    def train_meta_learner(
        self,
        agent_predictions: np.ndarray,
        true_outcomes: np.ndarray,
        save_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Train meta-learner on historical agent predictions.
        
        Args:
            agent_predictions: Shape (n_samples, 8) - encoded agent signals
            true_outcomes: Shape (n_samples,) - actual outcomes (0-4)
            save_path: Path to save trained model
        
        Returns:
            Training metrics
        """
        try:
            logger.info(f"Training meta-learner on {len(agent_predictions)} samples...")
            
            # Create base logistic regression model
            base_model = LogisticRegression(
                multi_class='multinomial',
                max_iter=1000,
                random_state=42,
                class_weight='balanced'  # Handle class imbalance
            )
            
            # Calibrate probabilities using Platt scaling
            meta_model = CalibratedClassifierCV(
                base_model,
                method='sigmoid',  # Platt scaling
                cv=5,  # 5-fold cross-validation
                n_jobs=-1
            )
            
            # Train model
            meta_model.fit(agent_predictions, true_outcomes)
            
            # Calculate training accuracy
            train_accuracy = meta_model.score(agent_predictions, true_outcomes)
            
            # Save model
            save_path = save_path or self.model_path
            Path(save_path).parent.mkdir(parents=True, exist_ok=True)
            joblib.dump(meta_model, save_path)
            
            # Update instance model
            self.model = meta_model
            
            logger.info(f"Meta-learner trained successfully. Accuracy: {train_accuracy:.3f}")
            logger.info(f"Model saved to {save_path}")
            
            return {
                "status": "success",
                "samples": len(agent_predictions),
                "train_accuracy": float(train_accuracy),
                "model_path": save_path,
                "trained_at": datetime.now().isoformat()
            }
        
        except Exception as e:
            logger.error(f"Error training meta-learner: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def reload_model(self):
        """Reload meta-learner model from disk."""
        self._load_model()


# Singleton instance
meta_decision_engine = MetaDecisionEngine()
