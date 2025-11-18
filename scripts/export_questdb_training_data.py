#!/usr/bin/env python3
"""
Phase 4.1: Export Training Data from QuestDB
Exports historical market data from QuestDB for model training
"""

import psycopg2
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict
import yaml
from pathlib import Path
from loguru import logger


class QuestDBExporter:
    """Export training data from QuestDB"""

    def __init__(self, config_path: str = "config/settings.yaml"):
        with open(config_path) as f:
            self.config = yaml.safe_load(f)

        # QuestDB connection (PostgreSQL wire protocol)
        db_config = self.config.get('database', {}).get('questdb', {})
        self.host = db_config.get('host', 'localhost')
        self.port = db_config.get('pg_port', 8812)

        logger.info(f"QuestDB Exporter initialized: {self.host}:{self.port}")

    def connect(self):
        """Connect to QuestDB via PostgreSQL wire protocol"""
        try:
            conn = psycopg2.connect(
                host=self.host,
                port=self.port,
                user='admin',
                password='quest',
                database='qdb'
            )
            logger.success(f"✓ Connected to QuestDB")
            return conn

        except Exception as e:
            logger.error(f"✗ Failed to connect to QuestDB: {e}")
            raise

    def get_available_symbols(self) -> List[str]:
        """Get list of symbols with data in QuestDB"""
        conn = self.connect()
        cursor = conn.cursor()

        try:
            # Query for unique symbols in market_data table
            cursor.execute("""
                SELECT DISTINCT symbol
                FROM market_data
                ORDER BY symbol
            """)

            symbols = [row[0] for row in cursor.fetchall()]
            logger.info(f"Found {len(symbols)} symbols with data")
            return symbols

        except Exception as e:
            logger.warning(f"Could not get symbols: {e}")
            return []

        finally:
            cursor.close()
            conn.close()

    def export_symbol_data(
        self,
        symbol: str,
        start_date: str = None,
        end_date: str = None,
        min_candles: int = 1000
    ) -> pd.DataFrame:
        """
        Export OHLCV data for a symbol

        Args:
            symbol: Trading symbol (e.g., 'EUR_USD')
            start_date: Start date (YYYY-MM-DD) or None for all data
            end_date: End date (YYYY-MM-DD) or None for today
            min_candles: Minimum candles required

        Returns:
            DataFrame with OHLCV data
        """
        conn = self.connect()

        # Build query
        query = f"""
            SELECT
                timestamp,
                open,
                high,
                low,
                close,
                volume
            FROM market_data
            WHERE symbol = '{symbol}'
        """

        if start_date:
            query += f" AND timestamp >= '{start_date}'"

        if end_date:
            query += f" AND timestamp <= '{end_date}'"

        query += " ORDER BY timestamp"

        try:
            df = pd.read_sql(query, conn, parse_dates=['timestamp'])

            if len(df) < min_candles:
                logger.warning(
                    f"{symbol}: Only {len(df)} candles (< {min_candles} minimum)"
                )
                return pd.DataFrame()

            # Rename columns to standard format
            df.columns = ['timestamp', 'Open', 'High', 'Low', 'Close', 'Volume']
            df.set_index('timestamp', inplace=True)

            logger.success(f"✓ {symbol}: {len(df)} candles exported")
            return df

        except Exception as e:
            logger.error(f"✗ {symbol}: Export failed - {e}")
            return pd.DataFrame()

        finally:
            conn.close()

    def add_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add technical indicators for training"""

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
        if 'Volume' in df.columns and df['Volume'].sum() > 0:
            df['Volume_SMA'] = df['Volume'].rolling(20).mean()
            df['Volume_Ratio'] = df['Volume'] / df['Volume_SMA']
        else:
            df['Volume_SMA'] = 0
            df['Volume_Ratio'] = 1

        # Price momentum
        df['Returns'] = df['Close'].pct_change()
        df['Returns_5'] = df['Close'].pct_change(5)
        df['Returns_20'] = df['Close'].pct_change(20)

        # Trend strength
        df['Trend'] = (df['SMA_20'] - df['SMA_50']) / df['SMA_50']

        return df

    def create_regime_labels(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Create regime labels for HMM training

        Regimes:
        0 = Bear (downtrend)
        1 = Sideways (ranging)
        2 = Bull (uptrend)
        """

        # Simple regime classification based on trend
        conditions = [
            df['Trend'] < -0.01,  # Strong downtrend
            (df['Trend'] >= -0.01) & (df['Trend'] <= 0.01),  # Sideways
            df['Trend'] > 0.01  # Strong uptrend
        ]

        df['Regime'] = np.select(conditions, [0, 1, 2], default=1)

        # Add regime strength
        df['Regime_Strength'] = abs(df['Trend'])

        # Volatility regime (using ATR)
        atr_median = df['ATR'].rolling(100).median()
        df['Volatility_Regime'] = np.where(
            df['ATR'] > atr_median * 1.5,
            'HIGH',
            np.where(df['ATR'] < atr_median * 0.5, 'LOW', 'NORMAL')
        )

        return df

    def create_trading_labels(self, df: pd.DataFrame, forward_window: int = 20) -> pd.DataFrame:
        """
        Create labels for supervised learning

        Labels:
        1 = BUY (price will go up)
        0 = HOLD (price will stay flat)
        -1 = SELL (price will go down)
        """

        # Calculate forward returns
        df['Forward_Return'] = df['Close'].pct_change(forward_window).shift(-forward_window)

        # Create labels
        threshold = 0.005  # 0.5% threshold
        conditions = [
            df['Forward_Return'] > threshold,  # UP
            df['Forward_Return'] < -threshold,  # DOWN
        ]

        df['Label'] = np.select(conditions, [1, -1], default=0)

        return df

    def export_all_symbols(
        self,
        output_dir: str = "data/training",
        start_date: str = None,
        end_date: str = None
    ) -> Dict[str, pd.DataFrame]:
        """
        Export all symbols from QuestDB

        Args:
            output_dir: Directory to save CSV files
            start_date: Start date filter
            end_date: End date filter

        Returns:
            Dictionary of DataFrames
        """
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        # Get available symbols
        symbols = self.get_available_symbols()

        if not symbols:
            logger.warning("No symbols found in QuestDB")
            # Try config symbols as fallback
            symbols = self.config.get('trading', {}).get('symbols', [])
            logger.info(f"Using config symbols: {len(symbols)} symbols")

        training_data = {}

        for symbol in symbols:
            logger.info(f"\nProcessing {symbol}...")

            # Export OHLCV data
            df = self.export_symbol_data(
                symbol,
                start_date=start_date,
                end_date=end_date
            )

            if df.empty:
                continue

            # Add indicators
            df = self.add_technical_indicators(df)

            # Add regime labels
            df = self.create_regime_labels(df)

            # Add trading labels
            df = self.create_trading_labels(df)

            # Remove NaN values
            df = df.dropna()

            if len(df) < 500:
                logger.warning(f"{symbol}: Only {len(df)} rows after cleaning (skipping)")
                continue

            # Save to CSV
            output_path = Path(output_dir) / f"{symbol}_training.csv"
            df.to_csv(output_path)
            logger.success(f"✓ Saved {symbol} to {output_path} ({len(df)} rows)")

            training_data[symbol] = df

        return training_data

    def generate_statistics(self, training_data: Dict[str, pd.DataFrame]):
        """Generate statistics summary"""

        logger.info("\n" + "=" * 60)
        logger.info("TRAINING DATA SUMMARY")
        logger.info("=" * 60)

        total_rows = sum(len(df) for df in training_data.values())
        logger.info(f"Total symbols: {len(training_data)}")
        logger.info(f"Total rows: {total_rows:,}")

        logger.info("\nPer-symbol breakdown:")
        for symbol, df in training_data.items():
            date_range = f"{df.index.min()} to {df.index.max()}"
            logger.info(f"  {symbol:12s}: {len(df):6,} rows | {date_range}")

        # Regime distribution
        logger.info("\nRegime Distribution:")
        all_regimes = pd.concat([df['Regime'] for df in training_data.values()])
        regime_counts = all_regimes.value_counts().sort_index()
        total = len(all_regimes)

        logger.info(f"  Bear (0):     {regime_counts.get(0, 0):6,} ({regime_counts.get(0, 0)/total:.1%})")
        logger.info(f"  Sideways (1): {regime_counts.get(1, 0):6,} ({regime_counts.get(1, 0)/total:.1%})")
        logger.info(f"  Bull (2):     {regime_counts.get(2, 0):6,} ({regime_counts.get(2, 0)/total:.1%})")

        # Label distribution
        logger.info("\nTrading Label Distribution:")
        all_labels = pd.concat([df['Label'] for df in training_data.values()])
        label_counts = all_labels.value_counts().sort_index()
        total = len(all_labels)

        logger.info(f"  SELL (-1): {label_counts.get(-1, 0):6,} ({label_counts.get(-1, 0)/total:.1%})")
        logger.info(f"  HOLD (0):  {label_counts.get(0, 0):6,} ({label_counts.get(0, 0)/total:.1%})")
        logger.info(f"  BUY (1):   {label_counts.get(1, 0):6,} ({label_counts.get(1, 0)/total:.1%})")

        logger.info("=" * 60)


if __name__ == "__main__":
    print("=" * 60)
    print("  ATHENA-X Phase 4.1: Export Training Data from QuestDB")
    print("=" * 60)
    print()

    exporter = QuestDBExporter()

    # Export last 2 years of data
    end_date = datetime.now()
    start_date = end_date - timedelta(days=730)  # 2 years

    print(f"Exporting data from {start_date.date()} to {end_date.date()}")
    print()

    training_data = exporter.export_all_symbols(
        output_dir="data/training",
        start_date=start_date.strftime("%Y-%m-%d"),
        end_date=end_date.strftime("%Y-%m-%d")
    )

    if training_data:
        print()
        exporter.generate_statistics(training_data)
        print()
        print("✓ Phase 4.1 Complete: Training data exported from QuestDB")
        print(f"  Location: data/training/")
        print(f"  Symbols: {len(training_data)}")
        print(f"  Total rows: {sum(len(df) for df in training_data.values()):,}")
    else:
        print()
        print("✗ No training data exported")
        print()
        print("Possible reasons:")
        print("  1. QuestDB is not running")
        print("  2. No data in market_data table")
        print("  3. Data is not within date range")
        print()
        print("Solutions:")
        print("  1. Start QuestDB: docker-compose up -d questdb")
        print("  2. Run data pipeline to collect data: python scripts/run_data_pipeline.py")
        print("  3. Adjust date range in this script")
