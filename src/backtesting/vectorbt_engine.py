"""
ATHENA-X VectorBT Backtesting Engine
Vectorized backtesting using VectorBT library
"""

from typing import Dict, Any, List, Optional, Tuple
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from loguru import logger

try:
    import vectorbt as vbt
    VECTORBT_AVAILABLE = True
except ImportError:
    VECTORBT_AVAILABLE = False
    logger.warning("VectorBT not available - install with: pip install vectorbt")


class VectorBTEngine:
    """
    VectorBT-based backtesting engine

    Features:
    - Vectorized backtesting (fast)
    - Multi-symbol support
    - Custom indicators
    - Portfolio optimization
    - Walk-forward analysis
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize VectorBT engine

        Args:
            config: Backtesting configuration
        """
        if not VECTORBT_AVAILABLE:
            raise ImportError("VectorBT not installed. Install with: pip install vectorbt")

        self.config = config

        # Backtest parameters
        self.initial_capital = config.get('initial_capital', 10000)
        self.commission = config.get('commission', 0.0001)  # 1 pip
        self.slippage = config.get('slippage', 0.0001)

        logger.info(f"VectorBT engine initialized (capital: ${self.initial_capital})")

    def run_backtest(
        self,
        data: pd.DataFrame,
        entries: pd.Series,
        exits: pd.Series,
        size: Optional[pd.Series] = None,
        stop_loss: Optional[pd.Series] = None,
        take_profit: Optional[pd.Series] = None
    ) -> 'vbt.Portfolio':
        """
        Run backtest with entry/exit signals

        Args:
            data: Price data (OHLC)
            entries: Entry signals (boolean Series)
            exits: Exit signals (boolean Series)
            size: Position sizes (optional)
            stop_loss: Stop loss levels (optional)
            take_profit: Take profit levels (optional)

        Returns:
            VectorBT Portfolio object
        """
        logger.info("Running backtest...")

        # Build portfolio
        portfolio = vbt.Portfolio.from_signals(
            close=data['close'] if isinstance(data, pd.DataFrame) else data,
            entries=entries,
            exits=exits,
            size=size,
            init_cash=self.initial_capital,
            fees=self.commission,
            slippage=self.slippage,
            sl_stop=stop_loss,
            tp_stop=take_profit,
            freq='1D'  # Daily frequency
        )

        logger.success(f"Backtest complete: {portfolio.stats()['Total Trades']} trades")

        return portfolio

    def run_strategy_backtest(
        self,
        data: pd.DataFrame,
        strategy_func: Any,
        **strategy_params
    ) -> 'vbt.Portfolio':
        """
        Run backtest with custom strategy function

        Args:
            data: Price data
            strategy_func: Strategy function that returns (entries, exits)
            **strategy_params: Strategy parameters

        Returns:
            Portfolio object
        """
        # Generate signals from strategy
        entries, exits = strategy_func(data, **strategy_params)

        # Run backtest
        return self.run_backtest(data, entries, exits)

    def optimize_parameters(
        self,
        data: pd.DataFrame,
        strategy_func: Any,
        param_grid: Dict[str, List[Any]]
    ) -> pd.DataFrame:
        """
        Optimize strategy parameters

        Args:
            data: Price data
            strategy_func: Strategy function
            param_grid: Parameter grid to search

        Returns:
            DataFrame with results for each parameter combination
        """
        logger.info(f"Optimizing parameters: {len(param_grid)} dimensions")

        results = []

        # Generate all parameter combinations
        from itertools import product

        param_names = list(param_grid.keys())
        param_values = list(param_grid.values())

        for params in product(*param_values):
            param_dict = dict(zip(param_names, params))

            try:
                # Run backtest with these parameters
                portfolio = self.run_strategy_backtest(data, strategy_func, **param_dict)

                # Extract metrics
                stats = portfolio.stats()

                results.append({
                    **param_dict,
                    'total_return': stats.get('Total Return [%]', 0),
                    'sharpe_ratio': stats.get('Sharpe Ratio', 0),
                    'max_drawdown': stats.get('Max Drawdown [%]', 0),
                    'win_rate': stats.get('Win Rate [%]', 0),
                    'total_trades': stats.get('Total Trades', 0)
                })

            except Exception as e:
                logger.error(f"Backtest failed for params {param_dict}: {str(e)}")
                continue

        results_df = pd.DataFrame(results)

        # Sort by Sharpe ratio
        results_df = results_df.sort_values('sharpe_ratio', ascending=False)

        logger.success(f"Optimization complete: {len(results_df)} combinations tested")

        return results_df

    def walk_forward_analysis(
        self,
        data: pd.DataFrame,
        strategy_func: Any,
        param_grid: Dict[str, List[Any]],
        train_period: int = 252,
        test_period: int = 63,
        anchored: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Walk-forward optimization

        Args:
            data: Price data
            strategy_func: Strategy function
            param_grid: Parameter grid
            train_period: Training window size (days)
            test_period: Test window size (days)
            anchored: Whether to use anchored walk-forward (True) or rolling (False)

        Returns:
            List of walk-forward results
        """
        logger.info("Starting walk-forward analysis...")

        results = []
        total_length = len(data)

        # Iterate through data
        start_idx = 0
        while start_idx + train_period + test_period <= total_length:
            # Training window
            if anchored:
                train_start = 0  # Anchored: always start from beginning
            else:
                train_start = start_idx  # Rolling: move window

            train_end = start_idx + train_period
            train_data = data.iloc[train_start:train_end]

            # Test window
            test_start = train_end
            test_end = test_start + test_period
            test_data = data.iloc[test_start:test_end]

            logger.debug(f"Train: {train_data.index[0]} to {train_data.index[-1]}")
            logger.debug(f"Test: {test_data.index[0]} to {test_data.index[-1]}")

            # Optimize on training data
            opt_results = self.optimize_parameters(train_data, strategy_func, param_grid)

            if len(opt_results) == 0:
                logger.warning("No optimization results, skipping...")
                start_idx += test_period
                continue

            # Best parameters
            best_params = opt_results.iloc[0].to_dict()
            best_params = {k: v for k, v in best_params.items() if k in param_grid}

            # Test on out-of-sample data
            test_portfolio = self.run_strategy_backtest(test_data, strategy_func, **best_params)
            test_stats = test_portfolio.stats()

            results.append({
                'train_start': train_data.index[0],
                'train_end': train_data.index[-1],
                'test_start': test_data.index[0],
                'test_end': test_data.index[-1],
                'best_params': best_params,
                'test_return': test_stats.get('Total Return [%]', 0),
                'test_sharpe': test_stats.get('Sharpe Ratio', 0),
                'test_max_dd': test_stats.get('Max Drawdown [%]', 0),
                'test_trades': test_stats.get('Total Trades', 0)
            })

            # Move to next window
            start_idx += test_period

        logger.success(f"Walk-forward analysis complete: {len(results)} windows")

        return results

    def monte_carlo_simulation(
        self,
        portfolio: 'vbt.Portfolio',
        n_simulations: int = 1000,
        n_days: int = 252
    ) -> Dict[str, Any]:
        """
        Monte Carlo simulation of portfolio

        Args:
            portfolio: Portfolio object from backtest
            n_simulations: Number of simulations
            n_days: Number of days to simulate

        Returns:
            Monte Carlo results
        """
        logger.info(f"Running Monte Carlo simulation ({n_simulations} iterations)...")

        # Get trade returns
        trade_returns = portfolio.trades.returns.values

        if len(trade_returns) == 0:
            return {
                'mean_final_value': self.initial_capital,
                'std_final_value': 0.0,
                'percentile_5': self.initial_capital,
                'percentile_95': self.initial_capital,
                'prob_profit': 0.0
            }

        final_values = []

        for i in range(n_simulations):
            # Random sequence of returns (with replacement)
            simulated_returns = np.random.choice(trade_returns, size=n_days, replace=True)

            # Calculate final value
            final_value = self.initial_capital * np.prod(1 + simulated_returns)
            final_values.append(final_value)

        # Analyze distribution
        results = {
            'mean_final_value': np.mean(final_values),
            'std_final_value': np.std(final_values),
            'median_final_value': np.median(final_values),
            'percentile_5': np.percentile(final_values, 5),
            'percentile_25': np.percentile(final_values, 25),
            'percentile_75': np.percentile(final_values, 75),
            'percentile_95': np.percentile(final_values, 95),
            'prob_profit': sum(1 for v in final_values if v > self.initial_capital) / n_simulations,
            'worst_case': min(final_values),
            'best_case': max(final_values)
        }

        logger.success(f"Monte Carlo complete: {results['prob_profit']:.2%} probability of profit")

        return results

    def calculate_metrics(self, portfolio: 'vbt.Portfolio') -> Dict[str, Any]:
        """
        Calculate comprehensive metrics from portfolio

        Args:
            portfolio: Portfolio object

        Returns:
            Dictionary of metrics
        """
        stats = portfolio.stats()

        return {
            # Returns
            'total_return_pct': stats.get('Total Return [%]', 0),
            'annual_return_pct': stats.get('Annual Return [%]', 0),
            'cumulative_return': stats.get('Total Return [%]', 0) / 100,

            # Risk metrics
            'sharpe_ratio': stats.get('Sharpe Ratio', 0),
            'sortino_ratio': stats.get('Sortino Ratio', 0),
            'calmar_ratio': stats.get('Calmar Ratio', 0),
            'max_drawdown_pct': stats.get('Max Drawdown [%]', 0),
            'avg_drawdown_pct': stats.get('Avg Drawdown [%]', 0),

            # Trade statistics
            'total_trades': stats.get('Total Trades', 0),
            'win_rate_pct': stats.get('Win Rate [%]', 0),
            'profit_factor': stats.get('Profit Factor', 0),
            'avg_win_pct': stats.get('Avg Winning Trade [%]', 0),
            'avg_loss_pct': stats.get('Avg Losing Trade [%]', 0),
            'best_trade_pct': stats.get('Best Trade [%]', 0),
            'worst_trade_pct': stats.get('Worst Trade [%]', 0),

            # Exposure
            'exposure_time_pct': stats.get('Exposure Time [%]', 0),

            # Costs
            'total_fees': stats.get('Total Fees', 0)
        }
