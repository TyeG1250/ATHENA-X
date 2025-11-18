"""
JARVIS-X Data Validation Layer
Validates incoming data quality
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import numpy as np
from loguru import logger


class DataValidator:
    """
    Data quality validation for market data
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize data validator

        Args:
            config: Validation configuration
        """
        self.config = config
        self.validation_config = config.get('data_validation', {})

        # Validation thresholds
        self.max_price_deviation = self.validation_config.get('price_checks', {}).get('max_deviation_pct', 0.10)
        self.outlier_std_threshold = self.validation_config.get('price_checks', {}).get('outlier_std_threshold', 3.0)
        self.max_spread_multiplier = self.validation_config.get('spread_checks', {}).get('max_spread_multiplier', 3.0)
        self.min_volume_pct = self.validation_config.get('volume_checks', {}).get('min_volume_pct', 0.50)
        self.max_age_seconds = self.validation_config.get('timestamp_checks', {}).get('max_age_seconds', 300)

        # Historical data for validation
        self.price_history = {}

        logger.info("Data validator initialized")

    def validate_tick(self, tick: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate a single tick

        Args:
            tick: Tick data

        Returns:
            Validation result
        """
        checks = {
            'price_range': self._check_price_range(tick),
            'spread': self._check_spread(tick),
            'timestamp': self._check_timestamp(tick),
            'completeness': self._check_completeness(tick)
        }

        # Overall validity
        is_valid = all(checks.values())

        if not is_valid:
            failed_checks = [k for k, v in checks.items() if not v]
            logger.warning(f"Tick validation failed: {failed_checks}")

        return {
            'valid': is_valid,
            'checks': checks,
            'action': 'accept' if is_valid else 'reject'
        }

    def _check_price_range(self, tick: Dict[str, Any]) -> bool:
        """Check if price is within reasonable range"""
        symbol = tick.get('instrument') or tick.get('symbol')
        price = tick.get('price') or tick.get('mid')

        if not symbol or not price:
            return False

        # Get historical range
        if symbol in self.price_history:
            history = self.price_history[symbol]

            # Check if price deviates too much from recent range
            recent_high = history.get('high', price * 1.5)
            recent_low = history.get('low', price * 0.5)

            # Allow 10% deviation from historical range
            upper_bound = recent_high * (1 + self.max_price_deviation)
            lower_bound = recent_low * (1 - self.max_price_deviation)

            if not (lower_bound <= price <= upper_bound):
                logger.warning(f"Price {price} outside range [{lower_bound}, {upper_bound}] for {symbol}")
                return False

        # Update price history
        self._update_price_history(symbol, price)

        return True

    def _check_spread(self, tick: Dict[str, Any]) -> bool:
        """Check if spread is reasonable"""
        bid = tick.get('bid')
        ask = tick.get('ask')

        if bid is None or ask is None:
            return True  # Can't check without bid/ask

        spread = ask - bid

        if spread < 0:
            logger.warning("Negative spread detected")
            return False

        # Check against average spread (if available)
        avg_spread = tick.get('avg_spread', spread)

        if spread > avg_spread * self.max_spread_multiplier:
            logger.warning(f"Spread {spread} exceeds {self.max_spread_multiplier}x average {avg_spread}")
            return False

        return True

    def _check_timestamp(self, tick: Dict[str, Any]) -> bool:
        """Check if timestamp is recent"""
        timestamp = tick.get('timestamp')

        if not timestamp:
            return False

        # Convert to datetime if string
        if isinstance(timestamp, str):
            try:
                timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            except:
                return False

        # Check age
        age_seconds = (datetime.now() - timestamp.replace(tzinfo=None)).total_seconds()

        if age_seconds > self.max_age_seconds:
            logger.warning(f"Stale data: {age_seconds}s old (max: {self.max_age_seconds}s)")
            return False

        return True

    def _check_completeness(self, tick: Dict[str, Any]) -> bool:
        """Check if required fields are present"""
        required_fields = ['symbol', 'price', 'timestamp']

        # Check for symbol field (different naming conventions)
        has_symbol = 'symbol' in tick or 'instrument' in tick

        # Check for price field
        has_price = 'price' in tick or 'mid' in tick or ('bid' in tick and 'ask' in tick)

        # Check for timestamp
        has_timestamp = 'timestamp' in tick or 'time' in tick

        return has_symbol and has_price and has_timestamp

    def _update_price_history(self, symbol: str, price: float):
        """Update price history for symbol"""
        if symbol not in self.price_history:
            self.price_history[symbol] = {
                'prices': [],
                'high': price,
                'low': price,
                'last_update': datetime.now()
            }

        history = self.price_history[symbol]
        history['prices'].append(price)

        # Keep last 100 prices
        if len(history['prices']) > 100:
            history['prices'] = history['prices'][-100:]

        # Update high/low
        history['high'] = max(history['prices'])
        history['low'] = min(history['prices'])
        history['last_update'] = datetime.now()

    def validate_candles(self, candles: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Validate OHLC candle data

        Args:
            candles: List of candles

        Returns:
            Validation result
        """
        if not candles:
            return {'valid': False, 'error': 'No candles provided'}

        invalid_candles = []

        for i, candle in enumerate(candles):
            # Check OHLC relationship
            open_price = candle.get('open')
            high = candle.get('high')
            low = candle.get('low')
            close = candle.get('close')

            if None in [open_price, high, low, close]:
                invalid_candles.append(i)
                continue

            # High should be highest
            if high < max(open_price, close) or high < low:
                invalid_candles.append(i)
                logger.debug(f"Invalid high in candle {i}")
                continue

            # Low should be lowest
            if low > min(open_price, close) or low > high:
                invalid_candles.append(i)
                logger.debug(f"Invalid low in candle {i}")
                continue

        is_valid = len(invalid_candles) == 0

        return {
            'valid': is_valid,
            'total_candles': len(candles),
            'invalid_candles': len(invalid_candles),
            'invalid_indices': invalid_candles
        }

    def validate_news_article(self, article: Dict[str, Any]) -> bool:
        """
        Validate news article

        Args:
            article: News article

        Returns:
            True if valid
        """
        # Required fields
        required = ['title', 'source', 'scraped_at']

        for field in required:
            if field not in article or not article[field]:
                return False

        # Check title length
        title = article.get('title', '')
        if len(title) < 10 or len(title) > 500:
            return False

        # Check timestamp recency
        scraped_at = article.get('scraped_at')
        if isinstance(scraped_at, datetime):
            age_hours = (datetime.now() - scraped_at).total_seconds() / 3600
            if age_hours > 48:  # Older than 48 hours
                return False

        return True

    def detect_outliers(self, values: List[float], threshold: float = 3.0) -> List[int]:
        """
        Detect outliers using z-score

        Args:
            values: List of values
            threshold: Z-score threshold

        Returns:
            Indices of outliers
        """
        if len(values) < 3:
            return []

        values_array = np.array(values)
        mean = np.mean(values_array)
        std = np.std(values_array)

        if std == 0:
            return []

        z_scores = np.abs((values_array - mean) / std)
        outliers = np.where(z_scores > threshold)[0].tolist()

        return outliers

    def validate_sentiment_data(self, sentiment: Dict[str, Any]) -> bool:
        """
        Validate sentiment analysis result

        Args:
            sentiment: Sentiment data

        Returns:
            True if valid
        """
        # Check required fields
        required = ['sentiment', 'score', 'confidence']

        for field in required:
            if field not in sentiment:
                return False

        # Validate sentiment value
        if sentiment['sentiment'] not in ['positive', 'negative', 'neutral']:
            return False

        # Validate score range (-1 to 1)
        score = sentiment.get('score', 0)
        if not (-1.0 <= score <= 1.0):
            return False

        # Validate confidence range (0 to 1)
        confidence = sentiment.get('confidence', 0)
        if not (0.0 <= confidence <= 1.0):
            return False

        return True

    def get_validation_statistics(self) -> Dict[str, Any]:
        """
        Get validation statistics

        Returns:
            Validation statistics
        """
        total_symbols = len(self.price_history)

        return {
            'symbols_tracked': total_symbols,
            'price_history_size': {
                symbol: len(history['prices'])
                for symbol, history in self.price_history.items()
            },
            'validation_config': {
                'max_price_deviation': self.max_price_deviation,
                'max_spread_multiplier': self.max_spread_multiplier,
                'max_age_seconds': self.max_age_seconds
            }
        }
