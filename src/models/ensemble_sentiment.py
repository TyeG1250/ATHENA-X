"""
ATHENA-X Ensemble Sentiment Analysis
Combines multiple sentiment analysis models for robust sentiment scoring
"""

from typing import Dict, Any, List, Optional
from loguru import logger
import numpy as np

try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
    VADER_AVAILABLE = True
except ImportError:
    VADER_AVAILABLE = False
    logger.warning("VADER not available - install with: pip install vaderSentiment")

from .finbert import FinBERTSentiment


class EnsembleSentiment:
    """
    Ensemble sentiment analyzer

    Combines:
    - FinBERT (60% weight) - Financial domain-specific
    - VADER (30% weight) - General sentiment
    - TextBlob (10% weight) - Simple baseline (optional)

    Provides:
    - Robust sentiment scoring
    - Confidence weighting
    - Disagreement detection
    """

    def __init__(
        self,
        finbert_model: Optional[FinBERTSentiment] = None,
        weights: Optional[Dict[str, float]] = None
    ):
        """
        Initialize ensemble sentiment analyzer

        Args:
            finbert_model: Pre-initialized FinBERT model
            weights: Model weights (default: FinBERT 60%, VADER 30%, TextBlob 10%)
        """
        # Initialize models
        self.finbert = finbert_model if finbert_model else FinBERTSentiment()

        if VADER_AVAILABLE:
            self.vader = SentimentIntensityAnalyzer()
        else:
            self.vader = None
            logger.warning("VADER not available, using FinBERT only")

        # Set weights
        if weights is None:
            if self.vader:
                self.weights = {
                    'finbert': 0.70,
                    'vader': 0.30
                }
            else:
                # FinBERT only
                self.weights = {
                    'finbert': 1.0
                }
        else:
            self.weights = weights

        logger.info(f"Ensemble sentiment initialized: {self.weights}")

    def analyze(self, text: str) -> Dict[str, Any]:
        """
        Analyze sentiment using ensemble

        Args:
            text: Text to analyze

        Returns:
            Ensemble sentiment result
        """
        if not text or len(text.strip()) == 0:
            return {
                'sentiment': 'neutral',
                'score': 0.0,
                'confidence': 0.0,
                'ensemble': {}
            }

        scores = {}
        confidences = {}

        # FinBERT analysis
        try:
            finbert_result = self.finbert.analyze_sentiment(text)
            scores['finbert'] = finbert_result['score']
            confidences['finbert'] = finbert_result['confidence']
        except Exception as e:
            logger.error(f"FinBERT analysis failed: {str(e)}")
            scores['finbert'] = 0.0
            confidences['finbert'] = 0.0

        # VADER analysis
        if self.vader:
            try:
                vader_result = self.vader.polarity_scores(text)
                # VADER compound score is already -1 to 1
                scores['vader'] = vader_result['compound']
                # VADER doesn't provide confidence, estimate from abs(compound)
                confidences['vader'] = abs(vader_result['compound'])
            except Exception as e:
                logger.error(f"VADER analysis failed: {str(e)}")
                scores['vader'] = 0.0
                confidences['vader'] = 0.0

        # Calculate ensemble score (weighted average)
        ensemble_score = sum(
            scores.get(model, 0.0) * weight
            for model, weight in self.weights.items()
        )

        # Calculate ensemble confidence (weighted average)
        ensemble_confidence = sum(
            confidences.get(model, 0.0) * weight
            for model, weight in self.weights.items()
        )

        # Check model agreement
        agreement = self._check_agreement(scores)

        # Determine sentiment
        if ensemble_score > 0.2:
            sentiment = 'positive'
        elif ensemble_score < -0.2:
            sentiment = 'negative'
        else:
            sentiment = 'neutral'

        return {
            'sentiment': sentiment,
            'score': ensemble_score,
            'confidence': ensemble_confidence,
            'agreement': agreement,
            'models': {
                model: {
                    'score': scores.get(model, 0.0),
                    'confidence': confidences.get(model, 0.0)
                }
                for model in self.weights.keys()
            }
        }

    def analyze_batch(self, texts: List[str]) -> List[Dict[str, Any]]:
        """
        Analyze multiple texts

        Args:
            texts: List of texts

        Returns:
            List of sentiment results
        """
        results = []

        for text in texts:
            result = self.analyze(text)
            result['text'] = text[:100] + '...' if len(text) > 100 else text
            results.append(result)

        return results

    def analyze_articles(
        self,
        articles: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Analyze sentiment for news articles

        Args:
            articles: List of article dictionaries

        Returns:
            Articles with ensemble sentiment added
        """
        for article in articles:
            title = article.get('title', '')
            summary = article.get('summary', '')
            text = f"{title}. {summary}" if summary else title

            result = self.analyze(text)

            article['ensemble_sentiment'] = result['sentiment']
            article['ensemble_score'] = result['score']
            article['ensemble_confidence'] = result['confidence']
            article['model_agreement'] = result['agreement']

        return articles

    def aggregate_sentiment(
        self,
        sentiments: List[Dict[str, Any]],
        weight_by_confidence: bool = True
    ) -> Dict[str, Any]:
        """
        Aggregate multiple sentiment results

        Args:
            sentiments: List of sentiment results
            weight_by_confidence: Whether to weight by confidence

        Returns:
            Aggregated sentiment
        """
        if not sentiments:
            return {
                'aggregate_score': 0.0,
                'aggregate_sentiment': 'neutral',
                'confidence': 0.0,
                'count': 0
            }

        if weight_by_confidence:
            # Weighted average by confidence
            total_weight = sum(s.get('confidence', 0) for s in sentiments)

            if total_weight == 0:
                avg_score = 0.0
            else:
                avg_score = sum(
                    s.get('score', 0) * s.get('confidence', 0)
                    for s in sentiments
                ) / total_weight
        else:
            # Simple average
            avg_score = sum(s.get('score', 0) for s in sentiments) / len(sentiments)

        # Determine aggregate sentiment
        if avg_score > 0.2:
            aggregate_sentiment = 'positive'
        elif avg_score < -0.2:
            aggregate_sentiment = 'negative'
        else:
            aggregate_sentiment = 'neutral'

        # Calculate average confidence
        avg_confidence = sum(s.get('confidence', 0) for s in sentiments) / len(sentiments)

        # Calculate agreement across all sentiments
        scores = [s.get('score', 0) for s in sentiments]
        std_dev = np.std(scores) if len(scores) > 1 else 0.0
        agreement = max(0.0, 1.0 - std_dev)  # Lower std = higher agreement

        return {
            'aggregate_score': float(avg_score),
            'aggregate_sentiment': aggregate_sentiment,
            'confidence': float(avg_confidence),
            'agreement': float(agreement),
            'count': len(sentiments),
            'positive_count': sum(1 for s in sentiments if s.get('sentiment') == 'positive'),
            'negative_count': sum(1 for s in sentiments if s.get('sentiment') == 'negative'),
            'neutral_count': sum(1 for s in sentiments if s.get('sentiment') == 'neutral')
        }

    def _check_agreement(self, scores: Dict[str, float]) -> float:
        """
        Check agreement between models

        Args:
            scores: Dictionary of model scores

        Returns:
            Agreement score (0-1)
        """
        if len(scores) < 2:
            return 1.0  # Perfect agreement with only one model

        # Calculate standard deviation of scores
        score_values = list(scores.values())
        std_dev = np.std(score_values)

        # Convert to agreement score (0-1)
        # Low std = high agreement
        agreement = max(0.0, 1.0 - std_dev)

        return agreement

    def get_sentiment_strength(self, score: float) -> str:
        """
        Categorize sentiment strength

        Args:
            score: Sentiment score (-1 to 1)

        Returns:
            Strength category
        """
        abs_score = abs(score)

        if abs_score >= 0.7:
            return 'strong'
        elif abs_score >= 0.4:
            return 'moderate'
        else:
            return 'weak'
