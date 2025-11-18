"""
ATHENA-X Risk Management Agent
Manages risk and has VETO POWER over trades
"""

from typing import Dict, Any, List, Optional
from loguru import logger
import numpy as np

from .base_agent import VetoAgent


class RiskManagementAgent(VetoAgent):
    """
    Risk Management Agent with VETO POWER

    Responsibilities:
    - Position sizing (Kelly Criterion)
    - Risk validation (VaR, exposure limits)
    - Portfolio risk metrics
    - Circuit breakers
    - Trade validation (4-stage)
    - VETO power over risky trades
    """

    def __init__(self, name: str = "RiskAgent", config: Dict[str, Any] = None):
        if config is None:
            config = {}

        super().__init__(
            name=name,
            role="Risk Manager (VETO POWER)",
            config=config,
            weight=config.get('weight', 1.0)  # Risk has full weight
        )

        # Risk parameters
        self.max_position_size = config.get('max_position_pct', 0.02)  # 2% per trade
        self.max_total_exposure = config.get('max_total_exposure', 0.06)  # 6% total
        self.max_leverage = config.get('max_leverage', 2.0)
        self.max_drawdown = config.get('max_drawdown', 0.15)  # 15%
        self.daily_loss_limit = config.get('daily_loss_limit', 0.05)  # 5%
        self.var_limit = config.get('var_limit', 0.10)  # 10% VaR

        # Kelly parameters
        self.fractional_kelly = config.get('fractional_kelly', 0.5)  # Half Kelly
        self.min_win_rate = config.get('min_win_rate', 0.40)  # Minimum 40% win rate

        # Circuit breaker thresholds
        self.consecutive_loss_limit = config.get('consecutive_loss_limit', 5)
        self.vix_threshold = config.get('vix_threshold', 30)

        # Tracking
        self.consecutive_losses = 0
        self.daily_pnl = 0.0
        self.starting_equity = None

        logger.warning(f"{name} initialized - HAS VETO POWER over all trades")

    def analyze(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze risk factors

        Args:
            market_data: Complete market data from pipeline

        Returns:
            Risk analysis results
        """
        symbol = market_data.get('symbol')
        logger.debug(f"{self.name} analyzing risk for {symbol}")

        analysis = {
            'symbol': symbol,
            'timestamp': market_data.get('timestamp'),
            'risk_level': 'normal',
            'circuit_breakers': [],
            'warnings': [],
            'should_trade': True,
            'confidence': 1.0
        }

        # Check economic events
        economic_events = market_data.get('economic_events', {})
        if economic_events:
            should_avoid = economic_events.get('should_avoid_trading', False)
            if should_avoid:
                analysis['should_trade'] = False
                analysis['risk_level'] = 'high'
                analysis['warnings'].append('High-impact economic event imminent')

        # Check volatility
        indicators = market_data.get('technical_indicators', {})
        if indicators:
            atr = indicators.get('atr')
            if atr:
                # Compare to historical average (simplified)
                if atr > 0.02:  # High volatility threshold
                    analysis['risk_level'] = 'high'
                    analysis['warnings'].append(f'High volatility (ATR: {atr:.4f})')

        # Check data quality
        if not market_data.get('price_data'):
            analysis['should_trade'] = False
            analysis['warnings'].append('No price data available')

        return analysis

    def vote(self, analysis: Dict[str, Any]) -> str:
        """
        Risk agents use APPROVE/VETO instead of BUY/SELL

        Args:
            analysis: Risk analysis results

        Returns:
            Vote: 'APPROVE' or 'VETO'
        """
        should_trade = analysis.get('should_trade', True)
        risk_level = analysis.get('risk_level', 'normal')

        if not should_trade:
            return 'VETO'
        elif risk_level == 'high':
            return 'VETO'
        else:
            return 'APPROVE'

    def validate_trade(
        self,
        proposed_trade: Dict[str, Any],
        current_portfolio: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate proposed trade (4-stage validation)

        Args:
            proposed_trade: Proposed trade details
            current_portfolio: Current portfolio state

        Returns:
            Validation result with 'approved' boolean
        """
        logger.info(f"{self.name} validating trade: {proposed_trade.get('symbol')} {proposed_trade.get('direction')}")

        # Stage 1: Position size check
        stage1 = self._validate_position_size(proposed_trade)
        if not stage1['passed']:
            return self._veto_trade(1, stage1['reason'])

        # Stage 2: Risk checks
        stage2 = self._validate_risk_parameters(proposed_trade, current_portfolio)
        if not stage2['passed']:
            return self._veto_trade(2, stage2['reason'])

        # Stage 3: Circuit breakers
        stage3 = self._check_circuit_breakers(current_portfolio)
        if not stage3['passed']:
            return self._veto_trade(3, stage3['reason'])

        # Stage 4: Market conditions
        stage4 = self._validate_market_conditions(proposed_trade)
        if not stage4['passed']:
            return self._veto_trade(4, stage4['reason'])

        # All checks passed
        logger.success(f"{self.name} APPROVED trade")
        return {
            'approved': True,
            'veto': False,
            'stages': {
                'position_size': stage1,
                'risk_parameters': stage2,
                'circuit_breakers': stage3,
                'market_conditions': stage4
            }
        }

    def _validate_position_size(self, trade: Dict[str, Any]) -> Dict[str, bool]:
        """Stage 1: Validate position size"""
        position_size = trade.get('position_size_pct', 0.0)

        if position_size > self.max_position_size:
            return {
                'passed': False,
                'reason': f'Position size {position_size:.2%} exceeds max {self.max_position_size:.2%}'
            }

        if position_size <= 0:
            return {
                'passed': False,
                'reason': 'Invalid position size'
            }

        return {'passed': True, 'reason': 'Position size OK'}

    def _validate_risk_parameters(
        self,
        trade: Dict[str, Any],
        portfolio: Dict[str, Any]
    ) -> Dict[str, bool]:
        """Stage 2: Validate risk parameters"""

        # Total exposure check
        current_exposure = portfolio.get('total_exposure', 0.0)
        proposed_exposure = trade.get('position_size_pct', 0.0)
        total_exposure = current_exposure + proposed_exposure

        if total_exposure > self.max_total_exposure:
            return {
                'passed': False,
                'reason': f'Total exposure {total_exposure:.2%} exceeds max {self.max_total_exposure:.2%}'
            }

        # Leverage check
        leverage = trade.get('leverage', 1.0)
        if abs(leverage) > self.max_leverage:
            return {
                'passed': False,
                'reason': f'Leverage {leverage:.1f}x exceeds max {self.max_leverage:.1f}x'
            }

        # Stop loss check
        stop_loss = trade.get('stop_loss')
        entry_price = trade.get('entry_price')

        if not stop_loss or not entry_price:
            return {
                'passed': False,
                'reason': 'Missing stop loss or entry price'
            }

        # Validate stop loss distance
        stop_distance = abs((entry_price - stop_loss) / entry_price)
        if stop_distance > 0.05:  # Max 5% stop loss
            return {
                'passed': False,
                'reason': f'Stop loss distance {stop_distance:.2%} too wide'
            }

        return {'passed': True, 'reason': 'Risk parameters OK'}

    def _check_circuit_breakers(self, portfolio: Dict[str, Any]) -> Dict[str, bool]:
        """Stage 3: Check circuit breakers"""

        # Daily loss limit
        equity = portfolio.get('equity', 100.0)
        if self.starting_equity is None:
            self.starting_equity = equity

        daily_loss = (equity - self.starting_equity) / self.starting_equity

        if daily_loss <= -self.daily_loss_limit:
            return {
                'passed': False,
                'reason': f'Daily loss limit exceeded: {daily_loss:.2%}'
            }

        # Maximum drawdown
        drawdown = portfolio.get('drawdown', 0.0)
        if drawdown >= self.max_drawdown:
            return {
                'passed': False,
                'reason': f'Max drawdown exceeded: {drawdown:.2%}'
            }

        # Consecutive losses
        if self.consecutive_losses >= self.consecutive_loss_limit:
            return {
                'passed': False,
                'reason': f'Consecutive loss limit reached: {self.consecutive_losses}'
            }

        return {'passed': True, 'reason': 'Circuit breakers OK'}

    def _validate_market_conditions(self, trade: Dict[str, Any]) -> Dict[str, bool]:
        """Stage 4: Validate market conditions"""

        # Check spread
        spread = trade.get('spread')
        avg_spread = trade.get('avg_spread', 0.0001)

        if spread and avg_spread:
            if spread > avg_spread * 3:
                return {
                    'passed': False,
                    'reason': f'Spread too wide: {spread:.5f} (avg: {avg_spread:.5f})'
                }

        # Check liquidity
        volume = trade.get('volume')
        avg_volume = trade.get('avg_volume')

        if volume and avg_volume:
            if volume < avg_volume * 0.5:
                return {
                    'passed': False,
                    'reason': 'Low liquidity'
                }

        return {'passed': True, 'reason': 'Market conditions OK'}

    def _veto_trade(self, stage: int, reason: str) -> Dict[str, Any]:
        """Veto a trade"""
        logger.warning(f"{self.name} VETO (Stage {stage}): {reason}")

        return {
            'approved': False,
            'veto': True,
            'stage': stage,
            'reason': reason
        }

    def calculate_position_size(
        self,
        strategy_stats: Dict[str, Any],
        account_balance: float,
        regime_volatility: float = 0.015
    ) -> Dict[str, Any]:
        """
        Calculate position size using Kelly Criterion

        Args:
            strategy_stats: Historical strategy statistics
            account_balance: Current account balance
            regime_volatility: Current market volatility

        Returns:
            Position sizing recommendation
        """
        win_rate = strategy_stats.get('win_rate', 0.5)
        avg_win = strategy_stats.get('avg_win', 0.02)
        avg_loss = strategy_stats.get('avg_loss', 0.01)

        # Check minimum win rate
        if win_rate < self.min_win_rate:
            logger.warning(f"Win rate {win_rate:.2%} below minimum {self.min_win_rate:.2%}")
            return {
                'risk_percentage': 0.0,
                'risk_amount': 0.0,
                'position_size': 0.0,
                'reason': 'Win rate too low'
            }

        # Calculate Kelly percentage
        if avg_loss == 0:
            kelly_pct = 0.0
        else:
            b = avg_win / avg_loss  # Win/loss ratio
            kelly_pct = (win_rate * b - (1 - win_rate)) / b

        # Apply fractional Kelly
        kelly_pct = kelly_pct * self.fractional_kelly

        # Regime adjustment (reduce size in high volatility)
        regime_multiplier = 1.0
        if regime_volatility > 0.025:  # High volatility
            regime_multiplier = 0.5
        elif regime_volatility > 0.020:
            regime_multiplier = 0.75

        # Apply regime adjustment
        kelly_pct = kelly_pct * regime_multiplier

        # Cap at maximum position size
        risk_pct = min(max(kelly_pct, 0.01), self.max_position_size)

        # Calculate risk amount
        risk_amount = account_balance * risk_pct

        return {
            'risk_percentage': risk_pct,
            'risk_amount': risk_amount,
            'base_kelly': kelly_pct / self.fractional_kelly if self.fractional_kelly > 0 else 0,
            'fractional_kelly': kelly_pct,
            'regime_multiplier': regime_multiplier,
            'position_size_pct': risk_pct
        }

    def record_trade_result(self, profit: float):
        """
        Record trade result for circuit breaker tracking

        Args:
            profit: Trade profit/loss
        """
        if profit < 0:
            self.consecutive_losses += 1
        else:
            self.consecutive_losses = 0

        self.daily_pnl += profit

        logger.debug(
            f"{self.name} trade result: {profit:+.2f}, "
            f"consecutive losses: {self.consecutive_losses}"
        )

    def reset_daily(self):
        """Reset daily tracking (call at market open)"""
        self.starting_equity = None
        self.daily_pnl = 0.0
        logger.info(f"{self.name} daily reset")

    def get_reasoning(self, analysis: Dict[str, Any]) -> str:
        """Generate detailed reasoning"""
        vote = self.vote(analysis)
        risk_level = analysis.get('risk_level', 'normal')
        warnings = analysis.get('warnings', [])

        reasoning = f"{self.name}: {vote} (risk level: {risk_level})\n"

        if warnings:
            reasoning += "Warnings:\n"
            for warning in warnings:
                reasoning += f"  - {warning}\n"

        return reasoning
