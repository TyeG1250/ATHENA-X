"""
ATHENA-X Risk Metrics
VaR, CVaR, Sharpe, Sortino, and other risk-adjusted performance metrics
"""

from typing import List, Dict, Any, Optional
import numpy as np
import pandas as pd
from loguru import logger


class RiskMetrics:
    """
    Comprehensive risk metrics calculator

    Metrics:
    - VaR (Value at Risk)
    - CVaR (Conditional VaR / Expected Shortfall)
    - Sharpe Ratio
    - Sortino Ratio
    - Calmar Ratio
    - Maximum Drawdown
    - Volatility
    """

    def __init__(self, risk_free_rate: float = 0.02):
        """
        Initialize risk metrics calculator

        Args:
            risk_free_rate: Annual risk-free rate (default: 2%)
        """
        self.risk_free_rate = risk_free_rate
        logger.info(f"Risk metrics initialized (risk-free rate: {risk_free_rate:.2%})")

    def calculate_var(
        self,
        returns: List[float],
        confidence: float = 0.95,
        method: str = 'historical'
    ) -> float:
        """
        Calculate Value at Risk

        Args:
            returns: List of returns
            confidence: Confidence level (0.95 = 95%)
            method: 'historical', 'parametric', or 'monte_carlo'

        Returns:
            VaR value (positive number representing potential loss)
        """
        if len(returns) < 2:
            return 0.0

        if method == 'historical':
            # Historical VaR (non-parametric)
            var = np.percentile(returns, (1 - confidence) * 100)
            return abs(var)

        elif method == 'parametric':
            # Parametric VaR (assumes normal distribution)
            mean = np.mean(returns)
            std = np.std(returns)

            # Z-score for confidence level
            from scipy import stats
            z_score = stats.norm.ppf(1 - confidence)

            var = mean + z_score * std
            return abs(var)

        else:
            logger.warning(f"Unknown VaR method: {method}, using historical")
            return self.calculate_var(returns, confidence, 'historical')

    def calculate_cvar(
        self,
        returns: List[float],
        confidence: float = 0.95
    ) -> float:
        """
        Calculate Conditional VaR (Expected Shortfall)

        Average loss in worst (1-confidence)% of cases

        Args:
            returns: List of returns
            confidence: Confidence level

        Returns:
            CVaR value
        """
        if len(returns) < 2:
            return 0.0

        # Calculate VaR
        var = self.calculate_var(returns, confidence, 'historical')

        # Find all returns worse than VaR
        returns_array = np.array(returns)
        tail_losses = returns_array[returns_array <= -var]

        if len(tail_losses) == 0:
            return var

        # Average of tail losses
        cvar = abs(np.mean(tail_losses))

        return cvar

    def calculate_sharpe_ratio(
        self,
        returns: List[float],
        periods_per_year: int = 252
    ) -> float:
        """
        Calculate Sharpe Ratio

        Sharpe = (Return - Risk Free) / Volatility

        Args:
            returns: List of returns
            periods_per_year: Trading periods per year (252 for daily)

        Returns:
            Annualized Sharpe ratio
        """
        if len(returns) < 2:
            return 0.0

        returns_array = np.array(returns)

        # Daily risk-free rate
        daily_rf = self.risk_free_rate / periods_per_year

        # Excess returns
        excess_returns = returns_array - daily_rf

        mean_excess = np.mean(excess_returns)
        std_excess = np.std(excess_returns)

        if std_excess == 0:
            return 0.0

        # Annualized Sharpe
        sharpe = (mean_excess / std_excess) * np.sqrt(periods_per_year)

        return sharpe

    def calculate_sortino_ratio(
        self,
        returns: List[float],
        periods_per_year: int = 252
    ) -> float:
        """
        Calculate Sortino Ratio

        Sortino = (Return - Risk Free) / Downside Deviation

        Only penalizes downside volatility

        Args:
            returns: List of returns
            periods_per_year: Trading periods per year

        Returns:
            Annualized Sortino ratio
        """
        if len(returns) < 2:
            return 0.0

        returns_array = np.array(returns)

        # Daily risk-free rate
        daily_rf = self.risk_free_rate / periods_per_year

        # Excess returns
        excess_returns = returns_array - daily_rf

        # Downside deviation (only negative returns)
        downside_returns = excess_returns[excess_returns < 0]

        if len(downside_returns) == 0:
            return float('inf')  # No downside = infinite Sortino

        downside_dev = np.std(downside_returns)

        if downside_dev == 0:
            return 0.0

        mean_excess = np.mean(excess_returns)

        # Annualized Sortino
        sortino = (mean_excess / downside_dev) * np.sqrt(periods_per_year)

        return sortino

    def calculate_calmar_ratio(
        self,
        returns: List[float],
        max_drawdown: Optional[float] = None
    ) -> float:
        """
        Calculate Calmar Ratio

        Calmar = Annual Return / Max Drawdown

        Args:
            returns: List of returns
            max_drawdown: Pre-calculated max drawdown (optional)

        Returns:
            Calmar ratio
        """
        if len(returns) < 2:
            return 0.0

        # Annual return
        total_return = np.prod([1 + r for r in returns]) - 1
        annual_return = total_return  # Assuming returns are already annualized

        # Max drawdown
        if max_drawdown is None:
            max_drawdown = self.calculate_max_drawdown(returns)

        if max_drawdown == 0:
            return 0.0

        calmar = annual_return / abs(max_drawdown)

        return calmar

    def calculate_max_drawdown(
        self,
        returns: List[float]
    ) -> float:
        """
        Calculate maximum drawdown

        Args:
            returns: List of returns

        Returns:
            Maximum drawdown (negative value)
        """
        if len(returns) < 2:
            return 0.0

        # Calculate cumulative returns
        cumulative = np.cumprod([1 + r for r in returns])

        # Calculate running maximum
        running_max = np.maximum.accumulate(cumulative)

        # Calculate drawdown
        drawdown = (cumulative - running_max) / running_max

        # Maximum drawdown
        max_dd = np.min(drawdown)

        return max_dd

    def calculate_volatility(
        self,
        returns: List[float],
        periods_per_year: int = 252
    ) -> float:
        """
        Calculate annualized volatility

        Args:
            returns: List of returns
            periods_per_year: Trading periods per year

        Returns:
            Annualized volatility
        """
        if len(returns) < 2:
            return 0.0

        # Standard deviation of returns
        std = np.std(returns)

        # Annualize
        annual_vol = std * np.sqrt(periods_per_year)

        return annual_vol

    def calculate_portfolio_var(
        self,
        positions: List[Dict[str, Any]],
        correlation_matrix: Optional[np.ndarray] = None,
        confidence: float = 0.95
    ) -> float:
        """
        Calculate portfolio VaR considering correlations

        Args:
            positions: List of position dictionaries with 'weight' and 'var'
            correlation_matrix: Correlation matrix (if None, assumes independence)
            confidence: Confidence level

        Returns:
            Portfolio VaR
        """
        if not positions:
            return 0.0

        # Extract weights and individual VaRs
        weights = np.array([p.get('weight', 0) for p in positions])
        individual_vars = np.array([p.get('var', 0) for p in positions])

        if correlation_matrix is None:
            # Assume independence (correlation = 0)
            correlation_matrix = np.eye(len(positions))

        # Portfolio variance = w^T * Σ * w
        # where Σ is covariance matrix
        # For VaR: use correlation × individual_vars

        # Covariance matrix from correlation and individual VaRs
        cov_matrix = correlation_matrix * np.outer(individual_vars, individual_vars)

        # Portfolio VaR
        portfolio_variance = weights.T @ cov_matrix @ weights
        portfolio_var = np.sqrt(portfolio_variance)

        return portfolio_var

    def calculate_all_metrics(
        self,
        returns: List[float],
        periods_per_year: int = 252
    ) -> Dict[str, float]:
        """
        Calculate all risk metrics

        Args:
            returns: List of returns
            periods_per_year: Trading periods per year

        Returns:
            Dictionary of all metrics
        """
        max_dd = self.calculate_max_drawdown(returns)

        return {
            'var_95': self.calculate_var(returns, 0.95),
            'var_99': self.calculate_var(returns, 0.99),
            'cvar_95': self.calculate_cvar(returns, 0.95),
            'cvar_99': self.calculate_cvar(returns, 0.99),
            'sharpe_ratio': self.calculate_sharpe_ratio(returns, periods_per_year),
            'sortino_ratio': self.calculate_sortino_ratio(returns, periods_per_year),
            'calmar_ratio': self.calculate_calmar_ratio(returns, max_dd),
            'max_drawdown': max_dd,
            'volatility': self.calculate_volatility(returns, periods_per_year),
            'avg_return': np.mean(returns) if returns else 0.0,
            'std_return': np.std(returns) if returns else 0.0,
            'total_return': np.prod([1 + r for r in returns]) - 1 if returns else 0.0
        }

    def format_metrics(self, metrics: Dict[str, float]) -> str:
        """
        Format metrics for display

        Args:
            metrics: Dictionary of metrics

        Returns:
            Formatted string
        """
        output = "Risk Metrics:\n"
        output += "="*50 + "\n"
        output += f"VaR (95%):        {metrics['var_95']:>10.2%}\n"
        output += f"VaR (99%):        {metrics['var_99']:>10.2%}\n"
        output += f"CVaR (95%):       {metrics['cvar_95']:>10.2%}\n"
        output += f"CVaR (99%):       {metrics['cvar_99']:>10.2%}\n"
        output += f"Sharpe Ratio:     {metrics['sharpe_ratio']:>10.2f}\n"
        output += f"Sortino Ratio:    {metrics['sortino_ratio']:>10.2f}\n"
        output += f"Calmar Ratio:     {metrics['calmar_ratio']:>10.2f}\n"
        output += f"Max Drawdown:     {metrics['max_drawdown']:>10.2%}\n"
        output += f"Volatility:       {metrics['volatility']:>10.2%}\n"
        output += f"Avg Return:       {metrics['avg_return']:>10.2%}\n"
        output += f"Total Return:     {metrics['total_return']:>10.2%}\n"
        output += "="*50

        return output
