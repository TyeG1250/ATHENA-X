"""
ATHENA-X Base Agent Class
Abstract base class for all trading agents
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from datetime import datetime
from loguru import logger
import numpy as np


class BaseAgent(ABC):
    """
    Abstract base class for all ATHENA trading agents

    All agents must implement:
    - analyze(): Perform analysis on market data
    - vote(): Return trading decision (BUY/SELL/NEUTRAL)
    - get_confidence(): Return confidence score (0-1)
    """

    def __init__(
        self,
        name: str,
        role: str,
        config: Dict[str, Any],
        weight: float = 1.0
    ):
        """
        Initialize base agent

        Args:
            name: Agent name
            role: Agent role/description
            config: Agent configuration
            weight: Agent weight in voting (0-1)
        """
        self.name = name
        self.role = role
        self.config = config
        self.weight = weight

        # Performance tracking
        self.performance_history = []
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0
        self.total_profit = 0.0

        # Agent state
        self.enabled = config.get('enabled', True)
        self.confidence_threshold = config.get('confidence_threshold', 0.70)

        logger.info(f"Agent initialized: {name} ({role}) - weight: {weight}")

    @abstractmethod
    def analyze(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze market data and generate insights

        Args:
            market_data: Complete market data from pipeline

        Returns:
            Analysis results dictionary
        """
        pass

    @abstractmethod
    def vote(self, analysis: Dict[str, Any]) -> str:
        """
        Generate trading vote based on analysis

        Args:
            analysis: Analysis results from analyze()

        Returns:
            Vote: 'BUY', 'SELL', 'NEUTRAL', 'VETO', or 'APPROVE'
        """
        pass

    def get_confidence(self, analysis: Dict[str, Any]) -> float:
        """
        Calculate confidence score for the analysis

        Args:
            analysis: Analysis results

        Returns:
            Confidence score (0-1)
        """
        # Default implementation - override in subclasses for custom logic
        return analysis.get('confidence', 0.5)

    def get_reasoning(self, analysis: Dict[str, Any]) -> str:
        """
        Generate human-readable reasoning for decision

        Args:
            analysis: Analysis results

        Returns:
            Reasoning string
        """
        vote = self.vote(analysis)
        confidence = self.get_confidence(analysis)

        return f"{self.name}: {vote} (confidence: {confidence:.2%})"

    def update_performance(self, trade_result: Dict[str, Any]):
        """
        Update agent performance metrics

        Args:
            trade_result: Trade outcome data
        """
        self.total_trades += 1

        profit = trade_result.get('profit', 0.0)
        self.total_profit += profit

        if profit > 0:
            self.winning_trades += 1
        elif profit < 0:
            self.losing_trades += 1

        # Add to history
        self.performance_history.append({
            'timestamp': datetime.now(),
            'profit': profit,
            'return_pct': trade_result.get('return_pct', 0.0),
            'trade_id': trade_result.get('trade_id'),
            'symbol': trade_result.get('symbol')
        })

        # Keep last 100 trades
        if len(self.performance_history) > 100:
            self.performance_history = self.performance_history[-100:]

        # Log performance update
        if self.total_trades % 10 == 0:
            logger.info(
                f"{self.name} performance: "
                f"{self.calculate_win_rate():.1%} win rate, "
                f"{self.calculate_sharpe():.2f} Sharpe, "
                f"${self.total_profit:.2f} total profit"
            )

    def calculate_win_rate(self) -> float:
        """
        Calculate agent's win rate

        Returns:
            Win rate (0-1)
        """
        if self.total_trades == 0:
            return 0.0

        return self.winning_trades / self.total_trades

    def calculate_accuracy(self) -> float:
        """
        Calculate rolling window accuracy

        Returns:
            Accuracy score (0-1)
        """
        if len(self.performance_history) < 20:
            return 0.5

        recent = self.performance_history[-20:]
        wins = sum(1 for r in recent if r['profit'] > 0)

        return wins / len(recent)

    def calculate_sharpe(self) -> float:
        """
        Calculate Sharpe ratio

        Returns:
            Sharpe ratio
        """
        if len(self.performance_history) < 2:
            return 0.0

        returns = [r['return_pct'] for r in self.performance_history]

        if len(returns) == 0:
            return 0.0

        mean_return = np.mean(returns)
        std_return = np.std(returns)

        if std_return == 0:
            return 0.0

        # Annualized Sharpe (assuming daily returns)
        sharpe = (mean_return / std_return) * np.sqrt(252)

        return sharpe

    def calculate_avg_profit(self) -> float:
        """
        Calculate average profit per trade

        Returns:
            Average profit
        """
        if self.total_trades == 0:
            return 0.0

        return self.total_profit / self.total_trades

    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Get comprehensive performance metrics

        Returns:
            Performance metrics dictionary
        """
        return {
            'name': self.name,
            'role': self.role,
            'enabled': self.enabled,
            'weight': self.weight,
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'win_rate': self.calculate_win_rate(),
            'accuracy': self.calculate_accuracy(),
            'sharpe_ratio': self.calculate_sharpe(),
            'total_profit': self.total_profit,
            'avg_profit': self.calculate_avg_profit(),
            'recent_trades': len(self.performance_history)
        }

    def is_confident(self, analysis: Dict[str, Any]) -> bool:
        """
        Check if confidence meets threshold

        Args:
            analysis: Analysis results

        Returns:
            True if confidence above threshold
        """
        confidence = self.get_confidence(analysis)
        return confidence >= self.confidence_threshold

    def enable(self):
        """Enable agent"""
        self.enabled = True
        logger.info(f"Agent enabled: {self.name}")

    def disable(self):
        """Disable agent"""
        self.enabled = False
        logger.info(f"Agent disabled: {self.name}")

    def reset_performance(self):
        """Reset performance history"""
        self.performance_history = []
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0
        self.total_profit = 0.0
        logger.info(f"Performance reset: {self.name}")

    def __repr__(self) -> str:
        """String representation"""
        return (
            f"{self.__class__.__name__}("
            f"name='{self.name}', "
            f"role='{self.role}', "
            f"weight={self.weight}, "
            f"enabled={self.enabled})"
        )


class VetoAgent(BaseAgent):
    """
    Special agent with veto power

    Veto agents can block trades regardless of other agents' votes
    Used for: Risk Management, Compliance
    """

    def __init__(self, name: str, role: str, config: Dict[str, Any], weight: float = 1.0):
        super().__init__(name, role, config, weight)
        self.has_veto_power = True
        logger.warning(f"Veto agent initialized: {name} - HAS VETO POWER")

    @abstractmethod
    def validate_trade(
        self,
        proposed_trade: Dict[str, Any],
        current_portfolio: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate proposed trade (veto agents only)

        Args:
            proposed_trade: Proposed trade details
            current_portfolio: Current portfolio state

        Returns:
            Validation result with 'approved' boolean
        """
        pass
