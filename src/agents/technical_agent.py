"""
ATHENA-X Technical Analysis Agent
Analyzes price action, indicators, patterns, and trends
"""

from typing import Dict, Any, List, Optional
from loguru import logger
import numpy as np

from .base_agent import BaseAgent


class TechnicalAnalysisAgent(BaseAgent):
    """
    Technical Analysis Agent

    Analyzes:
    - Trend direction (EMA crossovers, ADX)
    - Momentum (RSI, MACD, Stochastic)
    - Volatility (Bollinger Bands, ATR)
    - Volume analysis
    - Support/Resistance levels
    - Chart patterns
    """

    def __init__(self, name: str = "TechnicalAgent", config: Dict[str, Any] = None):
        if config is None:
            config = {}

        super().__init__(
            name=name,
            role="Technical Analyst",
            config=config,
            weight=config.get('weight', 0.35)
        )

        # Technical analysis parameters
        self.rsi_oversold = config.get('rsi_oversold', 30)
        self.rsi_overbought = config.get('rsi_overbought', 70)
        self.macd_threshold = config.get('macd_threshold', 0.0)
        self.trend_threshold = config.get('trend_threshold', 0.7)

        # Indicator weights
        self.indicator_weights = {
            'trend': 0.30,
            'momentum': 0.25,
            'volume': 0.15,
            'volatility': 0.15,
            'patterns': 0.15
        }

        logger.info(f"{name} initialized with {len(self.indicator_weights)} analysis components")

    def analyze(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform comprehensive technical analysis

        Args:
            market_data: Complete market data from pipeline

        Returns:
            Technical analysis results
        """
        symbol = market_data.get('symbol')
        logger.debug(f"{self.name} analyzing {symbol}")

        analysis = {
            'symbol': symbol,
            'timestamp': market_data.get('timestamp'),
            'trend': None,
            'momentum': None,
            'volume': None,
            'volatility': None,
            'patterns': None,
            'score': 0.0,
            'confidence': 0.0,
            'signals': []
        }

        # Extract data
        indicators = market_data.get('technical_indicators', {})
        tradingview = market_data.get('tradingview_analysis', {})
        price_data = market_data.get('price_data', {})

        if not indicators and not tradingview:
            logger.warning(f"No technical data available for {symbol}")
            return analysis

        # Analyze components
        analysis['trend'] = self._analyze_trend(indicators, tradingview)
        analysis['momentum'] = self._analyze_momentum(indicators)
        analysis['volume'] = self._analyze_volume(indicators)
        analysis['volatility'] = self._analyze_volatility(indicators)
        analysis['patterns'] = self._detect_patterns(indicators, tradingview)

        # Calculate overall score
        analysis['score'] = self._calculate_score(analysis)
        analysis['confidence'] = self._calculate_confidence(analysis)
        analysis['signals'] = self._generate_signals(analysis)

        logger.debug(f"{self.name} score: {analysis['score']:.2f}, confidence: {analysis['confidence']:.2%}")

        return analysis

    def _analyze_trend(
        self,
        indicators: Dict[str, Any],
        tradingview: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze trend direction and strength"""
        trend = {
            'direction': 'neutral',
            'strength': 0.0,
            'ema_alignment': False,
            'adx': 0.0,
            'aligned_timeframes': []
        }

        if not indicators:
            return trend

        # EMA analysis
        ema_20 = indicators.get('ema_20')
        ema_50 = indicators.get('ema_50')
        ema_200 = indicators.get('ema_200')
        close = indicators.get('close')

        if all([ema_20, ema_50, close]):
            # Determine trend direction
            if ema_20 > ema_50:
                trend['direction'] = 'uptrend'
                trend['ema_alignment'] = True
            elif ema_20 < ema_50:
                trend['direction'] = 'downtrend'
                trend['ema_alignment'] = True
            else:
                trend['direction'] = 'neutral'

            # Calculate trend strength (0-1)
            if ema_50 != 0:
                trend['strength'] = abs((ema_20 - ema_50) / ema_50)

        # ADX (trend strength indicator)
        adx = indicators.get('adx')
        if adx:
            trend['adx'] = adx

            # Strong trend if ADX > 25
            if adx > 25:
                trend['strength'] = max(trend['strength'], adx / 100)

        # Multi-timeframe alignment (from TradingView)
        if tradingview:
            for interval, data in tradingview.items():
                recommendation = data.get('recommendation', {}).get('overall')
                if recommendation in ['BUY', 'STRONG_BUY']:
                    trend['aligned_timeframes'].append(f"{interval}_bullish")
                elif recommendation in ['SELL', 'STRONG_SELL']:
                    trend['aligned_timeframes'].append(f"{interval}_bearish")

        return trend

    def _analyze_momentum(self, indicators: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze momentum indicators"""
        momentum = {
            'rsi': None,
            'rsi_signal': 'neutral',
            'macd': None,
            'macd_signal': 'neutral',
            'stochastic': None,
            'stoch_signal': 'neutral',
            'score': 0.0
        }

        if not indicators:
            return momentum

        # RSI analysis
        rsi = indicators.get('rsi')
        if rsi is not None:
            momentum['rsi'] = rsi

            if rsi < self.rsi_oversold:
                momentum['rsi_signal'] = 'oversold'
            elif rsi > self.rsi_overbought:
                momentum['rsi_signal'] = 'overbought'
            elif 40 < rsi < 60:
                momentum['rsi_signal'] = 'neutral'
            elif rsi > 50:
                momentum['rsi_signal'] = 'bullish'
            else:
                momentum['rsi_signal'] = 'bearish'

        # MACD analysis
        macd = indicators.get('macd')
        macd_signal = indicators.get('macd_signal')

        if macd is not None and macd_signal is not None:
            momentum['macd'] = macd - macd_signal

            if momentum['macd'] > self.macd_threshold:
                momentum['macd_signal'] = 'bullish'
            elif momentum['macd'] < -self.macd_threshold:
                momentum['macd_signal'] = 'bearish'
            else:
                momentum['macd_signal'] = 'neutral'

        # Stochastic oscillator
        stoch_k = indicators.get('stoch_k')
        stoch_d = indicators.get('stoch_d')

        if stoch_k is not None and stoch_d is not None:
            momentum['stochastic'] = {'k': stoch_k, 'd': stoch_d}

            if stoch_k < 20:
                momentum['stoch_signal'] = 'oversold'
            elif stoch_k > 80:
                momentum['stoch_signal'] = 'overbought'
            elif stoch_k > stoch_d:
                momentum['stoch_signal'] = 'bullish'
            else:
                momentum['stoch_signal'] = 'bearish'

        # Calculate momentum score (-1 to 1)
        signals = [
            momentum['rsi_signal'],
            momentum['macd_signal'],
            momentum['stoch_signal']
        ]

        bullish = sum(1 for s in signals if s in ['bullish', 'oversold'])
        bearish = sum(1 for s in signals if s in ['bearish', 'overbought'])

        if len(signals) > 0:
            momentum['score'] = (bullish - bearish) / len(signals)

        return momentum

    def _analyze_volume(self, indicators: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze volume patterns"""
        volume_analysis = {
            'current_volume': None,
            'avg_volume': None,
            'relative_volume': 0.0,
            'signal': 'neutral'
        }

        if not indicators:
            return volume_analysis

        volume = indicators.get('volume')
        avg_volume = indicators.get('volume_sma')

        if volume and avg_volume and avg_volume > 0:
            volume_analysis['current_volume'] = volume
            volume_analysis['avg_volume'] = avg_volume
            volume_analysis['relative_volume'] = volume / avg_volume

            # High volume confirmation
            if volume_analysis['relative_volume'] > 1.5:
                volume_analysis['signal'] = 'high_volume'
            elif volume_analysis['relative_volume'] < 0.5:
                volume_analysis['signal'] = 'low_volume'
            else:
                volume_analysis['signal'] = 'normal'

        return volume_analysis

    def _analyze_volatility(self, indicators: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze volatility indicators"""
        volatility = {
            'atr': None,
            'bb_width': None,
            'bb_position': None,
            'signal': 'normal'
        }

        if not indicators:
            return volatility

        # Average True Range
        atr = indicators.get('atr')
        if atr:
            volatility['atr'] = atr

        # Bollinger Bands
        bb_upper = indicators.get('bb_upper')
        bb_lower = indicators.get('bb_lower')
        bb_middle = indicators.get('bb_middle')
        close = indicators.get('close')

        if all([bb_upper, bb_lower, bb_middle, close]):
            # Band width (volatility measure)
            volatility['bb_width'] = (bb_upper - bb_lower) / bb_middle

            # Price position within bands
            if bb_upper != bb_lower:
                volatility['bb_position'] = (close - bb_lower) / (bb_upper - bb_lower)

                # Signals
                if close >= bb_upper:
                    volatility['signal'] = 'overbought'
                elif close <= bb_lower:
                    volatility['signal'] = 'oversold'
                else:
                    volatility['signal'] = 'normal'

        return volatility

    def _detect_patterns(
        self,
        indicators: Dict[str, Any],
        tradingview: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Detect chart patterns"""
        patterns = {
            'detected': [],
            'bullish_count': 0,
            'bearish_count': 0,
            'score': 0.0
        }

        # TradingView pattern detection (if available)
        if tradingview:
            for interval, data in tradingview.items():
                recommendation = data.get('recommendation', {})
                summary = recommendation.get('overall')

                if summary in ['STRONG_BUY', 'BUY']:
                    patterns['bullish_count'] += 1
                    patterns['detected'].append(f"{interval}_bullish_pattern")
                elif summary in ['STRONG_SELL', 'SELL']:
                    patterns['bearish_count'] += 1
                    patterns['detected'].append(f"{interval}_bearish_pattern")

        # Calculate pattern score
        total = patterns['bullish_count'] + patterns['bearish_count']
        if total > 0:
            patterns['score'] = (patterns['bullish_count'] - patterns['bearish_count']) / total

        return patterns

    def _calculate_score(self, analysis: Dict[str, Any]) -> float:
        """Calculate weighted technical score"""
        score = 0.0

        # Trend score
        if analysis['trend']:
            trend = analysis['trend']
            if trend['direction'] == 'uptrend':
                score += self.indicator_weights['trend'] * trend['strength']
            elif trend['direction'] == 'downtrend':
                score -= self.indicator_weights['trend'] * trend['strength']

        # Momentum score
        if analysis['momentum']:
            momentum_score = analysis['momentum'].get('score', 0.0)
            score += self.indicator_weights['momentum'] * momentum_score

        # Volume score (confirmation)
        if analysis['volume']:
            volume_signal = analysis['volume']['signal']
            if volume_signal == 'high_volume':
                score *= 1.2  # Amplify signal with high volume
            elif volume_signal == 'low_volume':
                score *= 0.8  # Dampen signal with low volume

        # Volatility score
        if analysis['volatility']:
            vol_signal = analysis['volatility']['signal']
            if vol_signal == 'oversold':
                score += self.indicator_weights['volatility'] * 0.5
            elif vol_signal == 'overbought':
                score -= self.indicator_weights['volatility'] * 0.5

        # Pattern score
        if analysis['patterns']:
            pattern_score = analysis['patterns'].get('score', 0.0)
            score += self.indicator_weights['patterns'] * pattern_score

        # Normalize to -1 to 1
        score = max(-1.0, min(1.0, score))

        return score

    def _calculate_confidence(self, analysis: Dict[str, Any]) -> float:
        """Calculate confidence in analysis"""
        confidence_factors = []

        # Trend confidence
        if analysis['trend']:
            trend = analysis['trend']
            if trend['adx'] > 25:  # Strong trend
                confidence_factors.append(0.9)
            elif trend['ema_alignment']:
                confidence_factors.append(0.7)
            else:
                confidence_factors.append(0.5)

        # Momentum confidence
        if analysis['momentum']:
            momentum = analysis['momentum']
            # All momentum indicators agree
            signals = [momentum['rsi_signal'], momentum['macd_signal'], momentum['stoch_signal']]
            bullish = sum(1 for s in signals if s in ['bullish', 'oversold'])
            bearish = sum(1 for s in signals if s in ['bearish', 'overbought'])

            if bullish == len(signals) or bearish == len(signals):
                confidence_factors.append(0.9)  # Perfect agreement
            elif bullish > bearish or bearish > bullish:
                confidence_factors.append(0.7)  # Majority agreement
            else:
                confidence_factors.append(0.5)  # Disagreement

        # Volume confidence
        if analysis['volume']:
            volume = analysis['volume']
            if volume['signal'] == 'high_volume':
                confidence_factors.append(0.8)  # High volume confirmation
            else:
                confidence_factors.append(0.6)

        # Pattern confidence
        if analysis['patterns']:
            patterns = analysis['patterns']
            total = patterns['bullish_count'] + patterns['bearish_count']
            if total >= 2:  # Multiple timeframes agree
                confidence_factors.append(0.8)
            elif total == 1:
                confidence_factors.append(0.6)
            else:
                confidence_factors.append(0.4)

        # Average confidence
        if confidence_factors:
            return sum(confidence_factors) / len(confidence_factors)
        else:
            return 0.5

    def _generate_signals(self, analysis: Dict[str, Any]) -> List[str]:
        """Generate human-readable signals"""
        signals = []

        # Trend signals
        if analysis['trend']:
            trend = analysis['trend']
            signals.append(f"Trend: {trend['direction']} (strength: {trend['strength']:.2f})")

            if trend['adx'] > 25:
                signals.append(f"Strong trend confirmed (ADX: {trend['adx']:.1f})")

        # Momentum signals
        if analysis['momentum']:
            momentum = analysis['momentum']

            if momentum['rsi_signal'] == 'oversold':
                signals.append(f"RSI oversold ({momentum['rsi']:.1f})")
            elif momentum['rsi_signal'] == 'overbought':
                signals.append(f"RSI overbought ({momentum['rsi']:.1f})")

            if momentum['macd_signal'] != 'neutral':
                signals.append(f"MACD {momentum['macd_signal']}")

        # Volume signals
        if analysis['volume']:
            volume = analysis['volume']
            if volume['signal'] == 'high_volume':
                signals.append(f"High volume ({volume['relative_volume']:.1f}x average)")

        # Volatility signals
        if analysis['volatility']:
            volatility = analysis['volatility']
            if volatility['signal'] in ['oversold', 'overbought']:
                signals.append(f"Bollinger Bands: {volatility['signal']}")

        return signals

    def vote(self, analysis: Dict[str, Any]) -> str:
        """
        Generate trading vote based on technical analysis

        Args:
            analysis: Technical analysis results

        Returns:
            Vote: 'BUY', 'SELL', or 'NEUTRAL'
        """
        score = analysis.get('score', 0.0)
        confidence = analysis.get('confidence', 0.0)

        # Require minimum confidence
        if confidence < self.confidence_threshold:
            logger.debug(f"{self.name} insufficient confidence: {confidence:.2%}")
            return 'NEUTRAL'

        # Vote based on score
        if score > 0.30:  # Bullish threshold
            return 'BUY'
        elif score < -0.30:  # Bearish threshold
            return 'SELL'
        else:
            return 'NEUTRAL'

    def get_reasoning(self, analysis: Dict[str, Any]) -> str:
        """Generate detailed reasoning"""
        vote = self.vote(analysis)
        score = analysis.get('score', 0.0)
        confidence = analysis.get('confidence', 0.0)
        signals = analysis.get('signals', [])

        reasoning = f"{self.name}: {vote} (score: {score:.2f}, confidence: {confidence:.2%})\n"
        reasoning += "Key signals:\n"
        for signal in signals[:5]:  # Top 5 signals
            reasoning += f"  - {signal}\n"

        return reasoning
