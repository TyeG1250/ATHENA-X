"""
JARVIS-X News Scraper
Multi-source news aggregation for market sentiment
"""

import requests
from bs4 import BeautifulSoup
import feedparser
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import time
import random
from loguru import logger
from fake_useragent import UserAgent


class NewsAggregator:
    """
    Multi-source news aggregator
    Sources: Reuters, CNBC, MarketWatch, Investing.com
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize news aggregator

        Args:
            config: News source configuration
        """
        self.config = config
        self.sources = config.get('news_sources', {})
        self.update_frequency = config.get('update_frequency', 900)  # 15 minutes
        self.ua = UserAgent()

        # Rate limiting
        self.last_request = {}
        self.min_delay = 2  # Minimum 2 seconds between requests

        logger.info("News aggregator initialized")

    def _get_random_headers(self) -> Dict[str, str]:
        """Generate random headers to avoid blocking"""
        return {
            'User-Agent': self.ua.random,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Referer': 'https://www.google.com/',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }

    def _rate_limit(self, source: str):
        """Enforce rate limiting"""
        if source in self.last_request:
            elapsed = time.time() - self.last_request[source]
            if elapsed < self.min_delay:
                sleep_time = self.min_delay - elapsed + random.uniform(0.5, 1.5)
                time.sleep(sleep_time)

        self.last_request[source] = time.time()

    def scrape_reuters(self) -> List[Dict[str, Any]]:
        """Scrape Reuters market news"""
        articles = []

        if not self.sources.get('reuters', {}).get('enabled', True):
            return articles

        try:
            self._rate_limit('reuters')

            url = "https://www.reuters.com/markets/"
            response = requests.get(url, headers=self._get_random_headers(), timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # Find article containers
            article_elements = soup.find_all('div', {'data-testid': 'MediaStoryCard'})

            for element in article_elements[:20]:  # Limit to 20 articles
                try:
                    # Extract title
                    title_elem = element.find('a', {'data-testid': 'Heading'})
                    if not title_elem:
                        continue

                    title = title_elem.get_text(strip=True)
                    link = "https://www.reuters.com" + title_elem.get('href', '')

                    # Extract summary if available
                    summary_elem = element.find('p', {'data-testid': 'Body'})
                    summary = summary_elem.get_text(strip=True) if summary_elem else ""

                    # Extract time
                    time_elem = element.find('time')
                    pub_time = time_elem.get('datetime') if time_elem else None

                    articles.append({
                        'source': 'Reuters',
                        'title': title,
                        'url': link,
                        'summary': summary,
                        'published_at': pub_time,
                        'scraped_at': datetime.now(),
                        'category': 'markets'
                    })

                except Exception as e:
                    logger.debug(f"Error parsing Reuters article: {str(e)}")
                    continue

            logger.info(f"Scraped {len(articles)} articles from Reuters")

        except Exception as e:
            logger.error(f"Failed to scrape Reuters: {str(e)}")

        return articles

    def scrape_cnbc_rss(self) -> List[Dict[str, Any]]:
        """Scrape CNBC via RSS feeds"""
        articles = []

        if not self.sources.get('cnbc', {}).get('enabled', True):
            return articles

        rss_feeds = [
            "https://www.cnbc.com/id/100003114/device/rss/rss.html",  # Top News
            "https://www.cnbc.com/id/20910258/device/rss/rss.html",   # Markets
            "https://www.cnbc.com/id/15839135/device/rss/rss.html",   # Economy
        ]

        try:
            self._rate_limit('cnbc')

            for feed_url in rss_feeds:
                feed = feedparser.parse(feed_url)

                for entry in feed.entries[:10]:  # Limit per feed
                    try:
                        articles.append({
                            'source': 'CNBC',
                            'title': entry.get('title', ''),
                            'url': entry.get('link', ''),
                            'summary': entry.get('summary', ''),
                            'published_at': entry.get('published', None),
                            'scraped_at': datetime.now(),
                            'category': 'markets'
                        })

                    except Exception as e:
                        logger.debug(f"Error parsing CNBC entry: {str(e)}")
                        continue

                time.sleep(1)  # Brief delay between feeds

            logger.info(f"Scraped {len(articles)} articles from CNBC")

        except Exception as e:
            logger.error(f"Failed to scrape CNBC: {str(e)}")

        return articles

    def scrape_marketwatch(self) -> List[Dict[str, Any]]:
        """Scrape MarketWatch latest news"""
        articles = []

        if not self.sources.get('marketwatch', {}).get('enabled', True):
            return articles

        try:
            self._rate_limit('marketwatch')

            url = "https://www.marketwatch.com/latest-news"
            response = requests.get(url, headers=self._get_random_headers(), timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # Find article elements
            article_elements = soup.find_all('div', class_='article__content')

            for element in article_elements[:20]:
                try:
                    # Extract title and link
                    title_elem = element.find('a', class_='link')
                    if not title_elem:
                        continue

                    title = title_elem.get_text(strip=True)
                    link = title_elem.get('href', '')

                    if not link.startswith('http'):
                        link = "https://www.marketwatch.com" + link

                    # Extract summary
                    summary_elem = element.find('p', class_='article__summary')
                    summary = summary_elem.get_text(strip=True) if summary_elem else ""

                    # Extract timestamp
                    time_elem = element.find('span', class_='article__timestamp')
                    pub_time = time_elem.get_text(strip=True) if time_elem else None

                    articles.append({
                        'source': 'MarketWatch',
                        'title': title,
                        'url': link,
                        'summary': summary,
                        'published_at': pub_time,
                        'scraped_at': datetime.now(),
                        'category': 'markets'
                    })

                except Exception as e:
                    logger.debug(f"Error parsing MarketWatch article: {str(e)}")
                    continue

            logger.info(f"Scraped {len(articles)} articles from MarketWatch")

        except Exception as e:
            logger.error(f"Failed to scrape MarketWatch: {str(e)}")

        return articles

    def scrape_investing_com(self) -> List[Dict[str, Any]]:
        """Scrape Investing.com news"""
        articles = []

        if not self.sources.get('investing', {}).get('enabled', True):
            return articles

        try:
            self._rate_limit('investing')

            url = "https://www.investing.com/news/latest-news"
            response = requests.get(url, headers=self._get_random_headers(), timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # Find article elements
            article_elements = soup.find_all('article', class_='js-article-item')

            for element in article_elements[:20]:
                try:
                    # Extract title and link
                    title_elem = element.find('a', class_='title')
                    if not title_elem:
                        continue

                    title = title_elem.get_text(strip=True)
                    link = "https://www.investing.com" + title_elem.get('href', '')

                    # Extract provider
                    provider_elem = element.find('span', class_='articleDetails')
                    provider = provider_elem.get_text(strip=True) if provider_elem else "Investing.com"

                    # Extract timestamp
                    time_elem = element.find('time')
                    pub_time = time_elem.get('datetime') if time_elem else None

                    articles.append({
                        'source': 'Investing.com',
                        'title': title,
                        'url': link,
                        'summary': '',
                        'published_at': pub_time,
                        'scraped_at': datetime.now(),
                        'category': 'markets',
                        'provider': provider
                    })

                except Exception as e:
                    logger.debug(f"Error parsing Investing.com article: {str(e)}")
                    continue

            logger.info(f"Scraped {len(articles)} articles from Investing.com")

        except Exception as e:
            logger.error(f"Failed to scrape Investing.com: {str(e)}")

        return articles

    def get_all_news(self, max_articles: int = 100) -> List[Dict[str, Any]]:
        """
        Aggregate news from all sources

        Args:
            max_articles: Maximum total articles to return

        Returns:
            List of articles from all sources
        """
        all_articles = []

        # Scrape from all sources
        sources = [
            ('Reuters', self.scrape_reuters),
            ('CNBC', self.scrape_cnbc_rss),
            ('MarketWatch', self.scrape_marketwatch),
            ('Investing.com', self.scrape_investing_com)
        ]

        for source_name, scraper_func in sources:
            try:
                articles = scraper_func()
                all_articles.extend(articles)
                logger.debug(f"Added {len(articles)} articles from {source_name}")

            except Exception as e:
                logger.error(f"Error scraping {source_name}: {str(e)}")

        # Remove duplicates based on URL
        seen_urls = set()
        unique_articles = []

        for article in all_articles:
            url = article.get('url', '')
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_articles.append(article)

        # Sort by scraped time (most recent first)
        unique_articles.sort(key=lambda x: x.get('scraped_at', datetime.min), reverse=True)

        # Limit to max articles
        result = unique_articles[:max_articles]

        logger.info(f"Aggregated {len(result)} unique articles from {len(sources)} sources")

        return result

    def filter_by_keywords(
        self,
        articles: List[Dict[str, Any]],
        keywords: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Filter articles by keywords

        Args:
            articles: List of articles
            keywords: Keywords to search for

        Returns:
            Filtered articles
        """
        filtered = []

        keywords_lower = [k.lower() for k in keywords]

        for article in articles:
            title = article.get('title', '').lower()
            summary = article.get('summary', '').lower()
            text = title + ' ' + summary

            if any(keyword in text for keyword in keywords_lower):
                filtered.append(article)

        logger.info(f"Filtered {len(filtered)} articles matching keywords")

        return filtered

    def filter_by_timeframe(
        self,
        articles: List[Dict[str, Any]],
        hours: int = 24
    ) -> List[Dict[str, Any]]:
        """
        Filter articles by timeframe

        Args:
            articles: List of articles
            hours: Hours to look back

        Returns:
            Recent articles
        """
        cutoff_time = datetime.now() - timedelta(hours=hours)

        filtered = [
            article for article in articles
            if article.get('scraped_at', datetime.min) > cutoff_time
        ]

        logger.info(f"Filtered {len(filtered)} articles from last {hours} hours")

        return filtered
