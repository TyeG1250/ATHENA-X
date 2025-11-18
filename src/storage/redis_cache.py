"""
JARVIS-X Redis Cache Client
Caching layer for fast data access
"""

import redis
import json
import pickle
from typing import Any, Optional, Dict, List
from datetime import timedelta
from loguru import logger


class RedisCache:
    """
    Redis cache client for JARVIS-X
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Redis cache

        Args:
            config: Redis configuration
        """
        self.config = config
        self.host = config.get('host', 'localhost')
        self.port = config.get('port', 6379)
        self.db = config.get('db', 0)
        self.password = config.get('password')
        self.default_ttl = config.get('default_ttl', 900)  # 15 minutes

        self.client = redis.Redis(
            host=self.host,
            port=self.port,
            db=self.db,
            password=self.password,
            decode_responses=False  # We'll handle encoding ourselves
        )

        # Test connection
        try:
            self.client.ping()
            logger.info(f"Connected to Redis at {self.host}:{self.port}")
        except redis.ConnectionError as e:
            logger.error(f"Failed to connect to Redis: {str(e)}")
            raise

    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        serialize: str = 'json'
    ) -> bool:
        """
        Set a value in cache

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds (None = default)
            serialize: Serialization method ('json' or 'pickle')

        Returns:
            Success status
        """
        if ttl is None:
            ttl = self.default_ttl

        try:
            # Serialize value
            if serialize == 'json':
                serialized = json.dumps(value)
            elif serialize == 'pickle':
                serialized = pickle.dumps(value)
            else:
                serialized = str(value)

            # Set with TTL
            result = self.client.setex(
                name=key,
                time=ttl,
                value=serialized
            )

            logger.debug(f"Cached: {key} (TTL: {ttl}s)")
            return bool(result)

        except Exception as e:
            logger.error(f"Failed to set cache key '{key}': {str(e)}")
            return False

    def get(
        self,
        key: str,
        default: Any = None,
        deserialize: str = 'json'
    ) -> Any:
        """
        Get a value from cache

        Args:
            key: Cache key
            default: Default value if not found
            deserialize: Deserialization method ('json' or 'pickle')

        Returns:
            Cached value or default
        """
        try:
            value = self.client.get(key)

            if value is None:
                logger.debug(f"Cache miss: {key}")
                return default

            # Deserialize value
            if deserialize == 'json':
                result = json.loads(value)
            elif deserialize == 'pickle':
                result = pickle.loads(value)
            else:
                result = value.decode('utf-8')

            logger.debug(f"Cache hit: {key}")
            return result

        except Exception as e:
            logger.error(f"Failed to get cache key '{key}': {str(e)}")
            return default

    def delete(self, key: str) -> bool:
        """
        Delete a key from cache

        Args:
            key: Cache key

        Returns:
            Success status
        """
        try:
            result = self.client.delete(key)
            logger.debug(f"Deleted cache key: {key}")
            return bool(result)

        except Exception as e:
            logger.error(f"Failed to delete cache key '{key}': {str(e)}")
            return False

    def exists(self, key: str) -> bool:
        """Check if key exists"""
        try:
            return bool(self.client.exists(key))
        except Exception as e:
            logger.error(f"Failed to check key existence '{key}': {str(e)}")
            return False

    def get_ttl(self, key: str) -> Optional[int]:
        """
        Get remaining TTL for a key

        Args:
            key: Cache key

        Returns:
            Remaining seconds or None if key doesn't exist
        """
        try:
            ttl = self.client.ttl(key)
            return ttl if ttl >= 0 else None
        except Exception as e:
            logger.error(f"Failed to get TTL for '{key}': {str(e)}")
            return None

    def set_with_prefix(self, prefix: str, identifier: str, value: Any, ttl: Optional[int] = None):
        """
        Set value with prefixed key

        Args:
            prefix: Key prefix (e.g., 'price', 'news', 'sentiment')
            identifier: Unique identifier (e.g., symbol, article ID)
            value: Value to cache
            ttl: Time to live
        """
        key = f"{prefix}:{identifier}"
        return self.set(key, value, ttl)

    def get_with_prefix(self, prefix: str, identifier: str, default: Any = None):
        """Get value with prefixed key"""
        key = f"{prefix}:{identifier}"
        return self.get(key, default)

    def delete_by_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching a pattern

        Args:
            pattern: Key pattern (e.g., 'price:*', 'news:EUR_USD:*')

        Returns:
            Number of keys deleted
        """
        try:
            keys = self.client.keys(pattern)
            if keys:
                deleted = self.client.delete(*keys)
                logger.info(f"Deleted {deleted} keys matching pattern: {pattern}")
                return deleted
            return 0

        except Exception as e:
            logger.error(f"Failed to delete keys by pattern '{pattern}': {str(e)}")
            return 0

    def flush_db(self):
        """Clear all keys in current database"""
        try:
            self.client.flushdb()
            logger.warning("Flushed all keys from Redis database")
        except Exception as e:
            logger.error(f"Failed to flush database: {str(e)}")

    # Specialized caching methods for JARVIS-X

    def cache_price(self, symbol: str, price_data: Dict[str, Any], ttl: int = 60):
        """Cache latest price data"""
        return self.set_with_prefix('price', symbol, price_data, ttl)

    def get_cached_price(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get cached price data"""
        return self.get_with_prefix('price', symbol)

    def cache_indicators(self, symbol: str, timeframe: str, indicators: Dict[str, Any], ttl: int = 300):
        """Cache technical indicators"""
        key = f"{symbol}:{timeframe}"
        return self.set_with_prefix('indicators', key, indicators, ttl)

    def get_cached_indicators(self, symbol: str, timeframe: str) -> Optional[Dict[str, Any]]:
        """Get cached indicators"""
        key = f"{symbol}:{timeframe}"
        return self.get_with_prefix('indicators', key)

    def cache_news(self, source: str, articles: List[Dict[str, Any]], ttl: int = 900):
        """Cache news articles"""
        return self.set_with_prefix('news', source, articles, ttl)

    def get_cached_news(self, source: str) -> Optional[List[Dict[str, Any]]]:
        """Get cached news"""
        return self.get_with_prefix('news', source, default=[])

    def cache_sentiment(self, symbol: str, sentiment: Dict[str, Any], ttl: int = 1800):
        """Cache sentiment analysis"""
        return self.set_with_prefix('sentiment', symbol, sentiment, ttl)

    def get_cached_sentiment(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get cached sentiment"""
        return self.get_with_prefix('sentiment', symbol)

    def cache_economic_calendar(self, events: List[Dict[str, Any]], ttl: int = 86400):
        """Cache economic calendar (daily)"""
        return self.set('economic_calendar', events, ttl)

    def get_cached_economic_calendar(self) -> List[Dict[str, Any]]:
        """Get cached economic calendar"""
        return self.get('economic_calendar', default=[])

    # Statistics and monitoring

    def get_stats(self) -> Dict[str, Any]:
        """Get Redis statistics"""
        try:
            info = self.client.info()
            return {
                'connected_clients': info.get('connected_clients', 0),
                'used_memory': info.get('used_memory_human', '0B'),
                'total_keys': self.client.dbsize(),
                'hit_rate': self._calculate_hit_rate(info)
            }
        except Exception as e:
            logger.error(f"Failed to get Redis stats: {str(e)}")
            return {}

    def _calculate_hit_rate(self, info: Dict[str, Any]) -> float:
        """Calculate cache hit rate"""
        hits = info.get('keyspace_hits', 0)
        misses = info.get('keyspace_misses', 0)
        total = hits + misses

        if total == 0:
            return 0.0

        return (hits / total) * 100

    def close(self):
        """Close Redis connection"""
        try:
            self.client.close()
            logger.info("Redis connection closed")
        except Exception as e:
            logger.error(f"Error closing Redis connection: {str(e)}")
