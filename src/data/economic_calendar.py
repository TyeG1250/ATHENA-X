"""
ATHENA-X Economic Calendar Scraper
ForexFactory economic calendar for high-impact events
"""

import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from loguru import logger
from fake_useragent import UserAgent
import time


class EconomicCalendar:
    """
    Economic calendar scraper (ForexFactory)
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize economic calendar

        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.base_url = "https://www.forexfactory.com/calendar"
        self.ua = UserAgent()

        # Impact levels
        self.impact_levels = {
            'high': 3,
            'medium': 2,
            'low': 1,
            'holiday': 0
        }

        logger.info("Economic calendar initialized")

    def _get_headers(self) -> Dict[str, str]:
        """Get headers for requests"""
        return {
            'User-Agent': self.ua.random,
            'Accept': 'text/html,application/xhtml+xml',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://www.forexfactory.com/',
        }

    def scrape_today(self) -> List[Dict[str, Any]]:
        """
        Scrape today's economic events

        Returns:
            List of economic events
        """
        return self.scrape_calendar(date=datetime.now())

    def scrape_calendar(
        self,
        date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Scrape economic calendar for a specific date

        Args:
            date: Date to scrape (default: today)

        Returns:
            List of economic events
        """
        if date is None:
            date = datetime.now()

        events = []

        try:
            # Format date for URL (e.g., jan15.2024)
            date_str = date.strftime('%b%d.%Y').lower()
            url = f"{self.base_url}?day={date_str}"

            logger.info(f"Scraping economic calendar for {date.strftime('%Y-%m-%d')}")

            response = requests.get(url, headers=self._get_headers(), timeout=15)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # Find calendar table
            calendar_table = soup.find('table', class_='calendar__table')

            if not calendar_table:
                logger.warning("Calendar table not found")
                return events

            rows = calendar_table.find_all('tr', class_='calendar__row')

            current_date = date.strftime('%Y-%m-%d')
            current_time = None

            for row in rows:
                try:
                    # Extract time
                    time_elem = row.find('td', class_='calendar__time')
                    if time_elem:
                        time_text = time_elem.get_text(strip=True)
                        if time_text and time_text != '':
                            current_time = time_text

                    # Extract currency
                    currency_elem = row.find('td', class_='calendar__currency')
                    currency = currency_elem.get_text(strip=True) if currency_elem else ''

                    # Extract impact
                    impact_elem = row.find('td', class_='calendar__impact')
                    impact = 'low'
                    if impact_elem:
                        impact_span = impact_elem.find('span')
                        if impact_span:
                            impact_class = impact_span.get('class', [])
                            if 'icon--ff-impact-red' in impact_class:
                                impact = 'high'
                            elif 'icon--ff-impact-ora' in impact_class:
                                impact = 'medium'
                            elif 'icon--ff-impact-yel' in impact_class:
                                impact = 'low'

                    # Extract event name
                    event_elem = row.find('td', class_='calendar__event')
                    event_name = event_elem.get_text(strip=True) if event_elem else ''

                    # Extract actual, forecast, previous
                    actual_elem = row.find('td', class_='calendar__actual')
                    forecast_elem = row.find('td', class_='calendar__forecast')
                    previous_elem = row.find('td', class_='calendar__previous')

                    actual = actual_elem.get_text(strip=True) if actual_elem else ''
                    forecast = forecast_elem.get_text(strip=True) if forecast_elem else ''
                    previous = previous_elem.get_text(strip=True) if previous_elem else ''

                    # Only include events with impact and name
                    if event_name and currency:
                        event_data = {
                            'date': current_date,
                            'time': current_time if current_time else 'All Day',
                            'currency': currency,
                            'impact': impact,
                            'impact_score': self.impact_levels.get(impact, 0),
                            'event': event_name,
                            'actual': actual,
                            'forecast': forecast,
                            'previous': previous,
                            'scraped_at': datetime.now()
                        }

                        events.append(event_data)

                except Exception as e:
                    logger.debug(f"Error parsing calendar row: {str(e)}")
                    continue

            logger.info(f"Scraped {len(events)} events for {date.strftime('%Y-%m-%d')}")

        except Exception as e:
            logger.error(f"Failed to scrape economic calendar: {str(e)}")

        return events

    def get_high_impact_events(
        self,
        hours_ahead: int = 24
    ) -> List[Dict[str, Any]]:
        """
        Get high-impact events for the next N hours

        Args:
            hours_ahead: Hours to look ahead

        Returns:
            List of high-impact events
        """
        events = []

        # Scrape today and tomorrow
        today = datetime.now()
        tomorrow = today + timedelta(days=1)

        for date in [today, tomorrow]:
            day_events = self.scrape_calendar(date)
            events.extend(day_events)

        # Filter for high impact only
        high_impact = [
            event for event in events
            if event.get('impact') == 'high'
        ]

        logger.info(f"Found {len(high_impact)} high-impact events")

        return high_impact

    def check_upcoming_events(
        self,
        buffer_minutes: int = 30
    ) -> Dict[str, Any]:
        """
        Check for upcoming high-impact events within buffer time

        Args:
            buffer_minutes: Minutes to look ahead

        Returns:
            Dictionary with event check results
        """
        high_impact_events = self.get_high_impact_events(hours_ahead=2)

        upcoming_events = []
        now = datetime.now()

        for event in high_impact_events:
            # Parse event time
            event_time_str = event.get('time', '')

            if event_time_str == 'All Day' or not event_time_str:
                continue

            try:
                # Parse time (e.g., "2:00pm")
                event_time = datetime.strptime(
                    f"{event['date']} {event_time_str}",
                    "%Y-%m-%d %I:%M%p"
                )

                # Calculate time difference
                time_diff = (event_time - now).total_seconds() / 60

                # Check if within buffer
                if -buffer_minutes <= time_diff <= buffer_minutes:
                    upcoming_events.append({
                        **event,
                        'minutes_until': int(time_diff),
                        'is_imminent': True
                    })

            except Exception as e:
                logger.debug(f"Error parsing event time: {str(e)}")
                continue

        return {
            'has_upcoming_events': len(upcoming_events) > 0,
            'upcoming_events': upcoming_events,
            'should_pause_trading': len(upcoming_events) > 0,
            'checked_at': now
        }

    def get_events_by_currency(
        self,
        currency: str,
        impact_level: str = 'high'
    ) -> List[Dict[str, Any]]:
        """
        Get events for a specific currency

        Args:
            currency: Currency code (USD, EUR, GBP, etc.)
            impact_level: Minimum impact level (high, medium, low)

        Returns:
            Filtered events
        """
        events = self.scrape_today()

        min_impact_score = self.impact_levels.get(impact_level, 0)

        filtered = [
            event for event in events
            if event.get('currency') == currency
            and event.get('impact_score', 0) >= min_impact_score
        ]

        logger.info(f"Found {len(filtered)} {impact_level}+ impact events for {currency}")

        return filtered

    def should_avoid_trading(
        self,
        currencies: List[str],
        buffer_minutes: int = 30
    ) -> bool:
        """
        Check if trading should be avoided due to upcoming events

        Args:
            currencies: List of currencies to check (e.g., ['USD', 'EUR'])
            buffer_minutes: Minutes before/after event to avoid

        Returns:
            True if trading should be avoided
        """
        check_result = self.check_upcoming_events(buffer_minutes)

        if not check_result['has_upcoming_events']:
            return False

        # Check if any upcoming event involves our currencies
        for event in check_result['upcoming_events']:
            if event.get('currency') in currencies:
                logger.warning(
                    f"Upcoming {event['impact']} impact event: "
                    f"{event['currency']} - {event['event']} "
                    f"in {event['minutes_until']} minutes"
                )
                return True

        return False

    def get_weekly_calendar(self) -> List[Dict[str, Any]]:
        """
        Get entire week's calendar

        Returns:
            List of events for the week
        """
        events = []
        today = datetime.now()

        for i in range(7):  # Next 7 days
            date = today + timedelta(days=i)
            day_events = self.scrape_calendar(date)
            events.extend(day_events)

        logger.info(f"Scraped {len(events)} events for the week")

        return events
