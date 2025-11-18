"""
Phase 4.1: Historical Data Collection Script
Downloads historical forex data for model training
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict
import yaml
from loguru import logger


class HistoricalDataCollector:
    """Collect historical data for model training"""

    def __init__(self, config_path: str = "config/settings.yaml"):
        with open(config_path) as f:
            self.config = yaml.safe_load(f)

    def collect_forex_data(
        self,
        pairs: List[str],
        start_date: str = "2019-01-01",
        end_date: str = "2024-12-31",
        granularity: str = "H1"
    ) -> Dict[str, pd.DataFrame]:
        """
        Collect historical forex data

        Args:
            pairs: List of currency pairs (e.g., ['EUR_USD', 'GBP_USD'])
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            granularity: Timeframe (M1, M5, M15, H1, H4, D)

        Returns:
            Dictionary of DataFrames with OHLCV data
        """

        logger.info(f"Collecting data for {len(pairs)} pairs from {start_date} to {end_date}")

        data = {}

        for pair in pairs:
            logger.info(f"Downloading {pair}...")

            # Use yfinance as fallback if OANDA not available
            try:
                import yfinance as yf

                # Convert pair format: EUR_USD -> EURUSD=X
                symbol = pair.replace('_', '') + '=X'

                df = yf.download(
                    symbol,
                    start=start_date,
                    end=end_date,
                    interval=self._convert_granularity(granularity),
                    progress=False
                )

                if not df.empty:
                    data[pair] = df
                    logger.success(f"✓ {pair}: {len(df)} candles")
                else:
                    logger.warning(f"✗ {pair}: No data available")

            except Exception as e:
                logger.error(f"✗ {pair}: {e}")

        logger.info(f"Collected data for {len(data)}/{len(pairs)} pairs")
        return data

    def _convert_granularity(self, gran: str) -> str:
        """Convert OANDA granularity to yfinance interval"""
        mapping = {
            'M1': '1m',
            'M5': '5m',
            'M15': '15m',
            'M30': '30m',
            'H1': '1h',
            'H4': '4h',
            'D': '1d',
            'W': '1wk',
            'M': '1mo'
        }
        return mapping.get(gran, '1h')

    def add_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add technical indicators to OHLCV data"""

        # Simple Moving Averages
        df['SMA_20'] = df['Close'].rolling(20).mean()
        df['SMA_50'] = df['Close'].rolling(50).mean()
        df['SMA_200'] = df['Close'].rolling(200).mean()

        # Exponential Moving Averages
        df['EMA_20'] = df['Close'].ewm(span=20).mean()
        df['EMA_50'] = df['Close'].ewm(span=50).mean()

        # RSI
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))

        # MACD
        ema_12 = df['Close'].ewm(span=12).mean()
        ema_26 = df['Close'].ewm(span=26).mean()
        df['MACD'] = ema_12 - ema_26
        df['MACD_Signal'] = df['MACD'].ewm(span=9).mean()

        # Bollinger Bands
        df['BB_Middle'] = df['Close'].rolling(20).mean()
        std = df['Close'].rolling(20).std()
        df['BB_Upper'] = df['BB_Middle'] + (2 * std)
        df['BB_Lower'] = df['BB_Middle'] - (2 * std)

        # ATR (Average True Range)
        high_low = df['High'] - df['Low']
        high_close = abs(df['High'] - df['Close'].shift())
        low_close = abs(df['Low'] - df['Close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = ranges.max(axis=1)
        df['ATR'] = true_range.rolling(14).mean()

        # Volume-based indicators
        if 'Volume' in df.columns:
            df['Volume_SMA'] = df['Volume'].rolling(20).mean()
            df['Volume_Ratio'] = df['Volume'] / df['Volume_SMA']

        return df

    def create_regime_labels(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Create regime labels for HMM training

        Regimes:
        0 = Bear (downtrend)
        1 = Sideways (ranging)
        2 = Bull (uptrend)
        """

        # Calculate returns
        df['Returns'] = df['Close'].pct_change()

        # Calculate trend strength
        df['Trend'] = (df['SMA_20'] - df['SMA_50']) / df['SMA_50']

        # Simple regime classification (can be improved)
        conditions = [
            df['Trend'] < -0.01,  # Strong downtrend
            (df['Trend'] >= -0.01) & (df['Trend'] <= 0.01),  # Sideways
            df['Trend'] > 0.01  # Strong uptrend
        ]

        df['Regime'] = np.select(conditions, [0, 1, 2], default=1)

        return df

    def save_training_data(self, data: Dict[str, pd.DataFrame], output_dir: str = "data/training"):
        """Save processed data for training"""

        import os
        os.makedirs(output_dir, exist_ok=True)

        for pair, df in data.items():
            # Add indicators
            df = self.add_technical_indicators(df)
            df = self.create_regime_labels(df)

            # Remove NaN values
            df = df.dropna()

            # Save
            output_path = f"{output_dir}/{pair}_training.csv"
            df.to_csv(output_path)
            logger.success(f"✓ Saved {pair} to {output_path} ({len(df)} rows)")


if __name__ == "__main__":
    # Example usage
    collector = HistoricalDataCollector()

    # Collect data for major pairs
    pairs = ['EUR_USD', 'GBP_USD', 'USD_JPY', 'AUD_USD']

    print("Collecting historical data...")
    data = collector.collect_forex_data(
        pairs=pairs,
        start_date="2020-01-01",
        end_date="2024-12-31",
        granularity="H1"
    )

    print("\nSaving training data...")
    collector.save_training_data(data)

    print("\n✓ Phase 4.1 Complete: Data collection finished")
    print(f"Training data saved to: data/training/")
