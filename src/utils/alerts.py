"""
ATHENA-X Alert System
Notification system for critical events
"""

from typing import List, Optional, Dict, Any
from enum import Enum
from datetime import datetime
from loguru import logger


class AlertSeverity(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertChannel(Enum):
    """Alert delivery channels"""
    CONSOLE = "console"
    EMAIL = "email"
    TELEGRAM = "telegram"
    WEBHOOK = "webhook"


class Alert:
    """Alert message"""

    def __init__(
        self,
        title: str,
        message: str,
        severity: AlertSeverity,
        data: Optional[Dict[str, Any]] = None
    ):
        self.title = title
        self.message = message
        self.severity = severity
        self.data = data or {}
        self.timestamp = datetime.now()

    def __str__(self):
        return f"[{self.severity.value.upper()}] {self.title}: {self.message}"


class AlertManager:
    """
    Centralized alert management
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize alert manager

        Args:
            config: Alert configuration
        """
        self.config = config
        self.enabled = config.get('enabled', True)
        self.channels = self._init_channels(config.get('methods', ['console']))
        self.conditions = config.get('conditions', [])
        self.alert_history = []

    def _init_channels(self, methods: List[str]) -> List[AlertChannel]:
        """Initialize alert channels"""
        channels = []
        for method in methods:
            try:
                channels.append(AlertChannel(method))
            except ValueError:
                logger.warning(f"Unknown alert channel: {method}")
        return channels

    def send_alert(
        self,
        title: str,
        message: str,
        severity: AlertSeverity = AlertSeverity.INFO,
        data: Optional[Dict[str, Any]] = None
    ):
        """
        Send alert through configured channels

        Args:
            title: Alert title
            message: Alert message
            severity: Alert severity
            data: Additional data
        """
        if not self.enabled:
            return

        alert = Alert(title, message, severity, data)
        self.alert_history.append(alert)

        # Send through each channel
        for channel in self.channels:
            try:
                if channel == AlertChannel.CONSOLE:
                    self._send_console(alert)
                elif channel == AlertChannel.EMAIL:
                    self._send_email(alert)
                elif channel == AlertChannel.TELEGRAM:
                    self._send_telegram(alert)
                elif channel == AlertChannel.WEBHOOK:
                    self._send_webhook(alert)
            except Exception as e:
                logger.error(f"Failed to send alert via {channel.value}: {str(e)}")

    def _send_console(self, alert: Alert):
        """Send alert to console"""
        severity_colors = {
            AlertSeverity.INFO: logger.info,
            AlertSeverity.WARNING: logger.warning,
            AlertSeverity.ERROR: logger.error,
            AlertSeverity.CRITICAL: logger.critical
        }

        log_func = severity_colors.get(alert.severity, logger.info)
        log_func(f"🔔 ALERT: {alert}")

    def _send_email(self, alert: Alert):
        """Send alert via email"""
        # TODO: Implement email sending
        # Use smtplib or email service API
        logger.warning("Email alerts not yet implemented")

    def _send_telegram(self, alert: Alert):
        """Send alert via Telegram"""
        # TODO: Implement Telegram bot
        logger.warning("Telegram alerts not yet implemented")

    def _send_webhook(self, alert: Alert):
        """Send alert via webhook"""
        # TODO: Implement webhook posting
        logger.warning("Webhook alerts not yet implemented")

    # Predefined alert types
    def alert_daily_loss(self, loss_pct: float, threshold: float):
        """Alert for daily loss limit"""
        self.send_alert(
            title="Daily Loss Limit Reached",
            message=f"Daily loss ({loss_pct:.2f}%) exceeded threshold ({threshold:.2f}%)",
            severity=AlertSeverity.CRITICAL,
            data={'loss_pct': loss_pct, 'threshold': threshold}
        )

    def alert_drawdown(self, drawdown_pct: float, threshold: float):
        """Alert for drawdown"""
        severity = AlertSeverity.CRITICAL if drawdown_pct > 0.15 else AlertSeverity.WARNING

        self.send_alert(
            title="Drawdown Alert",
            message=f"Drawdown ({drawdown_pct:.2f}%) exceeded threshold ({threshold:.2f}%)",
            severity=severity,
            data={'drawdown_pct': drawdown_pct, 'threshold': threshold}
        )

    def alert_consecutive_losses(self, count: int, threshold: int):
        """Alert for consecutive losses"""
        self.send_alert(
            title="Consecutive Losses",
            message=f"{count} consecutive losses (threshold: {threshold})",
            severity=AlertSeverity.WARNING,
            data={'count': count, 'threshold': threshold}
        )

    def alert_risk_violation(self, violation_type: str, details: str):
        """Alert for risk violations"""
        self.send_alert(
            title="Risk Limit Violation",
            message=f"{violation_type}: {details}",
            severity=AlertSeverity.ERROR,
            data={'violation_type': violation_type, 'details': details}
        )

    def alert_system_error(self, component: str, error: str):
        """Alert for system errors"""
        self.send_alert(
            title="System Error",
            message=f"{component}: {error}",
            severity=AlertSeverity.ERROR,
            data={'component': component, 'error': error}
        )

    def alert_trade_executed(
        self,
        symbol: str,
        direction: str,
        size: float,
        price: float
    ):
        """Alert for trade execution"""
        self.send_alert(
            title="Trade Executed",
            message=f"{direction} {size} {symbol} @ {price}",
            severity=AlertSeverity.INFO,
            data={
                'symbol': symbol,
                'direction': direction,
                'size': size,
                'price': price
            }
        )

    def get_recent_alerts(self, limit: int = 10) -> List[Alert]:
        """Get recent alerts"""
        return self.alert_history[-limit:]


# Global alert manager instance
_alert_manager: Optional[AlertManager] = None


def init_alerts(config: Dict[str, Any]) -> AlertManager:
    """
    Initialize global alert manager

    Args:
        config: Alert configuration

    Returns:
        AlertManager instance
    """
    global _alert_manager
    _alert_manager = AlertManager(config)
    return _alert_manager


def get_alert_manager() -> Optional[AlertManager]:
    """Get global alert manager"""
    return _alert_manager


def send_alert(
    title: str,
    message: str,
    severity: AlertSeverity = AlertSeverity.INFO,
    data: Optional[Dict[str, Any]] = None
):
    """Send alert using global manager"""
    if _alert_manager:
        _alert_manager.send_alert(title, message, severity, data)
    else:
        logger.warning("Alert manager not initialized")
