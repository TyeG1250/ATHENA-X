#!/usr/bin/env python3
"""
ATHENA-X Deployment Script
Deploys the trading system to paper trading or live environment
"""

import sys
import yaml
import argparse
from pathlib import Path
from loguru import logger
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data.data_pipeline import ATHENADataPipeline
from src.orchestration.orchestrator import ATHENAOrchestrator
from src.execution.order_manager import OrderManager
from src.utils.metrics import MetricsCollector
from datetime import datetime
import time


def load_config(config_path: str = "config/settings.yaml") -> dict:
    """Load configuration"""
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def setup_logging(environment: str):
    """Setup logging"""
    logger.remove()
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan> - <level>{message}</level>",
        level="INFO"
    )
    logger.add(
        f"logs/athena_{environment}_{datetime.now().strftime('%Y%m%d')}.log",
        rotation="1 day",
        retention="30 days",
        level="DEBUG"
    )


def health_check(pipeline: ATHENADataPipeline) -> bool:
    """Run system health check"""
    logger.info("Running health check...")

    health = pipeline.health_check()

    all_healthy = all(health.values())

    for service, status in health.items():
        if status:
            logger.success(f"  ✓ {service}: OK")
        else:
            logger.error(f"  ✗ {service}: FAILED")

    return all_healthy


def trading_loop(
    pipeline: ATHENADataPipeline,
    orchestrator: ATHENAOrchestrator,
    order_manager: OrderManager,
    metrics: MetricsCollector,
    config: dict,
    dry_run: bool = True
):
    """Main trading loop"""
    symbols = config['trading']['symbols']
    loop_interval = config['system'].get('loop_interval', 60)  # seconds

    logger.info(f"Starting trading loop (dry_run={dry_run})...")
    logger.info(f"Monitoring symbols: {symbols}")
    logger.info(f"Loop interval: {loop_interval}s")

    iteration = 0

    try:
        while True:
            iteration += 1
            logger.info(f"{'='*60}")
            logger.info(f"Iteration #{iteration} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info(f"{'='*60}")

            for symbol in symbols:
                try:
                    # Get market data
                    logger.info(f"Fetching data for {symbol}...")
                    market_data = pipeline.get_complete_market_data(symbol)

                    # Evaluate opportunity
                    logger.info(f"Evaluating {symbol}...")
                    decision = orchestrator.evaluate_opportunity(
                        symbol=symbol,
                        market_data=market_data
                    )

                    # Log decision
                    if decision['decision'] == 'EXECUTE':
                        logger.success(
                            f"TRADE SIGNAL: {decision['direction']} {symbol} "
                            f"(confidence: {decision['confidence']:.2%}, "
                            f"size: {decision['position_size_pct']:.2%})"
                        )

                        # Execute trade
                        if not dry_run:
                            result = order_manager.execute_trade(decision, dry_run=False)
                            if result['success']:
                                logger.success(f"Trade executed: {result['order_id']}")
                            else:
                                logger.error(f"Trade failed: {result.get('error')}")
                        else:
                            logger.info("DRY RUN - Trade not executed")
                            result = order_manager.execute_trade(decision, dry_run=True)

                        # Record metrics
                        metrics.record_trade_decision(decision)

                    else:
                        logger.info(f"No trade for {symbol}: {decision.get('reason', 'N/A')}")

                except Exception as e:
                    logger.error(f"Error processing {symbol}: {str(e)}")
                    continue

            # Sleep before next iteration
            logger.info(f"Sleeping for {loop_interval}s...")
            time.sleep(loop_interval)

    except KeyboardInterrupt:
        logger.warning("Received interrupt signal, shutting down...")
        return
    except Exception as e:
        logger.error(f"Fatal error in trading loop: {str(e)}")
        raise


def main():
    """Main deployment function"""
    parser = argparse.ArgumentParser(description="Deploy ATHENA-X Trading System")
    parser.add_argument(
        '--mode',
        '--environment',
        dest='environment',
        choices=['paper', 'live'],
        default='paper',
        help='Deployment environment (paper or live)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Run without executing real trades'
    )
    parser.add_argument(
        '--config',
        default='config/settings.yaml',
        help='Configuration file path'
    )
    parser.add_argument(
        '--symbols',
        type=str,
        help='Comma-separated list of symbols to trade (overrides config)'
    )
    parser.add_argument(
        '--capital',
        type=float,
        help='Trading capital (overrides config)'
    )

    args = parser.parse_args()

    # Setup
    setup_logging(args.environment)
    logger.info("="*60)
    logger.info("ATHENA-X TRADING SYSTEM")
    logger.info("="*60)
    logger.info(f"Environment: {args.environment}")
    logger.info(f"Dry Run: {args.dry_run}")
    logger.info("="*60)

    # Load configuration
    config = load_config(args.config)

    # Override config with command-line arguments if provided
    if args.symbols:
        config['trading']['symbols'] = [s.strip() for s in args.symbols.split(',')]
        logger.info(f"Overriding symbols from command line: {config['trading']['symbols']}")

    if args.capital:
        config['trading']['capital'] = args.capital
        logger.info(f"Overriding capital from command line: ${args.capital}")

    # Update environment in config
    config['system']['environment'] = args.environment

    # Initialize components
    logger.info("Initializing components...")

    logger.info("  - Data Pipeline...")
    pipeline = ATHENADataPipeline(config)

    logger.info("  - Orchestrator...")
    orchestrator = ATHENAOrchestrator(config)

    logger.info("  - Order Manager...")
    order_manager = OrderManager(config, oanda_client=pipeline.oanda)

    logger.info("  - Metrics Collector...")
    metrics = MetricsCollector(config)

    # Health check
    if not health_check(pipeline):
        logger.error("Health check failed! Fix issues before deploying.")
        sys.exit(1)

    logger.success("All systems operational!")

    # Start trading loop
    logger.info("Starting trading loop...")
    trading_loop(
        pipeline=pipeline,
        orchestrator=orchestrator,
        order_manager=order_manager,
        metrics=metrics,
        config=config,
        dry_run=args.dry_run
    )

    # Cleanup
    logger.info("Shutting down gracefully...")
    pipeline.close()
    logger.info("ATHENA-X stopped")


if __name__ == "__main__":
    main()
