"""
JARVIS-X Metrics Collection and Monitoring
Prometheus metrics for system monitoring
"""

from prometheus_client import Counter, Histogram, Gauge, Summary, start_http_server
from typing import Optional, Dict, Any
import time
from functools import wraps


class MetricsCollector:
    """
    Centralized metrics collection for JARVIS-X
    """

    def __init__(self, port: int = 8000, enable_prometheus: bool = True):
        """
        Initialize metrics collector

        Args:
            port: Prometheus HTTP server port
            enable_prometheus: Whether to enable Prometheus server
        """
        self.port = port
        self.enable_prometheus = enable_prometheus

        # Trading Metrics
        self.trades_total = Counter(
            'jarvis_trades_total',
            'Total number of trades executed',
            ['symbol', 'direction', 'result']
        )

        self.trade_profit = Histogram(
            'jarvis_trade_profit',
            'Trade profit/loss distribution',
            ['symbol'],
            buckets=[-100, -50, -20, -10, -5, 0, 5, 10, 20, 50, 100, 200]
        )

        self.trade_duration = Histogram(
            'jarvis_trade_duration_seconds',
            'Time from entry to exit',
            ['symbol'],
            buckets=[60, 300, 900, 1800, 3600, 7200, 14400, 28800, 86400]
        )

        # Performance Metrics
        self.win_rate = Gauge(
            'jarvis_win_rate',
            'Current win rate percentage',
            ['period']
        )

        self.sharpe_ratio = Gauge(
            'jarvis_sharpe_ratio',
            'Current Sharpe ratio',
            ['period']
        )

        self.drawdown = Gauge(
            'jarvis_drawdown',
            'Current drawdown percentage'
        )

        self.account_balance = Gauge(
            'jarvis_account_balance',
            'Current account balance'
        )

        self.total_profit = Gauge(
            'jarvis_total_profit',
            'Total profit/loss'
        )

        # Agent Metrics
        self.agent_votes = Counter(
            'jarvis_agent_votes_total',
            'Agent voting activity',
            ['agent', 'vote']
        )

        self.agent_accuracy = Gauge(
            'jarvis_agent_accuracy',
            'Agent prediction accuracy',
            ['agent']
        )

        self.agent_confidence = Histogram(
            'jarvis_agent_confidence',
            'Agent confidence distribution',
            ['agent'],
            buckets=[0.5, 0.6, 0.7, 0.75, 0.8, 0.85, 0.9, 0.95, 1.0]
        )

        # Data Pipeline Metrics
        self.data_fetches = Counter(
            'jarvis_data_fetches_total',
            'Data fetch operations',
            ['source', 'status']
        )

        self.data_latency = Histogram(
            'jarvis_data_latency_seconds',
            'Data fetch latency',
            ['source'],
            buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
        )

        self.cache_hits = Counter(
            'jarvis_cache_hits_total',
            'Cache hit/miss statistics',
            ['cache_type', 'result']
        )

        # Risk Metrics
        self.risk_violations = Counter(
            'jarvis_risk_violations_total',
            'Risk limit violations',
            ['violation_type']
        )

        self.position_size = Histogram(
            'jarvis_position_size',
            'Position size distribution',
            ['symbol'],
            buckets=[0.005, 0.01, 0.015, 0.02, 0.025, 0.03]
        )

        self.var_95 = Gauge(
            'jarvis_var_95',
            'Value at Risk (95% confidence)'
        )

        # System Metrics
        self.loop_duration = Histogram(
            'jarvis_loop_duration_seconds',
            'Main loop execution time',
            buckets=[1, 5, 10, 30, 60, 120]
        )

        self.errors_total = Counter(
            'jarvis_errors_total',
            'Total errors',
            ['component', 'error_type']
        )

        self.active_positions = Gauge(
            'jarvis_active_positions',
            'Number of active positions'
        )

        # Sentiment Metrics
        self.sentiment_score = Gauge(
            'jarvis_sentiment_score',
            'Market sentiment score',
            ['symbol', 'source']
        )

        # Start Prometheus server
        if self.enable_prometheus:
            try:
                start_http_server(self.port)
                print(f"Prometheus metrics server started on port {self.port}")
            except OSError:
                print(f"Port {self.port} already in use, skipping Prometheus server")

    # Trading Methods
    def record_trade(
        self,
        symbol: str,
        direction: str,
        profit: float,
        duration_seconds: float,
        result: str
    ):
        """
        Record a completed trade

        Args:
            symbol: Trading symbol
            direction: BUY or SELL
            profit: Profit/loss amount
            duration_seconds: Trade duration
            result: WIN or LOSS
        """
        self.trades_total.labels(
            symbol=symbol,
            direction=direction,
            result=result
        ).inc()

        self.trade_profit.labels(symbol=symbol).observe(profit)
        self.trade_duration.labels(symbol=symbol).observe(duration_seconds)

    def update_performance(
        self,
        win_rate: float,
        sharpe_ratio: float,
        drawdown: float,
        balance: float,
        total_profit: float,
        period: str = "all"
    ):
        """
        Update performance metrics

        Args:
            win_rate: Win rate (0-1)
            sharpe_ratio: Sharpe ratio
            drawdown: Current drawdown (0-1)
            balance: Account balance
            total_profit: Total profit
            period: Time period (all, daily, weekly, monthly)
        """
        self.win_rate.labels(period=period).set(win_rate * 100)
        self.sharpe_ratio.labels(period=period).set(sharpe_ratio)
        self.drawdown.set(drawdown * 100)
        self.account_balance.set(balance)
        self.total_profit.set(total_profit)

    # Agent Methods
    def record_agent_vote(self, agent_name: str, vote: str):
        """Record agent vote"""
        self.agent_votes.labels(agent=agent_name, vote=vote).inc()

    def update_agent_accuracy(self, agent_name: str, accuracy: float):
        """Update agent accuracy"""
        self.agent_accuracy.labels(agent=agent_name).set(accuracy)

    def record_agent_confidence(self, agent_name: str, confidence: float):
        """Record agent confidence"""
        self.agent_confidence.labels(agent=agent_name).observe(confidence)

    # Data Pipeline Methods
    def record_data_fetch(self, source: str, status: str, latency: float):
        """
        Record data fetch operation

        Args:
            source: Data source name
            status: success or failure
            latency: Fetch latency in seconds
        """
        self.data_fetches.labels(source=source, status=status).inc()
        self.data_latency.labels(source=source).observe(latency)

    def record_cache_access(self, cache_type: str, hit: bool):
        """Record cache hit/miss"""
        result = "hit" if hit else "miss"
        self.cache_hits.labels(cache_type=cache_type, result=result).inc()

    # Risk Methods
    def record_risk_violation(self, violation_type: str):
        """Record risk limit violation"""
        self.risk_violations.labels(violation_type=violation_type).inc()

    def record_position_size(self, symbol: str, size: float):
        """Record position size"""
        self.position_size.labels(symbol=symbol).observe(size)

    def update_var(self, var_95: float):
        """Update VaR metric"""
        self.var_95.set(var_95)

    # System Methods
    def record_loop_duration(self, duration: float):
        """Record main loop duration"""
        self.loop_duration.observe(duration)

    def record_error(self, component: str, error_type: str):
        """Record error"""
        self.errors_total.labels(component=component, error_type=error_type).inc()

    def update_active_positions(self, count: int):
        """Update active positions count"""
        self.active_positions.set(count)

    # Sentiment Methods
    def update_sentiment(self, symbol: str, source: str, score: float):
        """Update sentiment score"""
        self.sentiment_score.labels(symbol=symbol, source=source).set(score)


def timing_metric(metric_func):
    """
    Decorator to measure execution time

    Args:
        metric_func: Function to call with duration

    Example:
        @timing_metric(lambda duration: metrics.data_latency.labels(source='oanda').observe(duration))
        def fetch_data():
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                metric_func(duration)
                return result
            except Exception as e:
                duration = time.time() - start_time
                metric_func(duration)
                raise e
        return wrapper
    return decorator


# Global metrics instance
_metrics_instance: Optional[MetricsCollector] = None


def get_metrics(port: int = 8000, enable_prometheus: bool = True) -> MetricsCollector:
    """
    Get global metrics instance

    Args:
        port: Prometheus port
        enable_prometheus: Enable Prometheus server

    Returns:
        MetricsCollector instance
    """
    global _metrics_instance

    if _metrics_instance is None:
        _metrics_instance = MetricsCollector(port=port, enable_prometheus=enable_prometheus)

    return _metrics_instance
