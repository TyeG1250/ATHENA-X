"""
ATHENA-X Phase 2 Testing
Test news, social, economic calendar, and sentiment analysis
"""

import sys
from pathlib import Path
import yaml
from loguru import logger

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data.news_scraper import NewsAggregator
from src.data.social_scraper import SocialSentimentScraper
from src.data.economic_calendar import EconomicCalendar
from src.data.data_validator import DataValidator
from src.models.finbert import FinBERTSentiment
from src.data.data_pipeline import ATHENADataPipeline


def load_config():
    """Load configuration"""
    config_path = Path(__file__).parent.parent / "config" / "settings.yaml"
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def test_news_scraper(config):
    """Test news aggregator"""
    logger.info("=" * 60)
    logger.info("Testing News Scraper")
    logger.info("=" * 60)

    try:
        news = NewsAggregator(config)

        # Test individual sources
        logger.info("Testing Reuters...")
        reuters = news.scrape_reuters()
        logger.info(f"✓ Reuters: {len(reuters)} articles")

        logger.info("Testing CNBC...")
        cnbc = news.scrape_cnbc_rss()
        logger.info(f"✓ CNBC: {len(cnbc)} articles")

        # Test aggregation
        logger.info("Testing aggregation...")
        all_news = news.get_all_news(max_articles=50)
        logger.info(f"✓ Total unique articles: {len(all_news)}")

        if all_news:
            logger.info(f"Sample article: {all_news[0]['title']}")

        logger.info("✅ News scraper working")
        return True

    except Exception as e:
        logger.error(f"❌ News scraper test failed: {str(e)}")
        return False


def test_economic_calendar(config):
    """Test economic calendar"""
    logger.info("=" * 60)
    logger.info("Testing Economic Calendar")
    logger.info("=" * 60)

    try:
        calendar = EconomicCalendar(config)

        # Test scraping today's events
        logger.info("Scraping today's events...")
        events = calendar.scrape_today()
        logger.info(f"✓ Found {len(events)} events today")

        # Test high-impact events
        logger.info("Getting high-impact events...")
        high_impact = calendar.get_high_impact_events()
        logger.info(f"✓ Found {len(high_impact)} high-impact events")

        # Test event checking
        should_avoid = calendar.should_avoid_trading(['USD', 'EUR'], buffer_minutes=30)
        logger.info(f"✓ Should avoid trading: {should_avoid}")

        logger.info("✅ Economic calendar working")
        return True

    except Exception as e:
        logger.error(f"❌ Economic calendar test failed: {str(e)}")
        return False


def test_social_scraper(config):
    """Test social media scraper"""
    logger.info("=" * 60)
    logger.info("Testing Social Media Scraper")
    logger.info("=" * 60)

    try:
        import os

        # Check if Reddit credentials are set
        if not os.getenv('REDDIT_CLIENT_ID'):
            logger.warning("⚠️  Reddit credentials not set, skipping test")
            logger.info("Set REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET to test")
            return None

        social = SocialSentimentScraper(config)

        # Test Reddit scraping
        logger.info("Scraping Reddit...")
        posts = social.scrape_reddit(subreddits=['Forex'], max_posts=10)
        logger.info(f"✓ Scraped {len(posts)} posts")

        if posts:
            # Test ticker extraction
            trending = social.get_trending_topics(posts)
            logger.info(f"✓ Trending tickers: {trending}")

            # Test sentiment for symbol
            sentiment = social.get_sentiment_for_symbol('EUR_USD', posts)
            logger.info(f"✓ EUR/USD sentiment: {sentiment['sentiment']}")

        logger.info("✅ Social scraper working")
        return True

    except Exception as e:
        logger.error(f"❌ Social scraper test failed: {str(e)}")
        return False


def test_finbert(config):
    """Test FinBERT sentiment analysis"""
    logger.info("=" * 60)
    logger.info("Testing FinBERT Sentiment Analysis")
    logger.info("=" * 60)

    try:
        finbert = FinBERTSentiment(device='cpu')  # Use CPU for testing

        # Test single text
        text = "The Federal Reserve raised interest rates, boosting the US dollar significantly."
        result = finbert.analyze_sentiment(text)
        logger.info(f"✓ Sentiment: {result['sentiment']} (score: {result['score']:.3f})")

        # Test batch analysis
        texts = [
            "Stock market crashes as recession fears grow",
            "Economy shows strong growth, unemployment at record low",
            "Markets remain flat with mixed signals from investors"
        ]
        results = finbert.analyze_batch(texts)
        logger.info(f"✓ Batch analysis: {len(results)} texts analyzed")

        for i, res in enumerate(results):
            logger.info(f"  {i+1}. {res['sentiment']} (score: {res['score']:.3f})")

        # Test aggregation
        aggregated = finbert.aggregate_sentiment(results)
        logger.info(f"✓ Aggregate sentiment: {aggregated['aggregate_sentiment']}")

        logger.info("✅ FinBERT working")
        return True

    except Exception as e:
        logger.error(f"❌ FinBERT test failed: {str(e)}")
        logger.warning("Make sure PyTorch and transformers are installed")
        return False


def test_data_validator(config):
    """Test data validator"""
    logger.info("=" * 60)
    logger.info("Testing Data Validator")
    logger.info("=" * 60)

    try:
        validator = DataValidator(config)

        # Test tick validation
        valid_tick = {
            'symbol': 'EUR_USD',
            'price': 1.0500,
            'bid': 1.0499,
            'ask': 1.0501,
            'timestamp': '2024-01-01T12:00:00Z'
        }

        result = validator.validate_tick(valid_tick)
        logger.info(f"✓ Valid tick: {result['valid']}")

        # Test invalid tick (negative spread)
        invalid_tick = {
            'symbol': 'EUR_USD',
            'price': 1.0500,
            'bid': 1.0502,
            'ask': 1.0500,
            'timestamp': '2024-01-01T12:00:00Z'
        }

        result = validator.validate_tick(invalid_tick)
        logger.info(f"✓ Invalid tick detected: {not result['valid']}")

        # Test candle validation
        candles = [
            {'open': 1.05, 'high': 1.06, 'low': 1.04, 'close': 1.055},
            {'open': 1.055, 'high': 1.07, 'low': 1.05, 'close': 1.065}
        ]

        result = validator.validate_candles(candles)
        logger.info(f"✓ Candle validation: {result['valid']}")

        logger.info("✅ Data validator working")
        return True

    except Exception as e:
        logger.error(f"❌ Data validator test failed: {str(e)}")
        return False


def test_integrated_pipeline(config):
    """Test integrated data pipeline with Phase 2 features"""
    logger.info("=" * 60)
    logger.info("Testing Integrated Pipeline (Phase 2)")
    logger.info("=" * 60)

    try:
        pipeline = ATHENADataPipeline(config)

        # Test getting news with sentiment
        logger.info("Testing news with sentiment...")
        news = pipeline.get_news(cached=False)
        logger.info(f"✓ Retrieved {len(news)} news articles")

        if news and 'sentiment' in news[0]:
            logger.info(f"  Sample: {news[0]['title']}")
            logger.info(f"  Sentiment: {news[0]['sentiment']}")

        # Test economic events check
        logger.info("Testing economic events...")
        events = pipeline.check_economic_events(['USD', 'EUR'])
        logger.info(f"✓ Should avoid trading: {events['should_avoid_trading']}")
        logger.info(f"  High-impact events: {len(events['high_impact_events'])}")

        # Test complete market data with Phase 2 enhancements
        logger.info("Testing complete market data...")
        data = pipeline.get_complete_market_data('EUR_USD')

        logger.info(f"✓ Price data: {data['price_data'] is not None}")
        logger.info(f"✓ Technical indicators: {data['technical_indicators'] is not None}")
        logger.info(f"✓ News sentiment: {data['news_sentiment'] is not None}")
        logger.info(f"✓ Economic events: {data['economic_events'] is not None}")

        pipeline.close()

        logger.info("✅ Integrated pipeline working")
        return True

    except Exception as e:
        logger.error(f"❌ Integrated pipeline test failed: {str(e)}")
        return False


def main():
    """Run all Phase 2 tests"""
    logger.info("╔" + "=" * 58 + "╗")
    logger.info("║" + " " * 15 + "ATHENA-X PHASE 2 TESTS" + " " * 21 + "║")
    logger.info("╚" + "=" * 58 + "╝")

    config = load_config()

    tests = [
        ("News Scraper", test_news_scraper, config),
        ("Economic Calendar", test_economic_calendar, config),
        ("Social Scraper", test_social_scraper, config),
        ("FinBERT", test_finbert, config),
        ("Data Validator", test_data_validator, config),
        ("Integrated Pipeline", test_integrated_pipeline, config),
    ]

    results = {}
    passed = 0
    failed = 0
    skipped = 0

    for name, test_func, test_config in tests:
        try:
            result = test_func(test_config)

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
        logger.info(f"{name:<25} {status}")

    logger.info("=" * 60)
    logger.info(f"Total: {len(tests)} | Passed: {passed} | Failed: {failed} | Skipped: {skipped}")
    logger.info("=" * 60)

    if failed == 0:
        logger.success("🎉 ALL TESTS PASSED! Phase 2 is complete!")
    else:
        logger.error(f"⚠️  {failed} test(s) failed. Review errors above.")

    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
