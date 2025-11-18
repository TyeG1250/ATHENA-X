"""
ATHENA-X Sentiment Analysis Agent
Analyzes news and social media sentiment
"""

from typing import Dict, Any, List, Optional
from loguru import logger
import numpy as np

from .base_agent import BaseAgent


class SentimentAnalysisAgent(BaseAgent):
    """
    Sentiment Analysis Agent

    Analyzes:
    - News sentiment (FinBERT)
    - Social media sentiment (Reddit, Twitter)
    - Sentiment trends over time
    - Sentiment divergence from price
    - Conviction levels
    """

    def __init__(self, name: str = "SentimentAgent", config: Dict[str, Any] = None):
        if config is None:
            config = {}

        super().__init__(
            name=name,
            role="Sentiment Analyst",
            config=config,
            weight=config.get('weight', 0.20)
        )

        # Sentiment thresholds
        self.bullish_threshold = config.get('bullish_threshold', 0.3)
        self.bearish_threshold = config.get('bearish_threshold', -0.3)
        self.min_conviction = config.get('min_conviction', 0.7)

        # Component weights
        self.weights = {
            'news': 0.60,
            'social': 0.40
        }

        logger.info(f"{name} initialized - news: {self.weights['news']}, social: {self.weights['social']}")

    def analyze(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform comprehensive sentiment analysis

        Args:
            market_data: Complete market data from pipeline

        Returns:
            Sentiment analysis results
        """
        symbol = market_data.get('symbol')
        logger.debug(f"{self.name} analyzing {symbol}")

        analysis = {
            'symbol': symbol,
            'timestamp': market_data.get('timestamp'),
            'news_sentiment': None,
            'social_sentiment': None,
            'combined_sentiment': 0.0,
            'conviction': 0.0,
            'confidence': 0.0,
            'signals': []
        }

        # Extract sentiment data
        news_sentiment = market_data.get('news_sentiment')
        social_sentiment = market_data.get('social_sentiment')

        # Analyze news sentiment
        if news_sentiment:
            analysis['news_sentiment'] = self._analyze_news_sentiment(news_sentiment)

        # Analyze social sentiment
        if social_sentiment:
            analysis['social_sentiment'] = self._analyze_social_sentiment(social_sentiment)

        # Combine sentiments
        analysis['combined_sentiment'] = self._combine_sentiments(
            analysis['news_sentiment'],
            analysis['social_sentiment']
        )

        # Calculate conviction and confidence
        analysis['conviction'] = self._calculate_conviction(
            analysis['news_sentiment'],
            analysis['social_sentiment']
        )

        analysis['confidence'] = self._calculate_confidence(
            analysis['news_sentiment'],
            analysis['social_sentiment']
        )

        # Generate signals
        analysis['signals'] = self._generate_signals(analysis)

        logger.debug(
            f"{self.name} combined sentiment: {analysis['combined_sentiment']:.2f}, "
            f"conviction: {analysis['conviction']:.2%}"
        )

        return analysis

    def _analyze_news_sentiment(self, news_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze news sentiment"""
        if not news_data:
            return None

        analysis = {
            'score': news_data.get('aggregate_score', 0.0),
            'sentiment': news_data.get('aggregate_sentiment', 'neutral'),
            'confidence': news_data.get('confidence', 0.0),
            'article_count': news_data.get('count', 0),
            'positive_count': news_data.get('positive_count', 0),
            'negative_count': news_data.get('negative_count', 0),
            'neutral_count': news_data.get('neutral_count', 0),
            'signal': 'neutral'
        }

        # Determine signal strength
        score = analysis['score']
        confidence = analysis['confidence']

        if score > self.bullish_threshold and confidence > 0.6:
            analysis['signal'] = 'bullish'
        elif score < self.bearish_threshold and confidence > 0.6:
            analysis['signal'] = 'bearish'
        else:
            analysis['signal'] = 'neutral'

        return analysis

    def _analyze_social_sentiment(self, social_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze social media sentiment"""
        if not social_data:
            return None

        analysis = {
            'mention_count': social_data.get('mention_count', 0),
            'avg_score': social_data.get('avg_score', 0),
            'avg_upvote_ratio': social_data.get('avg_upvote_ratio', 0.5),
            'total_comments': social_data.get('total_comments', 0),
            'sentiment': social_data.get('sentiment', 'neutral'),
            'signal': 'neutral'
        }

        # Normalize social sentiment to -1 to 1 scale
        if analysis['mention_count'] > 0:
            # Combine score and upvote ratio
            score_norm = min(1.0, max(-1.0, analysis['avg_score'] / 100))  # Normalize Reddit score
            ratio_norm = (analysis['avg_upvote_ratio'] - 0.5) * 2  # Convert 0-1 to -1 to 1

            social_score = (score_norm * 0.6 + ratio_norm * 0.4)
            analysis['score'] = social_score

            # Determine signal
            if social_score > 0.3 and analysis['avg_upvote_ratio'] > 0.7:
                analysis['signal'] = 'bullish'
            elif social_score < -0.3 or analysis['avg_upvote_ratio'] < 0.4:
                analysis['signal'] = 'bearish'
            else:
                analysis['signal'] = 'neutral'
        else:
            analysis['score'] = 0.0

        return analysis

    def _combine_sentiments(
        self,
        news: Optional[Dict[str, Any]],
        social: Optional[Dict[str, Any]]
    ) -> float:
        """Combine news and social sentiment with weights"""

        # Extract scores
        news_score = news.get('score', 0.0) if news else 0.0
        social_score = social.get('score', 0.0) if social else 0.0

        # If only one source available, use it
        if news and not social:
            return news_score
        elif social and not news:
            return social_score
        elif not news and not social:
            return 0.0

        # Weighted combination
        combined = (
            news_score * self.weights['news'] +
            social_score * self.weights['social']
        )

        return combined

    def _calculate_conviction(
        self,
        news: Optional[Dict[str, Any]],
        social: Optional[Dict[str, Any]]
    ) -> float:
        """
        Calculate conviction level (how strong the sentiment is)

        High conviction when:
        - Both news and social agree
        - High confidence in both sources
        - Large number of mentions
        """
        if not news and not social:
            return 0.0

        conviction_factors = []

        # News conviction
        if news:
            news_conviction = abs(news.get('score', 0.0)) * news.get('confidence', 0.0)
            conviction_factors.append(news_conviction)

        # Social conviction
        if social:
            mention_count = social.get('mention_count', 0)
            score = abs(social.get('score', 0.0))

            # More mentions = higher conviction
            mention_factor = min(1.0, mention_count / 10)  # Cap at 10 mentions

            social_conviction = score * mention_factor
            conviction_factors.append(social_conviction)

        # Agreement bonus
        if news and social:
            news_signal = news.get('signal')
            social_signal = social.get('signal')

            if news_signal == social_signal and news_signal != 'neutral':
                # Both agree on direction - boost conviction
                avg_conviction = sum(conviction_factors) / len(conviction_factors)
                conviction_factors.append(avg_conviction * 0.3)  # 30% bonus

        # Average conviction
        if conviction_factors:
            return min(1.0, sum(conviction_factors) / len(conviction_factors))
        else:
            return 0.0

    def _calculate_confidence(
        self,
        news: Optional[Dict[str, Any]],
        social: Optional[Dict[str, Any]]
    ) -> float:
        """Calculate confidence in sentiment analysis"""
        confidence_factors = []

        # News confidence
        if news:
            news_confidence = news.get('confidence', 0.0)
            article_count = news.get('article_count', 0)

            # More articles = higher confidence
            count_factor = min(1.0, article_count / 10)  # Cap at 10 articles

            news_conf = news_confidence * 0.7 + count_factor * 0.3
            confidence_factors.append(news_conf)

        # Social confidence
        if social:
            mention_count = social.get('mention_count', 0)
            total_comments = social.get('total_comments', 0)

            # More mentions and comments = higher confidence
            mention_factor = min(1.0, mention_count / 5)
            comment_factor = min(1.0, total_comments / 50)

            social_conf = (mention_factor * 0.5 + comment_factor * 0.5)
            confidence_factors.append(social_conf)

        # Agreement bonus
        if news and social:
            if news.get('signal') == social.get('signal'):
                # Both sources agree - boost confidence
                confidence_factors.append(0.9)
            else:
                # Disagreement - lower confidence
                confidence_factors.append(0.4)

        # Average confidence
        if confidence_factors:
            return sum(confidence_factors) / len(confidence_factors)
        else:
            return 0.5

    def _generate_signals(self, analysis: Dict[str, Any]) -> List[str]:
        """Generate human-readable signals"""
        signals = []

        # Combined sentiment
        combined = analysis['combined_sentiment']
        conviction = analysis['conviction']

        if abs(combined) > 0.3:
            direction = 'bullish' if combined > 0 else 'bearish'
            signals.append(f"Overall sentiment: {direction} ({combined:+.2f})")

        if conviction > 0.7:
            signals.append(f"High conviction ({conviction:.2%})")

        # News signals
        news = analysis.get('news_sentiment')
        if news:
            count = news.get('article_count', 0)
            sentiment = news.get('sentiment', 'neutral')
            signals.append(f"News: {sentiment} ({count} articles)")

            if news.get('signal') != 'neutral':
                signals.append(f"News signal: {news['signal']}")

        # Social signals
        social = analysis.get('social_sentiment')
        if social:
            mentions = social.get('mention_count', 0)
            sentiment = social.get('sentiment', 'neutral')

            if mentions > 0:
                signals.append(f"Social: {sentiment} ({mentions} mentions)")

                if social.get('signal') != 'neutral':
                    signals.append(f"Social signal: {social['signal']}")

        return signals

    def vote(self, analysis: Dict[str, Any]) -> str:
        """
        Generate trading vote based on sentiment analysis

        Args:
            analysis: Sentiment analysis results

        Returns:
            Vote: 'BUY', 'SELL', or 'NEUTRAL'
        """
        combined_sentiment = analysis.get('combined_sentiment', 0.0)
        conviction = analysis.get('conviction', 0.0)
        confidence = analysis.get('confidence', 0.0)

        # Require minimum conviction and confidence
        if conviction < self.min_conviction or confidence < self.confidence_threshold:
            logger.debug(
                f"{self.name} insufficient conviction/confidence: "
                f"{conviction:.2%}/{confidence:.2%}"
            )
            return 'NEUTRAL'

        # Vote based on sentiment
        if combined_sentiment > self.bullish_threshold:
            return 'BUY'
        elif combined_sentiment < self.bearish_threshold:
            return 'SELL'
        else:
            return 'NEUTRAL'

    def get_reasoning(self, analysis: Dict[str, Any]) -> str:
        """Generate detailed reasoning"""
        vote = self.vote(analysis)
        sentiment = analysis.get('combined_sentiment', 0.0)
        conviction = analysis.get('conviction', 0.0)
        confidence = analysis.get('confidence', 0.0)
        signals = analysis.get('signals', [])

        reasoning = (
            f"{self.name}: {vote} "
            f"(sentiment: {sentiment:+.2f}, conviction: {conviction:.2%}, "
            f"confidence: {confidence:.2%})\n"
        )

        reasoning += "Key signals:\n"
        for signal in signals[:5]:  # Top 5 signals
            reasoning += f"  - {signal}\n"

        return reasoning
