"""
ATHENA-X TradingView Scraper
Get price data and technical indicators from TradingView
"""

from tradingview_ta import TA_Handler, Interval
from typing import Dict, Any, List, Optional
from datetime import datetime
from loguru import logger
import time


class TradingViewClient:
    """
    TradingView API client for ATHENA-X
    """

    # Interval mapping
    INTERVALS = {
        '1m': Interval.INTERVAL_1_MINUTE,
        '5m': Interval.INTERVAL_5_MINUTES,
        '15m': Interval.INTERVAL_15_MINUTES,
        '30m': Interval.INTERVAL_30_MINUTES,
        '1h': Interval.INTERVAL_1_HOUR,
        '2h': Interval.INTERVAL_2_HOURS,
        '4h': Interval.INTERVAL_4_HOURS,
        '1d': Interval.INTERVAL_1_DAY,
        '1w': Interval.INTERVAL_1_WEEK,
        '1M': Interval.INTERVAL_1_MONTH
    }

    # Screener mapping
    SCREENERS = {
        'forex': 'forex',
        'crypto': 'crypto',
        'stocks': 'america',
        'cfd': 'cfd'
    }

    # Exchange mapping for forex
    FOREX_EXCHANGE = 'FX_IDC'
    OANDA_EXCHANGE = 'OANDA'

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize TradingView client

        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.timeout = config.get('timeout', 10)
        self.rate_limit_delay = 3  # Seconds between requests (conservative to avoid 429)

        logger.info("TradingView client initialized")

    def _get_handler(
        self,
        symbol: str,
        screener: str = 'forex',
        exchange: str = 'FX_IDC',
        interval: str = '15m'
    ) -> TA_Handler:
        """
        Create TA_Handler for a symbol

        Args:
            symbol: Trading symbol
            screener: Market screener
            exchange: Exchange name
            interval: Time interval

        Returns:
            TA_Handler instance
        """
        # Normalize symbol for TradingView
        tv_symbol = symbol.replace('_', '')  # EUR_USD -> EURUSD

        interval_obj = self.INTERVALS.get(interval, Interval.INTERVAL_15_MINUTES)

        return TA_Handler(
            symbol=tv_symbol,
            screener=screener,
            exchange=exchange,
            interval=interval_obj,
            timeout=self.timeout
        )

    def get_analysis(
        self,
        symbol: str,
        interval: str = '15m',
        screener: str = 'forex',
        exchange: str = 'FX_IDC',
        max_retries: int = 3
    ) -> Dict[str, Any]:
        """
        Get complete technical analysis for a symbol

        Args:
            symbol: Trading symbol (e.g., "EUR_USD")
            interval: Time interval
            screener: Market screener
            exchange: Exchange name
            max_retries: Maximum number of retries on rate limiting

        Returns:
            Complete analysis including indicators and recommendation
        """
        last_error = None

        for attempt in range(max_retries + 1):
            try:
                handler = self._get_handler(symbol, screener, exchange, interval)
                analysis = handler.get_analysis()

                # Success - break retry loop
                break

            except Exception as e:
                last_error = e
                error_msg = str(e)

                # Check if it's a rate limiting error (429)
                if 'HTTP status code: 429' in error_msg or '429' in error_msg:
                    if attempt < max_retries:
                        # Exponential backoff: 3s, 6s, 12s
                        delay = 3 * (2 ** attempt)
                        logger.warning(f"Rate limited for {symbol}, retrying in {delay}s (attempt {attempt + 1}/{max_retries})")
                        time.sleep(delay)
                        continue

                # Non-retryable error or max retries reached
                logger.error(f"Failed to get TradingView analysis for {symbol}: {error_msg}")
                return self._empty_analysis(symbol, interval)

        # If we got here without breaking, all retries failed
        if last_error:
            logger.error(f"Failed to get TradingView analysis for {symbol} after {max_retries} retries: {str(last_error)}")
            return self._empty_analysis(symbol, interval)

        # Extract data from successful analysis
        try:
            indicators = analysis.indicators
            summary = analysis.summary

            result = {
                'symbol': symbol,
                'interval': interval,
                'timestamp': datetime.now(),

                # Price data
                'price': {
                    'current': indicators.get('close'),
                    'open': indicators.get('open'),
                    'high': indicators.get('high'),
                    'low': indicators.get('low'),
                    'change': indicators.get('change'),
                    'change_pct': indicators.get('Change'),
                },

                # Technical indicators
                'indicators': {
                    # Trend
                    'ema_20': indicators.get('EMA20'),
                    'ema_50': indicators.get('EMA50'),
                    'ema_200': indicators.get('EMA200'),
                    'sma_20': indicators.get('SMA20'),
                    'sma_50': indicators.get('SMA50'),
                    'sma_200': indicators.get('SMA200'),

                    # Momentum
                    'rsi': indicators.get('RSI'),
                    'macd': indicators.get('MACD.macd'),
                    'macd_signal': indicators.get('MACD.signal'),
                    'stoch_k': indicators.get('Stoch.K'),
                    'stoch_d': indicators.get('Stoch.D'),
                    'cci': indicators.get('CCI20'),
                    'adx': indicators.get('ADX'),
                    'momentum': indicators.get('Mom'),

                    # Volatility
                    'atr': indicators.get('ATR'),
                    'bb_upper': indicators.get('BB.upper'),
                    'bb_lower': indicators.get('BB.lower'),
                    'bb_middle': indicators.get('BB.middle'),

                    # Volume
                    'volume': indicators.get('volume'),
                    'volume_ma': indicators.get('VWMA'),

                    # Pivot points
                    'pivot_m_r1': indicators.get('Pivot.M.Classic.R1'),
                    'pivot_m_s1': indicators.get('Pivot.M.Classic.S1'),
                },

                # Recommendation summary
                'recommendation': {
                    'overall': summary.get('RECOMMENDATION'),
                    'buy_signals': summary.get('BUY', 0),
                    'sell_signals': summary.get('SELL', 0),
                    'neutral_signals': summary.get('NEUTRAL', 0),

                    # Breakdown by type
                    'ma_recommendation': summary.get('RECOMMENDATION_MA'),
                    'oscillator_recommendation': summary.get('RECOMMENDATION_OTHER'),
                }
            }

            logger.debug(f"Analysis retrieved for {symbol} ({interval}): {result['recommendation']['overall']}")
            return result

        except Exception as e:
            logger.error(f"Failed to get TradingView analysis for {symbol}: {str(e)}")
            return self._empty_analysis(symbol, interval)

    def get_multiple_intervals(
        self,
        symbol: str,
        intervals: List[str] = ['15m', '1h', '4h'],
        screener: str = 'forex',
        exchange: str = 'FX_IDC'
    ) -> Dict[str, Dict[str, Any]]:
        """
        Get analysis for multiple timeframes

        Args:
            symbol: Trading symbol
            intervals: List of intervals
            screener: Market screener
            exchange: Exchange name

        Returns:
            Dictionary mapping interval to analysis
        """
        results = {}

        for interval in intervals:
            try:
                analysis = self.get_analysis(symbol, interval, screener, exchange)
                results[interval] = analysis

                # Rate limiting
                time.sleep(self.rate_limit_delay)

            except Exception as e:
                logger.error(f"Failed to get analysis for {symbol} {interval}: {str(e)}")
                results[interval] = self._empty_analysis(symbol, interval)

        return results

    def get_indicators(
        self,
        symbol: str,
        interval: str = '15m',
        screener: str = 'forex',
        exchange: str = 'FX_IDC'
    ) -> Dict[str, Any]:
        """
        Get only technical indicators (faster than full analysis)

        Args:
            symbol: Trading symbol
            interval: Time interval
            screener: Market screener
            exchange: Exchange name

        Returns:
            Technical indicators
        """
        analysis = self.get_analysis(symbol, interval, screener, exchange)
        return analysis.get('indicators', {})

    def get_recommendation(
        self,
        symbol: str,
        interval: str = '15m',
        screener: str = 'forex',
        exchange: str = 'FX_IDC'
    ) -> str:
        """
        Get trading recommendation (BUY/SELL/NEUTRAL)

        Args:
            symbol: Trading symbol
            interval: Time interval
            screener: Market screener
            exchange: Exchange name

        Returns:
            Recommendation string
        """
        analysis = self.get_analysis(symbol, interval, screener, exchange)
        return analysis.get('recommendation', {}).get('overall', 'NEUTRAL')

    def get_signal_strength(
        self,
        symbol: str,
        interval: str = '15m',
        screener: str = 'forex',
        exchange: str = 'FX_IDC'
    ) -> float:
        """
        Calculate signal strength from buy/sell ratio

        Args:
            symbol: Trading symbol
            interval: Time interval
            screener: Market screener
            exchange: Exchange name

        Returns:
            Signal strength (-1 to 1, negative = bearish, positive = bullish)
        """
        analysis = self.get_analysis(symbol, interval, screener, exchange)
        recommendation = analysis.get('recommendation', {})

        buy = recommendation.get('buy_signals', 0)
        sell = recommendation.get('sell_signals', 0)
        neutral = recommendation.get('neutral_signals', 0)

        total = buy + sell + neutral

        if total == 0:
            return 0.0

        # Calculate normalized score
        score = (buy - sell) / total

        return score

    def check_trend_alignment(
        self,
        symbol: str,
        intervals: List[str] = ['15m', '1h', '4h'],
        screener: str = 'forex',
        exchange: str = 'FX_IDC'
    ) -> Dict[str, Any]:
        """
        Check if multiple timeframes align on trend

        Args:
            symbol: Trading symbol
            intervals: Timeframes to check
            screener: Market screener
            exchange: Exchange name

        Returns:
            Trend alignment analysis
        """
        analyses = self.get_multiple_intervals(symbol, intervals, screener, exchange)

        buy_count = 0
        sell_count = 0
        neutral_count = 0

        for interval, analysis in analyses.items():
            rec = analysis.get('recommendation', {}).get('overall', 'NEUTRAL')

            if rec == 'BUY' or rec == 'STRONG_BUY':
                buy_count += 1
            elif rec == 'SELL' or rec == 'STRONG_SELL':
                sell_count += 1
            else:
                neutral_count += 1

        total = len(intervals)

        return {
            'symbol': symbol,
            'intervals_checked': intervals,
            'buy_count': buy_count,
            'sell_count': sell_count,
            'neutral_count': neutral_count,
            'bullish_alignment': buy_count / total,
            'bearish_alignment': sell_count / total,
            'aligned': buy_count >= total * 0.67 or sell_count >= total * 0.67,
            'direction': 'BUY' if buy_count > sell_count else ('SELL' if sell_count > buy_count else 'NEUTRAL')
        }

    def _empty_analysis(self, symbol: str, interval: str) -> Dict[str, Any]:
        """Return empty analysis structure"""
        return {
            'symbol': symbol,
            'interval': interval,
            'timestamp': datetime.now(),
            'price': {},
            'indicators': {},
            'recommendation': {
                'overall': 'NEUTRAL',
                'buy_signals': 0,
                'sell_signals': 0,
                'neutral_signals': 0
            }
        }

    # Batch operations

    def scan_multiple_symbols(
        self,
        symbols: List[str],
        interval: str = '15m',
        screener: str = 'forex',
        exchange: str = 'FX_IDC'
    ) -> Dict[str, Dict[str, Any]]:
        """
        Scan multiple symbols

        Args:
            symbols: List of symbols
            interval: Time interval
            screener: Market screener
            exchange: Exchange name

        Returns:
            Dictionary mapping symbol to analysis
        """
        results = {}

        for symbol in symbols:
            try:
                analysis = self.get_analysis(symbol, interval, screener, exchange)
                results[symbol] = analysis

                # Rate limiting
                time.sleep(self.rate_limit_delay)

            except Exception as e:
                logger.error(f"Failed to scan {symbol}: {str(e)}")
                results[symbol] = self._empty_analysis(symbol, interval)

        return results

    def get_top_movers(
        self,
        symbols: List[str],
        interval: str = '15m',
        screener: str = 'forex',
        exchange: str = 'FX_IDC',
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Get top moving symbols by price change

        Args:
            symbols: List of symbols to check
            interval: Time interval
            screener: Market screener
            exchange: Exchange name
            limit: Number of top movers to return

        Returns:
            List of top movers with their data
        """
        analyses = self.scan_multiple_symbols(symbols, interval, screener, exchange)

        movers = []
        for symbol, analysis in analyses.items():
            change_pct = analysis.get('price', {}).get('change_pct', 0)

            if change_pct is not None:
                movers.append({
                    'symbol': symbol,
                    'change_pct': abs(change_pct),
                    'direction': 'UP' if change_pct > 0 else 'DOWN',
                    'analysis': analysis
                })

        # Sort by absolute change percentage
        movers.sort(key=lambda x: x['change_pct'], reverse=True)

        return movers[:limit]
