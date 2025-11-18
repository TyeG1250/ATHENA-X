"""
JARVIS-X Social Media Scraper
Reddit and Twitter sentiment tracking
"""

import os
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from loguru import logger

try:
    import praw
    PRAW_AVAILABLE = True
except ImportError:
    PRAW_AVAILABLE = False
    logger.warning("PRAW not available - Reddit scraping disabled")


class SocialSentimentScraper:
    """
    Social media sentiment scraper
    Sources: Reddit (PRAW), Twitter/X (optional)
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize social sentiment scraper

        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.social_config = config.get('social_media', {})

        # Initialize Reddit
        self.reddit = None
        if self.social_config.get('reddit', {}).get('enabled', True):
            self._init_reddit()

        # Twitter/X support (optional - requires API access)
        self.twitter_enabled = self.social_config.get('twitter', {}).get('enabled', False)

        logger.info("Social sentiment scraper initialized")

    def _init_reddit(self):
        """Initialize Reddit client"""
        if not PRAW_AVAILABLE:
            logger.warning("PRAW not installed, Reddit scraping disabled")
            return

        try:
            client_id = os.getenv('REDDIT_CLIENT_ID', '')
            client_secret = os.getenv('REDDIT_CLIENT_SECRET', '')
            user_agent = os.getenv('REDDIT_USER_AGENT', 'JARVIS-X/1.0')

            if client_id and client_secret:
                self.reddit = praw.Reddit(
                    client_id=client_id,
                    client_secret=client_secret,
                    user_agent=user_agent
                )

                logger.info("Reddit client initialized")
            else:
                logger.warning("Reddit credentials not found")

        except Exception as e:
            logger.error(f"Failed to initialize Reddit client: {str(e)}")

    def scrape_reddit(
        self,
        subreddits: Optional[List[str]] = None,
        max_posts: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Scrape Reddit posts from trading-related subreddits

        Args:
            subreddits: List of subreddit names
            max_posts: Maximum posts per subreddit

        Returns:
            List of Reddit posts
        """
        if not self.reddit:
            logger.warning("Reddit client not initialized")
            return []

        if subreddits is None:
            subreddits = self.social_config.get('reddit', {}).get('subreddits', [
                'wallstreetbets',
                'Forex',
                'investing',
                'stocks',
                'algotrading'
            ])

        posts = []

        for subreddit_name in subreddits:
            try:
                logger.info(f"Scraping r/{subreddit_name}")

                subreddit = self.reddit.subreddit(subreddit_name)

                # Get hot posts
                for submission in subreddit.hot(limit=max_posts):
                    try:
                        post_data = {
                            'source': 'Reddit',
                            'subreddit': subreddit_name,
                            'id': submission.id,
                            'title': submission.title,
                            'selftext': submission.selftext,
                            'score': submission.score,
                            'upvote_ratio': submission.upvote_ratio,
                            'num_comments': submission.num_comments,
                            'author': str(submission.author) if submission.author else '[deleted]',
                            'created_utc': datetime.fromtimestamp(submission.created_utc),
                            'url': submission.url,
                            'permalink': f"https://reddit.com{submission.permalink}",
                            'scraped_at': datetime.now(),
                            'tickers': self._extract_tickers(submission.title + ' ' + submission.selftext)
                        }

                        posts.append(post_data)

                    except Exception as e:
                        logger.debug(f"Error parsing Reddit post: {str(e)}")
                        continue

                logger.info(f"Scraped {len(posts)} posts from r/{subreddit_name}")

            except Exception as e:
                logger.error(f"Failed to scrape r/{subreddit_name}: {str(e)}")

        return posts

    def scrape_reddit_comments(
        self,
        post_id: str,
        max_comments: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Scrape comments from a specific Reddit post

        Args:
            post_id: Reddit submission ID
            max_comments: Maximum comments to scrape

        Returns:
            List of comments
        """
        if not self.reddit:
            return []

        comments = []

        try:
            submission = self.reddit.submission(id=post_id)
            submission.comments.replace_more(limit=0)  # Don't fetch "more comments"

            for comment in submission.comments.list()[:max_comments]:
                try:
                    comments.append({
                        'id': comment.id,
                        'body': comment.body,
                        'score': comment.score,
                        'author': str(comment.author) if comment.author else '[deleted]',
                        'created_utc': datetime.fromtimestamp(comment.created_utc),
                        'parent_id': comment.parent_id,
                        'scraped_at': datetime.now()
                    })

                except Exception as e:
                    logger.debug(f"Error parsing comment: {str(e)}")
                    continue

        except Exception as e:
            logger.error(f"Failed to scrape comments: {str(e)}")

        return comments

    def _extract_tickers(self, text: str) -> List[str]:
        """
        Extract ticker symbols from text

        Args:
            text: Text to search

        Returns:
            List of ticker symbols
        """
        import re

        # Pattern for $TICKER or explicit tickers
        pattern = r'\$([A-Z]{1,5})\b'
        matches = re.findall(pattern, text.upper())

        # Common forex pairs
        forex_pattern = r'\b(EUR[/_]?USD|GBP[/_]?USD|USD[/_]?JPY|AUD[/_]?USD|USD[/_]?CAD|XAU[/_]?USD)\b'
        forex_matches = re.findall(forex_pattern, text.upper())

        tickers = list(set(matches + forex_matches))

        return tickers

    def get_trending_topics(
        self,
        posts: List[Dict[str, Any]],
        min_mentions: int = 3
    ) -> Dict[str, int]:
        """
        Get trending topics/tickers from posts

        Args:
            posts: List of posts
            min_mentions: Minimum mentions to be considered trending

        Returns:
            Dictionary of ticker: mention_count
        """
        ticker_counts = {}

        for post in posts:
            tickers = post.get('tickers', [])

            for ticker in tickers:
                ticker_counts[ticker] = ticker_counts.get(ticker, 0) + 1

        # Filter by minimum mentions
        trending = {
            ticker: count
            for ticker, count in ticker_counts.items()
            if count >= min_mentions
        }

        # Sort by count
        trending = dict(sorted(trending.items(), key=lambda x: x[1], reverse=True))

        logger.info(f"Found {len(trending)} trending tickers")

        return trending

    def get_sentiment_for_symbol(
        self,
        symbol: str,
        posts: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Get aggregated sentiment for a specific symbol

        Args:
            symbol: Trading symbol
            posts: List of posts

        Returns:
            Sentiment summary
        """
        relevant_posts = []

        # Normalize symbol
        symbol_variations = [
            symbol,
            symbol.replace('_', ''),
            symbol.replace('_', '/'),
            f"${symbol}"
        ]

        for post in posts:
            tickers = post.get('tickers', [])
            title = post.get('title', '').upper()
            text = post.get('selftext', '').upper()

            # Check if symbol mentioned
            if any(var in tickers or var in title or var in text for var in symbol_variations):
                relevant_posts.append(post)

        # Calculate aggregate metrics
        if not relevant_posts:
            return {
                'symbol': symbol,
                'mention_count': 0,
                'avg_score': 0,
                'avg_upvote_ratio': 0,
                'total_comments': 0,
                'sentiment': 'neutral'
            }

        avg_score = sum(p.get('score', 0) for p in relevant_posts) / len(relevant_posts)
        avg_ratio = sum(p.get('upvote_ratio', 0.5) for p in relevant_posts) / len(relevant_posts)
        total_comments = sum(p.get('num_comments', 0) for p in relevant_posts)

        # Simple sentiment based on score and ratio
        if avg_score > 100 and avg_ratio > 0.7:
            sentiment = 'bullish'
        elif avg_score < 50 or avg_ratio < 0.5:
            sentiment = 'bearish'
        else:
            sentiment = 'neutral'

        return {
            'symbol': symbol,
            'mention_count': len(relevant_posts),
            'avg_score': avg_score,
            'avg_upvote_ratio': avg_ratio,
            'total_comments': total_comments,
            'sentiment': sentiment,
            'posts': relevant_posts[:5]  # Top 5 posts
        }

    def filter_by_engagement(
        self,
        posts: List[Dict[str, Any]],
        min_score: int = 10,
        min_comments: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Filter posts by engagement metrics

        Args:
            posts: List of posts
            min_score: Minimum score
            min_comments: Minimum comments

        Returns:
            Filtered posts
        """
        filtered = [
            post for post in posts
            if post.get('score', 0) >= min_score
            and post.get('num_comments', 0) >= min_comments
        ]

        logger.info(f"Filtered {len(filtered)} high-engagement posts")

        return filtered

    def filter_by_timeframe(
        self,
        posts: List[Dict[str, Any]],
        hours: int = 24
    ) -> List[Dict[str, Any]]:
        """
        Filter posts by time frame

        Args:
            posts: List of posts
            hours: Hours to look back

        Returns:
            Recent posts
        """
        cutoff = datetime.now() - timedelta(hours=hours)

        filtered = [
            post for post in posts
            if post.get('created_utc', datetime.min) > cutoff
        ]

        logger.info(f"Filtered {len(filtered)} posts from last {hours} hours")

        return filtered

    # Twitter/X methods (optional - requires API access)

    def scrape_twitter(
        self,
        keywords: List[str],
        max_tweets: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Scrape Twitter/X (requires API access)

        Args:
            keywords: Keywords to search
            max_tweets: Maximum tweets

        Returns:
            List of tweets
        """
        if not self.twitter_enabled:
            logger.info("Twitter scraping disabled")
            return []

        # TODO: Implement Twitter API v2 integration
        # Requires Twitter API credentials
        logger.warning("Twitter scraping not yet implemented")
        return []

    def get_social_sentiment_summary(
        self,
        symbols: List[str]
    ) -> Dict[str, Any]:
        """
        Get social sentiment summary for multiple symbols

        Args:
            symbols: List of trading symbols

        Returns:
            Sentiment summary
        """
        # Scrape Reddit
        posts = self.scrape_reddit(max_posts=100)

        # Filter recent and high engagement
        posts = self.filter_by_timeframe(posts, hours=24)
        posts = self.filter_by_engagement(posts, min_score=10, min_comments=5)

        # Get trending
        trending = self.get_trending_topics(posts)

        # Get sentiment for each symbol
        symbol_sentiments = {}
        for symbol in symbols:
            sentiment = self.get_sentiment_for_symbol(symbol, posts)
            symbol_sentiments[symbol] = sentiment

        return {
            'total_posts_analyzed': len(posts),
            'trending_tickers': trending,
            'symbol_sentiments': symbol_sentiments,
            'analyzed_at': datetime.now()
        }
