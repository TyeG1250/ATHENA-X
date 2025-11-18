"""
ATHENA-X FinBERT Sentiment Analysis
Financial sentiment analysis using FinBERT
"""

import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from typing import List, Dict, Any, Optional
import numpy as np
from loguru import logger
from pathlib import Path


class FinBERTSentiment:
    """
    FinBERT sentiment analyzer for financial text
    """

    def __init__(
        self,
        model_name: str = "ProsusAI/finbert",
        device: Optional[str] = None,
        cache_dir: Optional[str] = None
    ):
        """
        Initialize FinBERT model

        Args:
            model_name: Model identifier
            device: Device to use (cuda/cpu)
            cache_dir: Model cache directory
        """
        self.model_name = model_name

        # Determine device
        if device is None:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device

        # Set cache directory
        if cache_dir:
            self.cache_dir = Path(cache_dir)
        else:
            self.cache_dir = Path("data/models/finbert")

        # Load model and tokenizer
        self._load_model()

        logger.info(f"FinBERT initialized on {self.device}")

    def _load_model(self):
        """Load FinBERT model and tokenizer"""
        try:
            # Check if model exists in cache
            if self.cache_dir.exists():
                logger.info(f"Loading model from cache: {self.cache_dir}")
                model_path = str(self.cache_dir)
            else:
                logger.info(f"Downloading model: {self.model_name}")
                model_path = self.model_name

            # Load tokenizer
            self.tokenizer = AutoTokenizer.from_pretrained(
                model_path,
                cache_dir=str(self.cache_dir) if not self.cache_dir.exists() else None
            )

            # Load model
            self.model = AutoModelForSequenceClassification.from_pretrained(
                model_path,
                cache_dir=str(self.cache_dir) if not self.cache_dir.exists() else None
            )

            # Move to device
            self.model.to(self.device)
            self.model.eval()

            # Save to cache if downloaded
            if not self.cache_dir.exists():
                logger.info(f"Saving model to cache: {self.cache_dir}")
                self.cache_dir.mkdir(parents=True, exist_ok=True)
                self.tokenizer.save_pretrained(str(self.cache_dir))
                self.model.save_pretrained(str(self.cache_dir))

            logger.success("FinBERT model loaded successfully")

        except Exception as e:
            logger.error(f"Failed to load FinBERT model: {str(e)}")
            raise

    def analyze_sentiment(
        self,
        text: str,
        return_probabilities: bool = False
    ) -> Dict[str, Any]:
        """
        Analyze sentiment of a single text

        Args:
            text: Text to analyze
            return_probabilities: Whether to return class probabilities

        Returns:
            Sentiment analysis result
        """
        if not text or len(text.strip()) == 0:
            return {
                'sentiment': 'neutral',
                'score': 0.0,
                'confidence': 0.0
            }

        try:
            # Tokenize
            inputs = self.tokenizer(
                text,
                return_tensors="pt",
                truncation=True,
                max_length=512,
                padding=True
            )

            # Move to device
            inputs = {k: v.to(self.device) for k, v in inputs.items()}

            # Get predictions
            with torch.no_grad():
                outputs = self.model(**inputs)
                logits = outputs.logits
                probs = torch.nn.functional.softmax(logits, dim=-1)

            # FinBERT outputs: [negative, neutral, positive]
            probs_np = probs.cpu().numpy()[0]

            negative_prob = probs_np[0]
            neutral_prob = probs_np[1]
            positive_prob = probs_np[2]

            # Determine sentiment
            if positive_prob > negative_prob and positive_prob > neutral_prob:
                sentiment = 'positive'
                confidence = positive_prob
            elif negative_prob > positive_prob and negative_prob > neutral_prob:
                sentiment = 'negative'
                confidence = negative_prob
            else:
                sentiment = 'neutral'
                confidence = neutral_prob

            # Calculate score (-1 to 1)
            score = positive_prob - negative_prob

            result = {
                'sentiment': sentiment,
                'score': float(score),
                'confidence': float(confidence)
            }

            if return_probabilities:
                result['probabilities'] = {
                    'negative': float(negative_prob),
                    'neutral': float(neutral_prob),
                    'positive': float(positive_prob)
                }

            return result

        except Exception as e:
            logger.error(f"Sentiment analysis failed: {str(e)}")
            return {
                'sentiment': 'neutral',
                'score': 0.0,
                'confidence': 0.0,
                'error': str(e)
            }

    def analyze_batch(
        self,
        texts: List[str],
        batch_size: int = 32
    ) -> List[Dict[str, Any]]:
        """
        Analyze sentiment for multiple texts

        Args:
            texts: List of texts
            batch_size: Batch size for processing

        Returns:
            List of sentiment results
        """
        results = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]

            try:
                # Tokenize batch
                inputs = self.tokenizer(
                    batch,
                    return_tensors="pt",
                    truncation=True,
                    max_length=512,
                    padding=True
                )

                # Move to device
                inputs = {k: v.to(self.device) for k, v in inputs.items()}

                # Get predictions
                with torch.no_grad():
                    outputs = self.model(**inputs)
                    logits = outputs.logits
                    probs = torch.nn.functional.softmax(logits, dim=-1)

                # Process each result
                probs_np = probs.cpu().numpy()

                for j, prob in enumerate(probs_np):
                    negative_prob = prob[0]
                    neutral_prob = prob[1]
                    positive_prob = prob[2]

                    # Determine sentiment
                    if positive_prob > negative_prob and positive_prob > neutral_prob:
                        sentiment = 'positive'
                        confidence = positive_prob
                    elif negative_prob > positive_prob and negative_prob > neutral_prob:
                        sentiment = 'negative'
                        confidence = negative_prob
                    else:
                        sentiment = 'neutral'
                        confidence = neutral_prob

                    score = positive_prob - negative_prob

                    results.append({
                        'sentiment': sentiment,
                        'score': float(score),
                        'confidence': float(confidence),
                        'text': batch[j]
                    })

            except Exception as e:
                logger.error(f"Batch analysis failed: {str(e)}")
                # Add neutral results for failed batch
                for text in batch:
                    results.append({
                        'sentiment': 'neutral',
                        'score': 0.0,
                        'confidence': 0.0,
                        'text': text,
                        'error': str(e)
                    })

        return results

    def analyze_news_articles(
        self,
        articles: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Analyze sentiment for news articles

        Args:
            articles: List of article dictionaries

        Returns:
            Articles with sentiment added
        """
        # Extract titles and summaries
        texts = []
        for article in articles:
            title = article.get('title', '')
            summary = article.get('summary', '')
            text = f"{title}. {summary}" if summary else title
            texts.append(text)

        # Analyze sentiment
        sentiments = self.analyze_batch(texts)

        # Add sentiment to articles
        for article, sentiment in zip(articles, sentiments):
            article['sentiment'] = sentiment['sentiment']
            article['sentiment_score'] = sentiment['score']
            article['sentiment_confidence'] = sentiment['confidence']

        return articles

    def aggregate_sentiment(
        self,
        sentiments: List[Dict[str, Any]],
        weight_by_confidence: bool = True
    ) -> Dict[str, Any]:
        """
        Aggregate multiple sentiment scores

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

        return {
            'aggregate_score': float(avg_score),
            'aggregate_sentiment': aggregate_sentiment,
            'confidence': float(avg_confidence),
            'count': len(sentiments),
            'positive_count': sum(1 for s in sentiments if s.get('sentiment') == 'positive'),
            'negative_count': sum(1 for s in sentiments if s.get('sentiment') == 'negative'),
            'neutral_count': sum(1 for s in sentiments if s.get('sentiment') == 'neutral')
        }

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
