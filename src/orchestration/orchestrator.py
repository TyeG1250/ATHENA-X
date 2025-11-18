"""
ATHENA-X Orchestrator (CEO)
Coordinates all agents and makes final trading decisions
"""

from typing import Dict, Any, List, Optional, TYPE_CHECKING
from datetime import datetime
from loguru import logger
import numpy as np

from ..agents.base_agent import BaseAgent, VetoAgent
from ..agents.technical_agent import TechnicalAnalysisAgent
from ..agents.sentiment_agent import SentimentAnalysisAgent
from ..agents.risk_agent import RiskManagementAgent

if TYPE_CHECKING:
    from ..data.oanda_client import OANDAClient


class ATHENAOrchestrator:
    """
    CEO Orchestrator for ATHENA-X

    Responsibilities:
    - Coordinate all agents
    - Collect votes and analyses
    - Calculate consensus (weighted voting)
    - Enforce veto power
    - Make final trading decisions
    - Track performance
    """

    def __init__(
        self,
        config: Dict[str, Any],
        oanda_client: Optional['OANDAClient'] = None
    ):
        """
        Initialize orchestrator

        Args:
            config: System configuration
            oanda_client: Optional OANDA client for live account data
        """
        self.config = config
        self.oanda_client = oanda_client

        # Initialize agents
        self.agents = self._initialize_agents(config)

        # Consensus parameters
        self.consensus_threshold = config.get('consensus', {}).get('agreement_threshold', 0.70)
        self.veto_enabled = config.get('consensus', {}).get('veto_enabled', True)

        # Performance tracking
        self.trade_log = []
        self.total_trades = 0
        self.approved_trades = 0
        self.vetoed_trades = 0

        # Account info
        self._cached_account_balance = None
        self._last_balance_fetch = None

        logger.info(f"ATHENA Orchestrator initialized with {len(self.agents)} agents")
        logger.info(f"Consensus threshold: {self.consensus_threshold:.0%}, Veto enabled: {self.veto_enabled}")

        if self.oanda_client:
            logger.info("✓ OANDA client connected - will use live account balance")
        else:
            logger.warning("No OANDA client - will use config initial_capital for testing")

    def get_account_balance(self) -> float:
        """
        Get current account balance from OANDA API or config

        Returns:
            Current account balance
        """
        from datetime import timedelta

        # Use cache if recent (< 60 seconds old)
        if self._cached_account_balance and self._last_balance_fetch:
            if (datetime.now() - self._last_balance_fetch) < timedelta(seconds=60):
                return self._cached_account_balance

        # Try OANDA API first
        if self.oanda_client:
            try:
                account_summary = self.oanda_client.get_account_summary()
                balance = account_summary.get('balance', 0)

                if balance > 0:
                    self._cached_account_balance = balance
                    self._last_balance_fetch = datetime.now()
                    logger.debug(f"Fetched account balance from OANDA: ${balance:.2f}")
                    return balance

            except Exception as e:
                logger.warning(f"Failed to get OANDA balance: {e}, using config fallback")

        # Fallback to config
        config_capital = self.config.get('trading', {}).get('initial_capital', 250.0)
        logger.debug(f"Using config initial_capital: ${config_capital:.2f}")
        return config_capital

    def get_current_portfolio(self) -> Dict[str, Any]:
        """
        Get current portfolio state from OANDA API or construct default

        Returns:
            Portfolio dictionary with equity, positions, exposure
        """
        portfolio = {
            'equity': self.get_account_balance(),
            'total_exposure': 0.0,
            'positions': []
        }

        # Get open positions from OANDA if available
        if self.oanda_client:
            try:
                positions = self.oanda_client.get_open_positions()
                portfolio['positions'] = positions

                # Calculate total exposure
                total_exposure = sum(
                    abs(pos.get('long_units', 0)) + abs(pos.get('short_units', 0))
                    for pos in positions
                )
                portfolio['total_exposure'] = total_exposure

            except Exception as e:
                logger.warning(f"Failed to get OANDA positions: {e}")

        return portfolio

    def _initialize_agents(self, config: Dict[str, Any]) -> Dict[str, BaseAgent]:
        """Initialize all trading agents"""
        agents = {}

        # Technical Analysis Agent
        technical_config = config.get('agents', {}).get('technical_agent', {})
        agents['technical'] = TechnicalAnalysisAgent(config=technical_config)

        # Sentiment Analysis Agent
        sentiment_config = config.get('agents', {}).get('sentiment_agent', {})
        agents['sentiment'] = SentimentAnalysisAgent(config=sentiment_config)

        # Risk Management Agent (VETO POWER)
        risk_config = config.get('agents', {}).get('risk_agent', {})
        agents['risk'] = RiskManagementAgent(config=risk_config)

        logger.info("Agents initialized:")
        for name, agent in agents.items():
            veto_status = " (VETO POWER)" if isinstance(agent, VetoAgent) else ""
            logger.info(f"  - {agent.name}: weight={agent.weight:.2f}{veto_status}")

        return agents

    def evaluate_opportunity(
        self,
        symbol: str,
        market_data: Dict[str, Any],
        current_portfolio: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Main decision loop - evaluate trading opportunity

        Args:
            symbol: Trading symbol
            market_data: Complete market data from pipeline
            current_portfolio: Current portfolio state

        Returns:
            Trading decision
        """
        logger.info(f"{'='*60}")
        logger.info(f"Evaluating opportunity: {symbol}")
        logger.info(f"{'='*60}")

        # Get current portfolio (from OANDA API if available)
        if current_portfolio is None:
            current_portfolio = self.get_current_portfolio()

        logger.info(f"Portfolio: ${current_portfolio['equity']:.2f}, Exposure: {current_portfolio['total_exposure']:.2%}, Positions: {len(current_portfolio.get('positions', []))}")

        # Stage 1: Parallel agent analysis
        logger.info("Stage 1: Agent Analysis")
        analyses = self._run_agent_analyses(market_data)

        # Stage 2: Collect votes
        logger.info("Stage 2: Voting")
        votes = self._collect_votes(analyses)

        # Stage 3: Calculate consensus
        logger.info("Stage 3: Consensus Calculation")
        consensus = self._calculate_consensus(votes)

        # If no consensus, reject
        if consensus['agreement'] < self.consensus_threshold:
            return self._reject_trade(
                symbol,
                f"No consensus reached (agreement: {consensus['agreement']:.2%})"
            )

        # If consensus is NEUTRAL, no trade
        if consensus['direction'] == 'NEUTRAL':
            return self._reject_trade(symbol, "Consensus is NEUTRAL")

        # Stage 4: Risk check (preliminary)
        logger.info("Stage 4: Risk Check")
        risk_analysis = analyses.get('risk', {})
        risk_vote = votes.get('risk')

        if risk_vote == 'VETO':
            return self._reject_trade(
                symbol,
                f"Risk agent VETO: {risk_analysis.get('warnings', ['Risk too high'])}"
            )

        # Stage 5: Position sizing
        logger.info("Stage 5: Position Sizing")
        position = self._calculate_position_size(
            symbol,
            consensus,
            market_data,
            current_portfolio
        )

        if position['position_size_pct'] == 0:
            return self._reject_trade(symbol, "Position size calculation failed")

        # Stage 6: Build proposed trade
        proposed_trade = self._build_proposed_trade(
            symbol,
            consensus,
            position,
            market_data
        )

        # Stage 7: Final risk validation (4-stage with VETO power)
        logger.info("Stage 7: Final Risk Validation")
        risk_agent = self.agents['risk']
        validation = risk_agent.validate_trade(proposed_trade, current_portfolio)

        if not validation['approved']:
            self.vetoed_trades += 1
            return self._reject_trade(
                symbol,
                f"Risk VETO (Stage {validation.get('stage')}): {validation.get('reason')}"
            )

        # Stage 8: All checks passed - EXECUTE
        logger.success("Stage 8: APPROVED FOR EXECUTION")
        self.approved_trades += 1

        decision = {
            'decision': 'EXECUTE',
            'symbol': symbol,
            'direction': consensus['direction'],
            'confidence': consensus['confidence'],
            'agreement': consensus['agreement'],
            'position_size_pct': position['position_size_pct'],
            'position_size_units': position['position_size_units'],
            'entry_price': proposed_trade['entry_price'],
            'stop_loss': proposed_trade['stop_loss'],
            'take_profit': proposed_trade['take_profit'],
            'risk_amount': position['risk_amount'],
            'agent_votes': votes,
            'analyses': {
                'technical': analyses.get('technical', {}),
                'sentiment': analyses.get('sentiment', {}),
                'risk': risk_analysis
            },
            'timestamp': datetime.now()
        }

        # Log decision
        self._log_decision(decision)

        return decision

    def _run_agent_analyses(self, market_data: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """Run analyses from all agents in parallel"""
        analyses = {}

        for name, agent in self.agents.items():
            if not agent.enabled:
                logger.debug(f"Agent {name} disabled, skipping")
                continue

            try:
                logger.debug(f"Running {agent.name} analysis...")
                analysis = agent.analyze(market_data)
                analyses[name] = analysis
                logger.debug(f"{agent.name} analysis complete")

            except Exception as e:
                logger.error(f"Agent {name} analysis failed: {str(e)}")
                analyses[name] = {'error': str(e)}

        return analyses

    def _collect_votes(self, analyses: Dict[str, Dict[str, Any]]) -> Dict[str, str]:
        """Collect votes from all agents"""
        votes = {}

        for name, agent in self.agents.items():
            if name not in analyses or 'error' in analyses[name]:
                continue

            try:
                vote = agent.vote(analyses[name])
                votes[name] = vote
                logger.info(f"  {agent.name}: {vote}")

            except Exception as e:
                logger.error(f"Agent {name} vote failed: {str(e)}")

        return votes

    def _calculate_consensus(self, votes: Dict[str, str]) -> Dict[str, Any]:
        """
        Calculate weighted consensus

        Args:
            votes: Dictionary of agent votes

        Returns:
            Consensus result
        """
        # Extract weights
        weights = {
            name: self.agents[name].weight
            for name in votes.keys()
            if name in self.agents
        }

        # Calculate BUY/SELL scores
        buy_score = sum(
            weights[name]
            for name, vote in votes.items()
            if vote == 'BUY'
        )

        sell_score = sum(
            weights[name]
            for name, vote in votes.items()
            if vote == 'SELL'
        )

        neutral_score = sum(
            weights[name]
            for name, vote in votes.items()
            if vote == 'NEUTRAL'
        )

        total_weight = sum(weights.values())

        # Determine direction
        if buy_score > sell_score and buy_score > neutral_score:
            direction = 'BUY'
            agreement = buy_score / total_weight if total_weight > 0 else 0
            confidence = buy_score / total_weight if total_weight > 0 else 0
        elif sell_score > buy_score and sell_score > neutral_score:
            direction = 'SELL'
            agreement = sell_score / total_weight if total_weight > 0 else 0
            confidence = sell_score / total_weight if total_weight > 0 else 0
        else:
            direction = 'NEUTRAL'
            agreement = neutral_score / total_weight if total_weight > 0 else 0
            confidence = 0.0

        logger.info(f"  Consensus: {direction} (agreement: {agreement:.2%}, confidence: {confidence:.2%})")
        logger.info(f"  Scores - BUY: {buy_score:.2f}, SELL: {sell_score:.2f}, NEUTRAL: {neutral_score:.2f}")

        return {
            'direction': direction,
            'agreement': agreement,
            'confidence': confidence,
            'buy_score': buy_score,
            'sell_score': sell_score,
            'neutral_score': neutral_score
        }

    def _calculate_position_size(
        self,
        symbol: str,
        consensus: Dict[str, Any],
        market_data: Dict[str, Any],
        portfolio: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Calculate position size using Risk Agent"""
        risk_agent = self.agents['risk']

        # Get strategy statistics (simplified - use agent performance)
        strategy_stats = {
            'win_rate': 0.65,  # Default until we have history
            'avg_win': 0.02,
            'avg_loss': 0.01
        }

        # Get current regime volatility
        indicators = market_data.get('technical_indicators', {})
        atr = indicators.get('atr', 0.015)

        # Calculate position size
        account_balance = portfolio.get('equity', self.get_account_balance())
        position = risk_agent.calculate_position_size(
            strategy_stats=strategy_stats,
            account_balance=account_balance,
            regime_volatility=atr
        )

        # Calculate stop loss distance
        price = market_data.get('price_data', {}).get('bid', 0)
        if price > 0:
            stop_distance = atr * 2  # 2× ATR stop loss
            position['position_size_units'] = self._calculate_units(
                account_balance,
                position['risk_amount'],
                price,
                stop_distance
            )
        else:
            position['position_size_units'] = 0

        logger.info(f"  Position size: {position['position_size_pct']:.2%} (${position['risk_amount']:.2f})")

        return position

    def _calculate_units(
        self,
        account_balance: float,
        risk_amount: float,
        price: float,
        stop_distance: float
    ) -> float:
        """Calculate position size in units/lots"""
        if stop_distance == 0 or price == 0:
            return 0.0

        # For forex: pip value calculation
        # Simplified: risk_amount / (stop_distance * price)
        units = risk_amount / stop_distance

        return round(units, 2)

    def _build_proposed_trade(
        self,
        symbol: str,
        consensus: Dict[str, Any],
        position: Dict[str, Any],
        market_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Build proposed trade for validation"""
        price_data = market_data.get('price_data', {})
        indicators = market_data.get('technical_indicators', {})

        entry_price = price_data.get('bid', 0)
        atr = indicators.get('atr', 0.0001)

        # Calculate stop loss and take profit
        if consensus['direction'] == 'BUY':
            stop_loss = entry_price - (atr * 2)
            take_profit = entry_price + (atr * 4)  # 2:1 risk/reward
        else:  # SELL
            stop_loss = entry_price + (atr * 2)
            take_profit = entry_price - (atr * 4)

        return {
            'symbol': symbol,
            'direction': consensus['direction'],
            'entry_price': entry_price,
            'position_size_pct': position['position_size_pct'],
            'position_size_units': position['position_size_units'],
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'leverage': 1.0,
            'risk_amount': position['risk_amount'],
            'spread': price_data.get('ask', entry_price) - entry_price,
            'avg_spread': 0.0001,  # TODO: Get from historical data
            'volume': indicators.get('volume'),
            'avg_volume': indicators.get('volume_sma')
        }

    def _reject_trade(self, symbol: str, reason: str) -> Dict[str, Any]:
        """Reject trade with reason"""
        logger.warning(f"Trade REJECTED: {reason}")

        return {
            'decision': 'REJECT',
            'symbol': symbol,
            'reason': reason,
            'timestamp': datetime.now()
        }

    def _log_decision(self, decision: Dict[str, Any]):
        """Log trading decision"""
        self.total_trades += 1
        self.trade_log.append(decision)

        # Keep last 100 decisions
        if len(self.trade_log) > 100:
            self.trade_log = self.trade_log[-100:]

        logger.info(f"Decision logged. Total: {self.total_trades}, Approved: {self.approved_trades}, Vetoed: {self.vetoed_trades}")

    def update_agent_performance(self, trade_result: Dict[str, Any]):
        """
        Update all agents with trade result

        Args:
            trade_result: Trade outcome
        """
        for agent in self.agents.values():
            agent.update_performance(trade_result)

        # Update risk agent tracking
        risk_agent = self.agents['risk']
        risk_agent.record_trade_result(trade_result.get('profit', 0.0))

    def get_performance_summary(self) -> Dict[str, Any]:
        """Get orchestrator and agent performance summary"""
        return {
            'orchestrator': {
                'total_decisions': self.total_trades,
                'approved_trades': self.approved_trades,
                'vetoed_trades': self.vetoed_trades,
                'approval_rate': self.approved_trades / self.total_trades if self.total_trades > 0 else 0
            },
            'agents': {
                name: agent.get_performance_metrics()
                for name, agent in self.agents.items()
            }
        }

    def __repr__(self) -> str:
        """String representation"""
        return f"ATHENAOrchestrator(agents={len(self.agents)}, threshold={self.consensus_threshold:.0%})"
