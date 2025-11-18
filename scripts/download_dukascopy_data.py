#!/usr/bin/env python3
"""
Download Historical Data from Dukascopy
Free tick-level forex data, converts to OHLC candles, stores in QuestDB
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import requests
import struct
import lzma
from io import BytesIO
from typing import List, Optional
import yaml
from loguru import logger
import psycopg2
from tqdm import tqdm
import asyncio
import aiohttp
from concurrent.futures import ThreadPoolExecutor
import time


class DukascopyDownloader:
    """
    Download historical forex data from Dukascopy

    Dukascopy provides free tick data for:
    - All major forex pairs
    - Precious metals (Gold, Silver)
    - Indices (limited)
    """

    BASE_URL = "https://datafeed.dukascopy.com/datafeed"

    # Dukascopy instrument mappings
    INSTRUMENTS = {
        # Major Forex
        'EUR_USD': 'EURUSD',
        'GBP_USD': 'GBPUSD',
        'USD_JPY': 'USDJPY',
        'USD_CHF': 'USDCHF',
        'AUD_USD': 'AUDUSD',
        'NZD_USD': 'NZDUSD',
        'USD_CAD': 'USDCAD',

        # Minor Forex
        'EUR_GBP': 'EURGBP',
        'EUR_JPY': 'EURJPY',
        'GBP_JPY': 'GBPJPY',
        'AUD_JPY': 'AUDJPY',
        'EUR_CHF': 'EURCHF',
        'GBP_CHF': 'GBPCHF',

        # Metals
        'XAU_USD': 'XAUUSD',
        'XAG_USD': 'XAGUSD',
    }

    def __init__(self, config_path: str = "config/settings.yaml", max_concurrent: int = 50):
        with open(config_path) as f:
            self.config = yaml.safe_load(f)

        # QuestDB connection
        db_config = self.config.get('database', {}).get('questdb', {})
        self.questdb_host = db_config.get('host', 'questdb')
        self.questdb_port = db_config.get('pg_port', 8812)

        # Concurrency settings
        self.max_concurrent = max_concurrent  # Download up to 50 hours simultaneously
        self.session = None

        logger.info("Dukascopy Downloader initialized")
        logger.info(f"QuestDB: {self.questdb_host}:{self.questdb_port}")
        logger.info(f"Max concurrent downloads: {max_concurrent}")

    def get_available_symbols(self) -> List[str]:
        """Get symbols that Dukascopy supports from config"""
        config_symbols = self.config.get('trading', {}).get('symbols', [])

        # Filter to only Dukascopy-supported instruments
        available = [s for s in config_symbols if s in self.INSTRUMENTS]

        logger.info(f"Dukascopy supports {len(available)}/{len(config_symbols)} configured symbols")
        return available

    def download_hour(
        self,
        instrument: str,
        year: int,
        month: int,
        day: int,
        hour: int
    ) -> Optional[pd.DataFrame]:
        """
        Download one hour of tick data from Dukascopy

        Returns DataFrame with columns: timestamp, ask, bid, ask_volume, bid_volume
        """
        # Convert OANDA format to Dukascopy format
        duka_instrument = self.INSTRUMENTS.get(instrument)
        if not duka_instrument:
            return None

        # Build URL
        # Format: {BASE_URL}/{INSTRUMENT}/{YEAR}/{MONTH-1}/{DAY}/{HOUR}h_ticks.bi5
        url = (
            f"{self.BASE_URL}/{duka_instrument}/"
            f"{year:04d}/{month-1:02d}/{day:02d}/{hour:02d}h_ticks.bi5"
        )

        try:
            response = requests.get(url, timeout=30)

            if response.status_code == 404:
                return None  # No data for this hour

            response.raise_for_status()

            # Decompress LZMA data
            decompressed = lzma.decompress(response.content)

            # Parse binary tick data
            # Format: 20 bytes per tick
            # - 4 bytes: timestamp (ms since hour start)
            # - 4 bytes: ask price
            # - 4 bytes: bid price
            # - 4 bytes: ask volume
            # - 4 bytes: bid volume

            ticks = []
            offset = 0

            while offset < len(decompressed):
                # Read 20 bytes
                tick_data = struct.unpack('>IIIff', decompressed[offset:offset+20])

                ms_offset = tick_data[0]
                ask = tick_data[1] / 100000.0  # Point value
                bid = tick_data[2] / 100000.0
                ask_vol = tick_data[3]
                bid_vol = tick_data[4]

                # Calculate absolute timestamp
                hour_start = datetime(year, month, day, hour)
                timestamp = hour_start + timedelta(milliseconds=ms_offset)

                ticks.append({
                    'timestamp': timestamp,
                    'ask': ask,
                    'bid': bid,
                    'ask_volume': ask_vol,
                    'bid_volume': bid_vol
                })

                offset += 20

            if not ticks:
                return None

            return pd.DataFrame(ticks)

        except requests.exceptions.RequestException as e:
            logger.debug(f"Download failed for {instrument} {year}-{month:02d}-{day:02d} {hour:02d}h: {e}")
            return None
        except Exception as e:
            logger.error(f"Parse error for {instrument}: {e}")
            return None

    async def download_hour_async(
        self,
        session: aiohttp.ClientSession,
        instrument: str,
        year: int,
        month: int,
        day: int,
        hour: int
    ) -> tuple:
        """
        Download one hour of tick data asynchronously
        Returns tuple: (hour_info, DataFrame or None)
        """
        duka_instrument = self.INSTRUMENTS.get(instrument)
        if not duka_instrument:
            return ((year, month, day, hour), None)

        url = (
            f"{self.BASE_URL}/{duka_instrument}/"
            f"{year:04d}/{month-1:02d}/{day:02d}/{hour:02d}h_ticks.bi5"
        )

        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                if response.status == 404:
                    return ((year, month, day, hour), None)

                response.raise_for_status()
                content = await response.read()

                # Decompress LZMA data
                decompressed = lzma.decompress(content)

                # Parse binary tick data
                ticks = []
                offset = 0

                while offset < len(decompressed):
                    tick_data = struct.unpack('>IIIff', decompressed[offset:offset+20])

                    ms_offset = tick_data[0]
                    ask = tick_data[1] / 100000.0
                    bid = tick_data[2] / 100000.0
                    ask_vol = tick_data[3]
                    bid_vol = tick_data[4]

                    hour_start = datetime(year, month, day, hour)
                    timestamp = hour_start + timedelta(milliseconds=ms_offset)

                    ticks.append({
                        'timestamp': timestamp,
                        'ask': ask,
                        'bid': bid,
                        'ask_volume': ask_vol,
                        'bid_volume': bid_vol
                    })

                    offset += 20

                if not ticks:
                    return ((year, month, day, hour), None)

                return ((year, month, day, hour), pd.DataFrame(ticks))

        except Exception:
            return ((year, month, day, hour), None)

    def ticks_to_candles(
        self,
        ticks: pd.DataFrame,
        timeframe: str = '15T'
    ) -> pd.DataFrame:
        """
        Convert tick data to OHLC candles

        Args:
            ticks: DataFrame with timestamp, ask, bid
            timeframe: Pandas frequency string (e.g., '15T' = 15 minutes)

        Returns:
            DataFrame with OHLC candles
        """
        if ticks.empty:
            return pd.DataFrame()

        # Use mid price (average of bid/ask)
        ticks['mid'] = (ticks['ask'] + ticks['bid']) / 2.0
        ticks['volume'] = ticks['ask_volume'] + ticks['bid_volume']

        # Set timestamp as index
        ticks.set_index('timestamp', inplace=True)

        # Resample to timeframe
        ohlc = ticks['mid'].resample(timeframe).ohlc()
        volume = ticks['volume'].resample(timeframe).sum()

        # Combine
        ohlc['volume'] = volume
        ohlc = ohlc.dropna()

        # Rename columns
        ohlc.columns = ['open', 'high', 'low', 'close', 'volume']

        return ohlc.reset_index()

    async def download_symbol_async(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        timeframe: str = '15T'
    ) -> pd.DataFrame:
        """
        Download historical data for a symbol using concurrent downloads

        Args:
            symbol: OANDA symbol (e.g., 'EUR_USD')
            start_date: Start date
            end_date: End date
            timeframe: Candle timeframe (default 15 minutes)

        Returns:
            DataFrame with OHLC candles
        """
        logger.info(f"Downloading {symbol} from {start_date.date()} to {end_date.date()}")

        # Generate all hours to download
        hours_to_download = []
        current = start_date
        while current < end_date:
            hours_to_download.append((current.year, current.month, current.day, current.hour))
            current += timedelta(hours=1)

        total_hours = len(hours_to_download)
        logger.info(f"Total hours to download: {total_hours:,}")

        # Create aiohttp session with connection pooling
        connector = aiohttp.TCPConnector(limit=self.max_concurrent, limit_per_host=self.max_concurrent)
        timeout = aiohttp.ClientTimeout(total=60, connect=10)

        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            # Create download tasks
            tasks = []
            for year, month, day, hour in hours_to_download:
                task = self.download_hour_async(session, symbol, year, month, day, hour)
                tasks.append(task)

            # Download with progress bar
            all_ticks = []
            completed = 0

            with tqdm(total=total_hours, desc=f"Downloading {symbol}") as pbar:
                # Process in batches to avoid overwhelming memory
                batch_size = self.max_concurrent * 10  # Process 500 hours at a time
                for i in range(0, len(tasks), batch_size):
                    batch = tasks[i:i + batch_size]
                    results = await asyncio.gather(*batch)

                    for hour_info, ticks_df in results:
                        if ticks_df is not None and not ticks_df.empty:
                            all_ticks.append(ticks_df)
                        completed += 1
                        pbar.update(1)

        if not all_ticks:
            logger.warning(f"No data downloaded for {symbol}")
            return pd.DataFrame()

        # Combine all ticks
        ticks_df = pd.concat(all_ticks, ignore_index=True)
        ticks_df.sort_values('timestamp', inplace=True)

        logger.success(f"Downloaded {len(ticks_df):,} ticks for {symbol}")

        # Convert to candles
        candles = self.ticks_to_candles(ticks_df, timeframe)

        logger.success(f"Created {len(candles):,} {timeframe} candles for {symbol}")

        return candles

    def download_symbol(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime,
        timeframe: str = '15T'
    ) -> pd.DataFrame:
        """
        Synchronous wrapper for async download method

        Args:
            symbol: OANDA symbol (e.g., 'EUR_USD')
            start_date: Start date
            end_date: End date
            timeframe: Candle timeframe (default 15 minutes)

        Returns:
            DataFrame with OHLC candles
        """
        return asyncio.run(self.download_symbol_async(symbol, start_date, end_date, timeframe))

    def save_to_questdb(
        self,
        symbol: str,
        candles: pd.DataFrame
    ):
        """
        Save candles to QuestDB

        Creates market_data table if it doesn't exist
        """
        if candles.empty:
            return

        try:
            # Connect to QuestDB
            conn = psycopg2.connect(
                host=self.questdb_host,
                port=self.questdb_port,
                user='admin',
                password='quest',
                database='qdb'
            )
            cursor = conn.cursor()

            # Create table if not exists
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS market_data (
                    timestamp TIMESTAMP,
                    symbol SYMBOL,
                    open DOUBLE,
                    high DOUBLE,
                    low DOUBLE,
                    close DOUBLE,
                    volume DOUBLE
                ) TIMESTAMP(timestamp) PARTITION BY DAY;
            """)
            conn.commit()

            # Insert data
            rows_inserted = 0

            for _, row in candles.iterrows():
                cursor.execute("""
                    INSERT INTO market_data (timestamp, symbol, open, high, low, close, volume)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (
                    row['timestamp'],
                    symbol,
                    row['open'],
                    row['high'],
                    row['low'],
                    row['close'],
                    row['volume']
                ))
                rows_inserted += 1

            conn.commit()
            cursor.close()
            conn.close()

            logger.success(f"✓ Saved {rows_inserted:,} candles for {symbol} to QuestDB")

        except Exception as e:
            logger.error(f"✗ Failed to save {symbol} to QuestDB: {e}")

    def download_all(
        self,
        start_date: datetime,
        end_date: datetime,
        timeframe: str = '15T'
    ):
        """
        Download all supported symbols

        Args:
            start_date: Start date
            end_date: End date
            timeframe: Candle timeframe (default 15 minutes)
        """
        symbols = self.get_available_symbols()

        logger.info(f"Starting download for {len(symbols)} symbols")
        logger.info(f"Date range: {start_date.date()} to {end_date.date()}")
        logger.info(f"Timeframe: {timeframe}")

        results = {}

        for i, symbol in enumerate(symbols, 1):
            logger.info(f"\n[{i}/{len(symbols)}] Processing {symbol}")

            # Download
            candles = self.download_symbol(
                symbol,
                start_date,
                end_date,
                timeframe
            )

            if not candles.empty:
                # Save to QuestDB
                self.save_to_questdb(symbol, candles)
                results[symbol] = len(candles)
            else:
                logger.warning(f"No data for {symbol}")
                results[symbol] = 0

        # Summary
        logger.info("\n" + "="*60)
        logger.info("DOWNLOAD SUMMARY")
        logger.info("="*60)

        total_candles = sum(results.values())
        successful = sum(1 for v in results.values() if v > 0)

        logger.info(f"Symbols processed: {len(symbols)}")
        logger.info(f"Successful: {successful}")
        logger.info(f"Total candles: {total_candles:,}")

        logger.info("\nPer-symbol breakdown:")
        for symbol, count in sorted(results.items(), key=lambda x: -x[1]):
            if count > 0:
                logger.info(f"  {symbol:12s}: {count:6,} candles")

        logger.info("="*60)


if __name__ == "__main__":
    print("="*60)
    print("  ATHENA-X: Dukascopy Historical Data Downloader")
    print("="*60)
    print()

    downloader = DukascopyDownloader()

    # Download last 2 years
    end_date = datetime.now()
    start_date = end_date - timedelta(days=730)  # 2 years

    print(f"Downloading historical data:")
    print(f"  Start: {start_date.date()}")
    print(f"  End: {end_date.date()}")
    print(f"  Timeframe: 15 minutes")
    print(f"  Concurrent downloads: {downloader.max_concurrent}")
    print()
    print("⚡ Using concurrent downloads - This should take 5-15 minutes with fast internet!")
    print()

    # Ask for confirmation
    response = input("Continue? (y/N): ")
    if response.lower() != 'y':
        print("Cancelled.")
        exit(0)

    print()

    # Download
    downloader.download_all(
        start_date=start_date,
        end_date=end_date,
        timeframe='15T'  # 15 minutes
    )

    print()
    print("="*60)
    print("✓ Download Complete!")
    print("="*60)
    print()
    print("Next steps:")
    print("  1. Run Phase 4 training: python scripts/export_questdb_training_data.py")
    print("  2. Or deploy immediately: python scripts/deploy.py --mode paper")
