"""
ATHENA-X Unified Data Pipeline
Coordinates all data sources and provides unified interface
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from loguru import logger

from .oanda_client import OANDAClient
from .tradingview_scraper import TradingViewClient
from .news_scraper import NewsAggregator
from .social_scraper import SocialSentimentScraper
from .economic_calendar import EconomicCalendar
from .data_validator import DataValidator
from ..storage.questdb_client import QuestDBClient
from ..storage.redis_cache import RedisCache
from ..models.finbert import FinBERTSentiment


class ATHENADataPipeline:
    """
    Unified data pipeline for ATHENA-X
    Coordinates: OANDA, TradingView, News, Social Media, Economic Calendar
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize data pipeline

        Args:
            config: System configuration
        """
        self.config = config

        # Initialize data sources
        self._init_oanda(config)
        self._init_tradingview(config)
        self._init_news(config)
        self._init_social(config)
        self._init_economic_calendar(config)
        self._init_sentiment(config)
        self._init_validator(config)
        self._init_storage(config)

        logger.info("ATHENA Data Pipeline initialized (Phase 2)")

    def _init_oanda(self, config: Dict[str, Any]):
        """Initialize OANDA client"""
        oanda_config = config.get('data_sources', {}).get('oanda', {})

        if oanda_config.get('enabled', True):
            try:
                # Get credentials from environment or config
                import os
                api_key = os.getenv('OANDA_API_KEY', '')
                account_id = os.getenv('OANDA_ACCOUNT_ID', '')
                environment = oanda_config.get('environment', 'practice')

                if api_key and account_id:
                    self.oanda = OANDAClient(
                        api_key=api_key,
                        account_id=account_id,
                        environment=environment
                    )
                    logger.info("OANDA client initialized")
                else:
                    logger.warning("OANDA credentials not found, client disabled")
                    self.oanda = None

            except Exception as e:
                logger.error(f"Failed to initialize OANDA: {str(e)}")
                self.oanda = None
        else:
            self.oanda = None
            logger.info("OANDA client disabled")

    def _init_tradingview(self, config: Dict[str, Any]):
        """Initialize TradingView client"""
        tv_config = config.get('data_sources', {}).get('tradingview', {})

        if tv_config.get('enabled', True):
            try:
                self.tradingview = TradingViewClient(tv_config)
                logger.info("TradingView client initialized")
            except Exception as e:
                logger.error(f"Failed to initialize TradingView: {str(e)}")
                self.tradingview = None
        else:
            self.tradingview = None
            logger.info("TradingView client disabled")

    def _init_news(self, config: Dict[str, Any]):
        """Initialize news aggregator"""
        news_config = config.get('data_sources', {}).get('news_sources', {})

        if news_config.get('enabled', True):
            try:
                self.news = NewsAggregator(config)
                logger.info("News aggregator initialized")
            except Exception as e:
                logger.error(f"Failed to initialize news aggregator: {str(e)}")
                self.news = None
        else:
            self.news = None
            logger.info("News aggregator disabled")

    def _init_social(self, config: Dict[str, Any]):
        """Initialize social media scraper"""
        social_config = config.get('data_sources', {}).get('social_media', {})

        if social_config.get('enabled', True):
            try:
                self.social = SocialSentimentScraper(config)
                logger.info("Social sentiment scraper initialized")
            except Exception as e:
                logger.error(f"Failed to initialize social scraper: {str(e)}")
                self.social = None
        else:
            self.social = None
            logger.info("Social sentiment scraper disabled")

    def _init_economic_calendar(self, config: Dict[str, Any]):
        """Initialize economic calendar"""
        calendar_config = config.get('data_sources', {}).get('economic_calendar', {})

        if calendar_config.get('enabled', True):
            try:
                self.economic_calendar = EconomicCalendar(calendar_config)
                logger.info("Economic calendar initialized")
            except Exception as e:
                logger.error(f"Failed to initialize economic calendar: {str(e)}")
                self.economic_calendar = None
        else:
            self.economic_calendar = None
            logger.info("Economic calendar disabled")

    def _init_sentiment(self, config: Dict[str, Any]):
        """Initialize FinBERT sentiment analyzer"""
        try:
            import torch
            if torch.cuda.is_available():
                self.finbert = FinBERTSentiment(device='cuda')
                logger.info("FinBERT initialized (GPU)")
            else:
                self.finbert = FinBERTSentiment(device='cpu')
                logger.info("FinBERT initialized (CPU)")
        except Exception as e:
            logger.warning(f"FinBERT not available: {str(e)}")
            self.finbert = None

    def _init_validator(self, config: Dict[str, Any]):
        """Initialize data validator"""
        try:
            self.validator = DataValidator(config)
            logger.info("Data validator initialized")
        except Exception as e:
            logger.error(f"Failed to initialize validator: {str(e)}")
            self.validator = None

    def _init_storage(self, config: Dict[str, Any]):
        """Initialize storage clients"""
        try:
            # QuestDB for time-series data
            questdb_config = config.get('database', {}).get('questdb', {})
            self.questdb = QuestDBClient(questdb_config)

            # Redis for caching
            redis_config = config.get('database', {}).get('redis', {})
            self.cache = RedisCache(redis_config)

            logger.info("Storage clients initialized")

        except Exception as e:
            logger.error(f"Failed to initialize storage: {str(e)}")
            self.questdb = None
            self.cache = None

    # Unified data access methods

    def get_complete_market_data(self, symbol: str) -> Dict[str, Any]:
        """
        Get complete market picture for a symbol

        Args:
            symbol: Trading symbol

        Returns:
            Complete market data including price, indicators, sentiment
        """
        logger.debug(f"Fetching complete market data for {symbol}")

        data = {
            'symbol': symbol,
            'timestamp': datetime.now(),
            'price_data': None,
            'technical_indicators': None,
            'tradingview_analysis': None,
            'sentiment': None,
            'economic_events': None
        }

        # 1. Get price data (OANDA preferred, TradingView fallback)
        data['price_data'] = self._get_price_data(symbol)

        # 2. Get technical indicators (TradingView)
        data['technical_indicators'] = self._get_technical_indicators(symbol)

        # 3. Get TradingView analysis
        data['tradingview_analysis'] = self._get_tradingview_analysis(symbol)

        # 4. Get sentiment (cached if available)
        # TODO: Implement in Phase 2
        data['sentiment'] = None

        # 5. Get economic events (cached if available)
        # TODO: Implement in Phase 2
        data['economic_events'] = None

        return data

    def _get_price_data(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get current price data"""

        # Try cache first
        if self.cache:
            cached_price = self.cache.get_cached_price(symbol)
            if cached_price:
                logger.debug(f"Price data from cache: {symbol}")
                return cached_price

        # Get from OANDA
        if self.oanda:
            try:
                prices = self.oanda.get_current_price([symbol])
                if symbol in prices:
                    price_data = prices[symbol]

                    # Cache for 60 seconds
                    if self.cache:
                        self.cache.cache_price(symbol, price_data, ttl=60)

                    return price_data

            except Exception as e:
                logger.error(f"Failed to get OANDA price for {symbol}: {str(e)}")

        # Fallback to TradingView
        if self.tradingview:
            try:
                analysis = self.tradingview.get_analysis(symbol)
                price_data = {
                    'bid': analysis['price']['current'],
                    'ask': analysis['price']['current'],
                    'spread': 0,
                    'timestamp': analysis['timestamp']
                }

                # Cache for 60 seconds
                if self.cache:
                    self.cache.cache_price(symbol, price_data, ttl=60)

                return price_data

            except Exception as e:
                logger.error(f"Failed to get TradingView price for {symbol}: {str(e)}")

        return None

    def _get_technical_indicators(
        self,
        symbol: str,
        timeframe: str = '15m'
    ) -> Optional[Dict[str, Any]]:
        """Get technical indicators"""

        # Try cache first
        if self.cache:
            cached_indicators = self.cache.get_cached_indicators(symbol, timeframe)
            if cached_indicators:
                logger.debug(f"Indicators from cache: {symbol} {timeframe}")
                return cached_indicators

        # Get from TradingView
        if self.tradingview:
            try:
                indicators = self.tradingview.get_indicators(symbol, timeframe)

                # Cache for 5 minutes
                if self.cache:
                    self.cache.cache_indicators(symbol, timeframe, indicators, ttl=300)

                return indicators

            except Exception as e:
                logger.error(f"Failed to get indicators for {symbol}: {str(e)}")

        return None

    def _get_tradingview_analysis(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get TradingView complete analysis"""

        if self.tradingview:
            try:
                # Get single timeframe to avoid rate limiting (was ['15m', '1h', '4h'])
                analyses = self.tradingview.get_multiple_intervals(
                    symbol,
                    intervals=['15m']  # Using only 15m to reduce API calls by 3x
                )

                return analyses

            except Exception as e:
                logger.error(f"Failed to get TradingView analysis for {symbol}: {str(e)}")

        return None

    # Historical data methods

    def get_historical_candles(
        self,
        symbol: str,
        timeframe: str = '15m',
        count: int = 500
    ) -> Optional[Any]:  # pd.DataFrame
        """
        Get historical candlestick data

        Args:
            symbol: Trading symbol
            timeframe: Candle timeframe
            count: Number of candles

        Returns:
            DataFrame with OHLCV data
        """

        # Map timeframe to OANDA granularity
        timeframe_map = {
            '1m': 'M1',
            '5m': 'M5',
            '15m': 'M15',
            '1h': 'H1',
            '4h': 'H4',
            '1d': 'D'
        }

        granularity = timeframe_map.get(timeframe, 'M15')

        # Get from OANDA
        if self.oanda:
            try:
                df = self.oanda.get_candles(
                    instrument=symbol,
                    granularity=granularity,
                    count=count
                )

                # Store in QuestDB for future use
                if self.questdb and not df.empty:
                    try:
                        # TODO: Implement bulk insert
                        pass
                    except Exception as e:
                        logger.error(f"Failed to store candles in QuestDB: {str(e)}")

                return df

            except Exception as e:
                logger.error(f"Failed to get historical candles: {str(e)}")

        return None

    # Data storage methods

    def store_tick(
        self,
        symbol: str,
        timestamp: datetime,
        bid: float,
        ask: float,
        spread: float
    ):
        """
        Store tick data in QuestDB

        Args:
            symbol: Trading symbol
            timestamp: Tick timestamp
            bid: Bid price
            ask: Ask price
            spread: Bid-ask spread
        """
        if self.questdb:
            try:
                mid_price = (bid + ask) / 2

                self.questdb.insert_tick(
                    table_name='ticks',
                    symbol=symbol,
                    timestamp=timestamp,
                    price=mid_price,
                    bid=bid,
                    ask=ask,
                    spread=spread
                )

            except Exception as e:
                logger.error(f"Failed to store tick: {str(e)}")

    # Batch operations

    def get_multiple_symbols_data(self, symbols: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        Get data for multiple symbols

        Args:
            symbols: List of symbols

        Returns:
            Dictionary mapping symbol to data
        """
        results = {}

        for symbol in symbols:
            try:
                results[symbol] = self.get_complete_market_data(symbol)
            except Exception as e:
                logger.error(f"Failed to get data for {symbol}: {str(e)}")
                results[symbol] = None

        return results

    # Health check

    def health_check(self) -> Dict[str, bool]:
        """
        Check health of all data sources

        Returns:
            Health status dictionary
        """
        health = {
            'oanda': False,
            'tradingview': False,
            'questdb': False,
            'redis': False
        }

        # Check OANDA
        if self.oanda:
            try:
                self.oanda.get_account_summary()
                health['oanda'] = True
            except Exception:
                pass

        # Check TradingView
        if self.tradingview:
            try:
                self.tradingview.get_analysis('EUR_USD')
                health['tradingview'] = True
            except Exception:
                pass

        # Check QuestDB
        if self.questdb:
            try:
                self.questdb.execute_query("SELECT 1")
                health['questdb'] = True
            except Exception:
                pass

        # Check Redis
        if self.cache:
            try:
                self.cache.client.ping()
                health['redis'] = True
            except Exception:
                pass

        return health

    def close(self):
        """Close all connections"""
        if self.questdb:
            self.questdb.close()

        if self.cache:
            self.cache.close()

        logger.info("Data pipeline connections closed")

    # Phase 2: News, Social, Economic Calendar methods

    def get_news(self, cached: bool = True) -> List[Dict[str, Any]]:
        """Get latest news articles with sentiment"""
        if not self.news:
            return []

        # Check cache first
        if cached and self.cache:
            cached_news = self.cache.get_cached_news('all')
            if cached_news:
                logger.debug("News from cache")
                return cached_news

        # Fetch fresh news
        articles = self.news.get_all_news(max_articles=100)

        # Add sentiment analysis if FinBERT available
        if self.finbert:
            articles = self.finbert.analyze_news_articles(articles)

        # Cache for 15 minutes
        if self.cache:
            self.cache.cache_news('all', articles, ttl=900)

        return articles

    def get_social_sentiment(self, symbols: List[str]) -> Dict[str, Any]:
        """Get social media sentiment for symbols"""
        if not self.social:
            return {'error': 'Social scraper not initialized'}

        return self.social.get_social_sentiment_summary(symbols)

    def check_economic_events(self, currencies: List[str], buffer_minutes: int = 30) -> Dict[str, Any]:
        """Check for upcoming high-impact economic events"""
        if not self.economic_calendar:
            return {'should_avoid_trading': False, 'events': []}

        should_avoid = self.economic_calendar.should_avoid_trading(currencies, buffer_minutes)
        events = self.economic_calendar.get_high_impact_events(hours_ahead=24)

        return {
            'should_avoid_trading': should_avoid,
            'high_impact_events': events,
            'checked_at': datetime.now()
        }

    def get_complete_market_data(self, symbol: str) -> Dict[str, Any]:
        """
        Get complete market picture for a symbol (Phase 2 enhanced)
        """
        logger.debug(f"Fetching complete market data for {symbol}")

        data = {
            'symbol': symbol,
            'timestamp': datetime.now(),
            'price_data': None,
            'technical_indicators': None,
            'tradingview_analysis': None,
            'news_sentiment': None,
            'social_sentiment': None,
            'economic_events': None
        }

        # 1. Get price data (OANDA preferred, TradingView fallback)
        data['price_data'] = self._get_price_data(symbol)

        # Validate price data
        if data['price_data'] and self.validator:
            validation = self.validator.validate_tick({
                'symbol': symbol,
                'price': data['price_data'].get('bid'),
                'bid': data['price_data'].get('bid'),
                'ask': data['price_data'].get('ask'),
                'timestamp': data['price_data'].get('timestamp')
            })

            if not validation['valid']:
                logger.warning(f"Price data validation failed for {symbol}")

        # 2. Get technical indicators (TradingView)
        data['technical_indicators'] = self._get_technical_indicators(symbol)

        # 3. Get TradingView analysis
        data['tradingview_analysis'] = self._get_tradingview_analysis(symbol)

        # 4. Get news sentiment (cached)
        data['news_sentiment'] = self._get_news_sentiment(symbol)

        # 5. Get social sentiment
        data['social_sentiment'] = self._get_social_sentiment(symbol)

        # 6. Check economic events
        data['economic_events'] = self._check_economic_events(symbol)

        return data

    def _get_news_sentiment(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get aggregated news sentiment for symbol"""
        if not self.news or not self.finbert:
            return None

        # Get cached sentiment
        if self.cache:
            cached = self.cache.get_cached_sentiment(symbol)
            if cached:
                return cached

        # Get news and filter by keywords
        keywords = [symbol, symbol.replace('_', ''), symbol.replace('_', '/')]
        articles = self.get_news(cached=True)
        relevant = self.news.filter_by_keywords(articles, keywords)

        if not relevant:
            return None

        # Aggregate sentiment
        sentiments = [
            {
                'score': a.get('sentiment_score', 0),
                'confidence': a.get('sentiment_confidence', 0),
                'sentiment': a.get('sentiment', 'neutral')
            }
            for a in relevant
        ]

        aggregated = self.finbert.aggregate_sentiment(sentiments)

        # Cache for 30 minutes
        if self.cache:
            self.cache.cache_sentiment(symbol, aggregated, ttl=1800)

        return aggregated

    def _get_social_sentiment(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get social media sentiment for symbol"""
        if not self.social:
            return None

        try:
            summary = self.social.get_social_sentiment_summary([symbol])
            return summary['symbol_sentiments'].get(symbol)
        except Exception as e:
            logger.error(f"Failed to get social sentiment: {str(e)}")
            return None

    def _check_economic_events(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Check for economic events affecting symbol"""
        if not self.economic_calendar:
            return None

        # Extract currency from symbol (e.g., EUR_USD -> [EUR, USD])
        currencies = symbol.split('_')

        if len(currencies) == 2:
            return self.check_economic_events(currencies, buffer_minutes=30)

        return None
