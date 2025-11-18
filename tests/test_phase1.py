"""
ATHENA-X Phase 1 Testing
Test data pipeline and all components
"""

import sys
from pathlib import Path
import yaml
from loguru import logger

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data.data_pipeline import ATHENADataPipeline
from src.data.oanda_client import OANDAClient
from src.data.tradingview_scraper import TradingViewClient
from src.storage.questdb_client import QuestDBClient
from src.storage.redis_cache import RedisCache
from src.storage.postgres_client import PostgreSQLClient
from src.utils.logging import setup_logging
from src.utils.metrics import get_metrics


def load_config():
    """Load configuration"""
    config_path = Path(__file__).parent.parent / "config" / "settings.yaml"

    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def test_logging():
    """Test logging system"""
    logger.info("=" * 60)
    logger.info("Testing Logging System")
    logger.info("=" * 60)

    try:
        setup_logging(log_level="INFO")
        logger.info("✅ Logging system initialized")
        logger.debug("Debug message test")
        logger.warning("Warning message test")
        logger.error("Error message test")

        return True

    except Exception as e:
        logger.error(f"❌ Logging test failed: {str(e)}")
        return False


def test_metrics():
    """Test metrics system"""
    logger.info("=" * 60)
    logger.info("Testing Metrics System")
    logger.info("=" * 60)

    try:
        metrics = get_metrics(port=8000, enable_prometheus=True)

        # Test recording metrics
        metrics.record_trade('EUR_USD', 'BUY', 10.50, 3600, 'WIN')
        metrics.update_performance(0.65, 1.8, 0.05, 1000, 150)
        metrics.record_agent_vote('TechnicalAgent', 'BUY')

        logger.info("✅ Metrics system working")
        return True

    except Exception as e:
        logger.error(f"❌ Metrics test failed: {str(e)}")
        return False


def test_redis(config):
    """Test Redis cache"""
    logger.info("=" * 60)
    logger.info("Testing Redis Cache")
    logger.info("=" * 60)

    try:
        redis_config = config.get('database', {}).get('redis', {})
        cache = RedisCache(redis_config)

        # Test set/get
        cache.set('test_key', {'value': 123}, ttl=60)
        value = cache.get('test_key')

        assert value['value'] == 123, "Cache value mismatch"

        # Test prefixed keys
        cache.cache_price('EUR_USD', {'bid': 1.0500, 'ask': 1.0502}, ttl=60)
        price = cache.get_cached_price('EUR_USD')

        assert price is not None, "Price not cached"

        logger.info("✅ Redis cache working")
        cache.close()
        return True

    except Exception as e:
        logger.error(f"❌ Redis test failed: {str(e)}")
        return False


def test_questdb(config):
    """Test QuestDB client"""
    logger.info("=" * 60)
    logger.info("Testing QuestDB")
    logger.info("=" * 60)

    try:
        questdb_config = config.get('database', {}).get('questdb', {})
        db = QuestDBClient(questdb_config)

        # Test query
        result = db.execute_query("SELECT 1 as test")
        assert len(result) > 0, "Query returned no results"

        logger.info("✅ QuestDB working")
        db.close()
        return True

    except Exception as e:
        logger.error(f"❌ QuestDB test failed: {str(e)}")
        logger.warning("Make sure QuestDB is running: ./scripts/start_services.sh")
        return False


def test_postgres(config):
    """Test PostgreSQL client"""
    logger.info("=" * 60)
    logger.info("Testing PostgreSQL")
    logger.info("=" * 60)

    try:
        postgres_config = config.get('database', {}).get('postgres', {})
        db = PostgreSQLClient(postgres_config)

        # Test query
        result = db.execute_query("SELECT 1 as test")
        assert len(result) > 0, "Query returned no results"

        # Test trade insert
        trade_data = {
            'symbol': 'EUR_USD',
            'direction': 'BUY',
            'entry_price': 1.0500,
            'position_size': 1000,
            'status': 'OPEN',
            'strategy': 'test'
        }

        trade_id = db.insert_trade(trade_data)
        logger.info(f"Test trade inserted: ID {trade_id}")

        logger.info("✅ PostgreSQL working")
        db.close()
        return True

    except Exception as e:
        logger.error(f"❌ PostgreSQL test failed: {str(e)}")
        logger.warning("Make sure PostgreSQL is running: ./scripts/start_services.sh")
        return False


def test_tradingview():
    """Test TradingView scraper"""
    logger.info("=" * 60)
    logger.info("Testing TradingView Scraper")
    logger.info("=" * 60)

    try:
        tv = TradingViewClient({})

        # Test analysis
        analysis = tv.get_analysis('EURUSD', interval='15m')

        assert analysis is not None, "No analysis returned"
        assert 'recommendation' in analysis, "No recommendation in analysis"

        logger.info(f"EUR/USD Recommendation: {analysis['recommendation']['overall']}")
        logger.info(f"RSI: {analysis['indicators'].get('rsi')}")

        logger.info("✅ TradingView scraper working")
        return True

    except Exception as e:
        logger.error(f"❌ TradingView test failed: {str(e)}")
        return False


def test_oanda():
    """Test OANDA client"""
    logger.info("=" * 60)
    logger.info("Testing OANDA Client")
    logger.info("=" * 60)

    try:
        import os

        api_key = os.getenv('OANDA_API_KEY')
        account_id = os.getenv('OANDA_ACCOUNT_ID')

        if not api_key or not account_id:
            logger.warning("⚠️  OANDA credentials not set, skipping test")
            logger.info("Set OANDA_API_KEY and OANDA_ACCOUNT_ID in environment")
            return None

        client = OANDAClient(
            api_key=api_key,
            account_id=account_id,
            environment='practice'
        )

        # Test account
        account = client.get_account_summary()
        logger.info(f"Account Balance: ${account['balance']}")

        # Test price
        prices = client.get_current_price(['EUR_USD'])
        if 'EUR_USD' in prices:
            logger.info(f"EUR/USD: Bid={prices['EUR_USD']['bid']}, Ask={prices['EUR_USD']['ask']}")

        # Test candles
        candles = client.get_candles('EUR_USD', granularity='M15', count=10)
        logger.info(f"Retrieved {len(candles)} candles")

        logger.info("✅ OANDA client working")
        return True

    except Exception as e:
        logger.error(f"❌ OANDA test failed: {str(e)}")
        return False


def test_data_pipeline(config):
    """Test unified data pipeline"""
    logger.info("=" * 60)
    logger.info("Testing Data Pipeline")
    logger.info("=" * 60)

    try:
        pipeline = ATHENADataPipeline(config)

        # Health check
        health = pipeline.health_check()
        logger.info(f"System Health: {health}")

        # Test market data
        data = pipeline.get_complete_market_data('EUR_USD')

        assert data is not None, "No market data returned"

        if data['price_data']:
            logger.info(f"Price Data: {data['price_data']}")

        if data['technical_indicators']:
            logger.info(f"RSI: {data['technical_indicators'].get('rsi')}")

        logger.info("✅ Data pipeline working")
        pipeline.close()
        return True

    except Exception as e:
        logger.error(f"❌ Data pipeline test failed: {str(e)}")
        return False


def main():
    """Run all tests"""
    logger.info("╔" + "=" * 58 + "╗")
    logger.info("║" + " " * 15 + "ATHENA-X PHASE 1 TESTS" + " " * 21 + "║")
    logger.info("╚" + "=" * 58 + "╝")

    # Load configuration
    config = load_config()

    # Run tests
    tests = [
        ("Logging", test_logging, None),
        ("Metrics", test_metrics, None),
        ("Redis", test_redis, config),
        ("QuestDB", test_questdb, config),
        ("PostgreSQL", test_postgres, config),
        ("TradingView", test_tradingview, None),
        ("OANDA", test_oanda, None),
        ("Data Pipeline", test_data_pipeline, config),
    ]

    results = {}
    passed = 0
    failed = 0
    skipped = 0

    for name, test_func, test_config in tests:
        try:
            if test_config:
                result = test_func(test_config)
            else:
                result = test_func()

            if result is True:
                results[name] = "✅ PASSED"
                passed += 1
            elif result is None:
                results[name] = "⚠️  SKIPPED"
                skipped += 1
            else:
                results[name] = "❌ FAILED"
                failed += 1

        except Exception as e:
            logger.error(f"Test {name} crashed: {str(e)}")
            results[name] = "❌ FAILED"
            failed += 1

    # Print summary
    logger.info("")
    logger.info("=" * 60)
    logger.info("TEST SUMMARY")
    logger.info("=" * 60)

    for name, status in results.items():
        logger.info(f"{name:<20} {status}")

    logger.info("=" * 60)
    logger.info(f"Total: {len(tests)} | Passed: {passed} | Failed: {failed} | Skipped: {skipped}")
    logger.info("=" * 60)

    if failed == 0:
        logger.success("🎉 ALL TESTS PASSED! Phase 1 is complete!")
    else:
        logger.error(f"⚠️  {failed} test(s) failed. Review errors above.")

    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
