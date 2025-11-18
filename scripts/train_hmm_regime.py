#!/usr/bin/env python3
"""
Phase 4.3: Train HMM Regime Detection Model
Uses historical data to train Hidden Markov Model for market regime detection
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List
import pickle
import yaml
from loguru import logger

try:
    from hmmlearn import hmm
    HMM_AVAILABLE = True
except ImportError:
    HMM_AVAILABLE = False
    logger.warning("hmmlearn not installed - will use fallback method")


class HMMRegimeTrainer:
    """Train HMM for market regime detection"""

    def __init__(self, config_path: str = "config/settings.yaml"):
        with open(config_path) as f:
            self.config = yaml.safe_load(f)

        self.n_regimes = self.config.get('models', {}).get('regime_detection', {}).get('n_regimes', 3)
        self.models = {}

        logger.info(f"HMM Regime Trainer initialized: {self.n_regimes} regimes")

    def load_training_data(self, data_dir: str = "data/training") -> Dict[str, pd.DataFrame]:
        """Load training data from CSV files"""

        data_path = Path(data_dir)

        if not data_path.exists():
            logger.error(f"Training data directory not found: {data_dir}")
            return {}

        training_data = {}

        for csv_file in data_path.glob("*_training.csv"):
            symbol = csv_file.stem.replace('_training', '')

            try:
                df = pd.read_csv(csv_file, index_col=0, parse_dates=True)
                training_data[symbol] = df
                logger.info(f"Loaded {symbol}: {len(df)} rows")

            except Exception as e:
                logger.error(f"Failed to load {csv_file}: {e}")

        logger.info(f"Loaded {len(training_data)} symbols")
        return training_data

    def prepare_features(self, df: pd.DataFrame) -> np.ndarray:
        """
        Prepare features for HMM training

        Features:
        - Returns (log returns)
        - Volatility (rolling std)
        - Volume ratio
        - Trend (SMA difference)
        """

        features = []

        # Returns
        if 'Returns' in df.columns:
            features.append(df['Returns'].values)
        else:
            features.append(df['Close'].pct_change().values)

        # Volatility (20-period rolling std)
        volatility = df['Close'].pct_change().rolling(20).std()
        features.append(volatility.values)

        # Volume ratio (if available)
        if 'Volume_Ratio' in df.columns and df['Volume_Ratio'].sum() > 0:
            features.append(df['Volume_Ratio'].values)
        else:
            features.append(np.ones(len(df)))

        # Trend
        if 'Trend' in df.columns:
            features.append(df['Trend'].values)
        else:
            sma_20 = df['Close'].rolling(20).mean()
            sma_50 = df['Close'].rolling(50).mean()
            trend = (sma_20 - sma_50) / sma_50
            features.append(trend.values)

        # Stack features
        X = np.column_stack(features)

        # Remove NaN rows
        mask = ~np.isnan(X).any(axis=1)
        X = X[mask]

        return X

    def train_hmm_model(self, X: np.ndarray, n_regimes: int = 3) -> hmm.GaussianHMM:
        """
        Train Gaussian HMM

        Args:
            X: Feature matrix (n_samples, n_features)
            n_regimes: Number of hidden states (regimes)

        Returns:
            Trained HMM model
        """

        if not HMM_AVAILABLE:
            logger.error("hmmlearn not installed. Install with: pip install hmmlearn")
            return None

        logger.info(f"Training HMM with {n_regimes} regimes on {len(X)} samples")

        # Initialize HMM
        model = hmm.GaussianHMM(
            n_components=n_regimes,
            covariance_type="full",
            n_iter=100,
            random_state=42,
            verbose=False
        )

        # Train
        model.fit(X)

        # Log convergence
        logger.info(f"  Converged: {model.monitor_.converged}")
        logger.info(f"  Iterations: {model.monitor_.iter}")
        logger.info(f"  Log likelihood: {model.score(X):.2f}")

        return model

    def predict_regimes(self, model: hmm.GaussianHMM, X: np.ndarray) -> np.ndarray:
        """Predict regimes for given data"""

        if model is None:
            return np.zeros(len(X))

        regimes = model.predict(X)
        return regimes

    def evaluate_model(self, model: hmm.GaussianHMM, X: np.ndarray, df: pd.DataFrame):
        """Evaluate HMM model performance"""

        # Predict regimes
        predicted_regimes = self.predict_regimes(model, X)

        # Align with dataframe (account for NaN removal)
        aligned_df = df[~df[['Returns', 'Trend']].isna().any(axis=1)].copy()
        aligned_df['Predicted_Regime'] = predicted_regimes

        logger.info("\nRegime Statistics:")

        for regime in range(self.n_regimes):
            regime_data = aligned_df[aligned_df['Predicted_Regime'] == regime]

            if len(regime_data) == 0:
                continue

            avg_return = regime_data['Returns'].mean()
            volatility = regime_data['Returns'].std()
            count = len(regime_data)
            pct = count / len(aligned_df)

            logger.info(f"  Regime {regime}:")
            logger.info(f"    Count:      {count:6,} ({pct:.1%})")
            logger.info(f"    Avg Return: {avg_return:+.4%}")
            logger.info(f"    Volatility: {volatility:.4%}")

        return aligned_df

    def train_all_symbols(self, data_dir: str = "data/training") -> Dict[str, hmm.GaussianHMM]:
        """Train HMM for all symbols"""

        # Load data
        training_data = self.load_training_data(data_dir)

        if not training_data:
            logger.error("No training data available")
            return {}

        models = {}

        for symbol, df in training_data.items():
            logger.info(f"\n{'='*60}")
            logger.info(f"Training HMM for {symbol}")
            logger.info(f"{'='*60}")

            # Prepare features
            X = self.prepare_features(df)

            if len(X) < 200:
                logger.warning(f"Insufficient data for {symbol} ({len(X)} samples)")
                continue

            # Train model
            model = self.train_hmm_model(X, n_regimes=self.n_regimes)

            if model is None:
                continue

            # Evaluate
            self.evaluate_model(model, X, df)

            models[symbol] = model

        return models

    def save_models(self, models: Dict[str, hmm.GaussianHMM], output_dir: str = "data/models/hmm"):
        """Save trained HMM models"""

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        for symbol, model in models.items():
            model_file = output_path / f"{symbol}_hmm.pkl"

            with open(model_file, 'wb') as f:
                pickle.dump(model, f)

            logger.success(f"✓ Saved {symbol} HMM to {model_file}")

        # Save metadata
        metadata = {
            'n_regimes': self.n_regimes,
            'symbols': list(models.keys()),
            'trained_at': pd.Timestamp.now().isoformat()
        }

        metadata_file = output_path / "metadata.pkl"
        with open(metadata_file, 'wb') as f:
            pickle.dump(metadata, f)

        logger.success(f"✓ Saved metadata to {metadata_file}")

    def load_model(self, symbol: str, model_dir: str = "data/models/hmm") -> hmm.GaussianHMM:
        """Load trained HMM model for a symbol"""

        model_file = Path(model_dir) / f"{symbol}_hmm.pkl"

        if not model_file.exists():
            logger.error(f"Model not found: {model_file}")
            return None

        with open(model_file, 'rb') as f:
            model = pickle.load(f)

        logger.info(f"Loaded HMM for {symbol}")
        return model


class SimpleFallbackRegimeDetector:
    """
    Fallback regime detector when HMM is not available
    Uses simple trend-based classification
    """

    def __init__(self, n_regimes: int = 3):
        self.n_regimes = n_regimes

    def predict(self, df: pd.DataFrame) -> np.ndarray:
        """Predict regimes using simple trend"""

        if 'Trend' not in df.columns:
            sma_20 = df['Close'].rolling(20).mean()
            sma_50 = df['Close'].rolling(50).mean()
            trend = (sma_20 - sma_50) / sma_50
        else:
            trend = df['Trend']

        # Classify into regimes
        conditions = [
            trend < -0.01,  # Bear
            (trend >= -0.01) & (trend <= 0.01),  # Sideways
            trend > 0.01  # Bull
        ]

        regimes = np.select(conditions, [0, 1, 2], default=1)
        return regimes


if __name__ == "__main__":
    print("=" * 60)
    print("  ATHENA-X Phase 4.3: Train HMM Regime Detection")
    print("=" * 60)
    print()

    if not HMM_AVAILABLE:
        print("⚠️  hmmlearn not installed")
        print("   Install with: pip install hmmlearn")
        print()
        print("   Continuing with fallback method...")
        print()

    trainer = HMMRegimeTrainer()

    # Train HMMs for all symbols
    models = trainer.train_all_symbols(data_dir="data/training")

    if models:
        print()
        print("=" * 60)
        print("TRAINING SUMMARY")
        print("=" * 60)
        print(f"Trained models: {len(models)}")
        print(f"Regimes per model: {trainer.n_regimes}")
        print()

        # Save models
        trainer.save_models(models, output_dir="data/models/hmm")

        print()
        print("✓ Phase 4.3 Complete: HMM models trained and saved")
        print(f"  Location: data/models/hmm/")
        print(f"  Models: {len(models)}")
    else:
        print()
        print("✗ No HMM models trained")
        print()
        print("Possible reasons:")
        print("  1. No training data available")
        print("  2. hmmlearn not installed")
        print()
        print("Solutions:")
        print("  1. Run Phase 4.1 first: python scripts/export_questdb_training_data.py")
        print("  2. Install hmmlearn: pip install hmmlearn")
