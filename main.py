#!/usr/bin/env python3
"""
ATHENA-X Trading System
Main Entry Point
"""

import sys
import time
import yaml
from pathlib import Path
from datetime import datetime
from loguru import logger

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.data.data_pipeline import ATHENADataPipeline
from src.storage.questdb_client import QuestDBClient
from src.storage.redis_cache import RedisCache
from src.storage.postgres_client import PostgreSQLClient
from src.utils.logging import setup_logging
from src.utils.metrics import get_metrics


def load_config(config_path="config/settings.yaml"):
    """Load system configuration"""
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def main():
    """Main entry point"""

    # Load configuration
    config = load_config()

    # Setup logging
    log_config = config.get('monitoring', {}).get('logging', {})
    setup_logging(
        log_level=log_config.get('level', 'INFO'),
        log_dir='logs'
    )

    logger.info("=" * 70)
    logger.info("ATHENA-X Trading System v{}".format(config['system']['version']))
    logger.info("=" * 70)
    logger.info(f"Environment: {config['system']['environment']}")
    logger.info(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 70)

    # Initialize metrics
    metrics_config = config.get('monitoring', {}).get('prometheus', {})
    if metrics_config.get('enabled', True):
        metrics = get_metrics(port=metrics_config.get('port', 8000))
        logger.info(f"Metrics server started on port {metrics_config.get('port', 8000)}")

    # Initialize data pipeline
    logger.info("Initializing data pipeline...")
    try:
        pipeline = ATHENADataPipeline(config)
    except Exception as e:
        logger.error(f"Failed to initialize data pipeline: {str(e)}")
        sys.exit(1)

    # Health check
    logger.info("Running system health check...")
    health = pipeline.health_check()

    for component, status in health.items():
        status_icon = "✅" if status else "❌"
        logger.info(f"  {component:<20} {status_icon}")

    if not any(health.values()):
        logger.error("No data sources available! Check configuration and services.")
        sys.exit(1)

    # Check if in testing mode
    if config['system']['environment'] == 'development':
        logger.info("")
        logger.info("=" * 70)
        logger.info("DEVELOPMENT MODE - Testing Data Pipeline")
        logger.info("=" * 70)

        # Test with configured symbols
        symbols = config.get('trading', {}).get('symbols', ['EUR_USD'])

        for symbol in symbols:
            logger.info(f"\nFetching data for {symbol}...")

            try:
                data = pipeline.get_complete_market_data(symbol)

                if data['price_data']:
                    price = data['price_data']
                    logger.info(f"  Price: Bid={price.get('bid'):.5f}, Ask={price.get('ask'):.5f}")

                if data['technical_indicators']:
                    indicators = data['technical_indicators']
                    logger.info(f"  RSI: {indicators.get('rsi')}")
                    logger.info(f"  MACD: {indicators.get('macd')}")

                if data['tradingview_analysis']:
                    for interval, analysis in data['tradingview_analysis'].items():
                        rec = analysis.get('recommendation', {}).get('overall', 'N/A')
                        logger.info(f"  TradingView ({interval}): {rec}")

            except Exception as e:
                logger.error(f"Error fetching data for {symbol}: {str(e)}")

        logger.info("")
        logger.info("=" * 70)
        logger.info("Development testing complete!")
        logger.info("For live trading, set environment to 'paper' or 'live' in config/settings.yaml")
        logger.info("=" * 70)

    elif config['system']['environment'] in ['paper', 'live']:
        logger.warning("=" * 70)
        logger.warning("TRADING MODE NOT YET IMPLEMENTED")
        logger.warning("Trading will be available in Phase 9+")
        logger.warning("Current Phase: 1 (Foundation)")
        logger.warning("=" * 70)

        # TODO: Implement trading loop in Phase 9
        # while True:
        #     # Main trading loop
        #     pass

    else:
        logger.error(f"Unknown environment: {config['system']['environment']}")
        sys.exit(1)

    # Cleanup
    logger.info("Shutting down...")
    pipeline.close()
    logger.info("ATHENA-X stopped")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\nShutdown requested by user")
        sys.exit(0)
    except Exception as e:
        logger.exception(f"Fatal error: {str(e)}")
        sys.exit(1)
