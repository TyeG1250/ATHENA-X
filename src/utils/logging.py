"""
ATHENA-X Logging Utilities
Structured logging with Loguru
"""

import sys
from pathlib import Path
from loguru import logger
from typing import Optional


class ATHENALogger:
    """
    Centralized logging configuration for ATHENA-X
    """

    def __init__(
        self,
        log_level: str = "INFO",
        log_dir: str = "logs",
        rotation: str = "1 day",
        retention: str = "30 days",
        format_type: str = "detailed"
    ):
        """
        Initialize logger

        Args:
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            log_dir: Directory for log files
            rotation: When to rotate logs
            retention: How long to keep logs
            format_type: Format style (simple, detailed, json)
        """
        self.log_level = log_level
        self.log_dir = Path(log_dir)
        self.rotation = rotation
        self.retention = retention
        self.format_type = format_type

        # Create logs directory
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # Remove default handler
        logger.remove()

        # Configure logger
        self._setup_handlers()

    def _setup_handlers(self):
        """Configure log handlers"""

        # Console handler with colors
        if self.format_type == "simple":
            console_format = "<level>{level: <8}</level> | <level>{message}</level>"
        elif self.format_type == "json":
            console_format = "{message}"
        else:  # detailed
            console_format = (
                "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
                "<level>{level: <8}</level> | "
                "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
                "<level>{message}</level>"
            )

        logger.add(
            sys.stdout,
            format=console_format,
            level=self.log_level,
            colorize=True,
            backtrace=True,
            diagnose=True
        )

        # File handler - General logs
        logger.add(
            self.log_dir / "athena_{time:YYYY-MM-DD}.log",
            format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}",
            level=self.log_level,
            rotation=self.rotation,
            retention=self.retention,
            compression="zip",
            backtrace=True,
            diagnose=True
        )

        # File handler - Errors only
        logger.add(
            self.log_dir / "errors_{time:YYYY-MM-DD}.log",
            format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}\n{exception}",
            level="ERROR",
            rotation=self.rotation,
            retention=self.retention,
            compression="zip",
            backtrace=True,
            diagnose=True
        )

        # File handler - Trading activity
        logger.add(
            self.log_dir / "trades_{time:YYYY-MM-DD}.log",
            format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {message}",
            level="INFO",
            rotation=self.rotation,
            retention=self.retention,
            filter=lambda record: "TRADE" in record["extra"],
            compression="zip"
        )

    @staticmethod
    def get_logger(name: Optional[str] = None):
        """
        Get logger instance

        Args:
            name: Logger name (usually __name__)

        Returns:
            Logger instance
        """
        if name:
            return logger.bind(name=name)
        return logger

    @staticmethod
    def log_trade(
        action: str,
        symbol: str,
        direction: str,
        size: float,
        price: float,
        **kwargs
    ):
        """
        Log trading activity

        Args:
            action: Trade action (ENTRY, EXIT, MODIFY)
            symbol: Trading symbol
            direction: BUY or SELL
            size: Position size
            price: Entry/exit price
            **kwargs: Additional parameters
        """
        logger.bind(TRADE=True).info(
            f"{action} | {symbol} | {direction} | Size: {size} | Price: {price} | {kwargs}"
        )

    @staticmethod
    def log_performance(
        metric: str,
        value: float,
        period: str = "daily",
        **kwargs
    ):
        """
        Log performance metrics

        Args:
            metric: Metric name (sharpe, win_rate, etc.)
            value: Metric value
            period: Time period
            **kwargs: Additional parameters
        """
        logger.bind(PERFORMANCE=True).info(
            f"PERFORMANCE | {period} | {metric}: {value} | {kwargs}"
        )

    @staticmethod
    def log_agent_decision(
        agent_name: str,
        symbol: str,
        vote: str,
        confidence: float,
        reasoning: str = ""
    ):
        """
        Log agent decisions

        Args:
            agent_name: Name of the agent
            symbol: Trading symbol
            vote: BUY/SELL/NEUTRAL
            confidence: Confidence score (0-1)
            reasoning: Decision reasoning
        """
        logger.bind(AGENT=True).info(
            f"AGENT | {agent_name} | {symbol} | Vote: {vote} | "
            f"Confidence: {confidence:.2f} | {reasoning}"
        )

    @staticmethod
    def log_risk_event(
        event_type: str,
        severity: str,
        message: str,
        **kwargs
    ):
        """
        Log risk management events

        Args:
            event_type: Type of risk event
            severity: LOW, MEDIUM, HIGH, CRITICAL
            message: Event message
            **kwargs: Additional parameters
        """
        log_func = logger.warning if severity in ["MEDIUM", "HIGH"] else logger.critical

        log_func(
            f"RISK | {event_type} | Severity: {severity} | {message} | {kwargs}"
        )


def setup_logging(
    log_level: str = "INFO",
    log_dir: str = "logs",
    format_type: str = "detailed"
) -> ATHENALogger:
    """
    Quick setup for logging

    Args:
        log_level: Logging level
        log_dir: Log directory
        format_type: Format style

    Returns:
        ATHENALogger instance
    """
    return ATHENALogger(
        log_level=log_level,
        log_dir=log_dir,
        format_type=format_type
    )


# Convenience functions
def get_logger(name: Optional[str] = None):
    """Get logger instance"""
    return ATHENALogger.get_logger(name)


def log_trade(action: str, symbol: str, direction: str, size: float, price: float, **kwargs):
    """Log trade"""
    ATHENALogger.log_trade(action, symbol, direction, size, price, **kwargs)


def log_performance(metric: str, value: float, period: str = "daily", **kwargs):
    """Log performance metric"""
    ATHENALogger.log_performance(metric, value, period, **kwargs)


def log_agent_decision(agent_name: str, symbol: str, vote: str, confidence: float, reasoning: str = ""):
    """Log agent decision"""
    ATHENALogger.log_agent_decision(agent_name, symbol, vote, confidence, reasoning)


def log_risk_event(event_type: str, severity: str, message: str, **kwargs):
    """Log risk event"""
    ATHENALogger.log_risk_event(event_type, severity, message, **kwargs)
