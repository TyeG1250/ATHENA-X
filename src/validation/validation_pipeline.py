"""
ATHENA-X Complete Validation Pipeline
4-stage comprehensive validation before trade execution
"""

from typing import Dict, Any
from datetime import datetime
from loguru import logger

from .signal_quality import SignalQualityValidator
from .conflict_detector import ConflictDetector


class ValidationPipeline:
    """
    Complete 4-stage validation pipeline

    Stage 1: Signal Quality (confidence, consensus, data recency, reasoning)
    Stage 2: Risk Parameters (via Risk Agent)
    Stage 3: Conflict Detection (opposite positions, sector, correlation)
    Stage 4: Market Conditions (volatility, liquidity, economic events)
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize validation pipeline

        Args:
            config: System configuration
        """
        self.config = config

        # Initialize validators
        self.signal_validator = SignalQualityValidator(config)
        self.conflict_detector = ConflictDetector(config)

        # Market condition thresholds
        self.max_vix = config.get('market_conditions', {}).get('max_vix', 30)
        self.min_volume_ratio = config.get('market_conditions', {}).get('min_volume_ratio', 0.5)
        self.max_spread_multiplier = config.get('market_conditions', {}).get('max_spread_multiplier', 2.0)

        logger.info("Validation pipeline initialized (4 stages)")

    def validate(
        self,
        proposed_trade: Dict[str, Any],
        market_data: Dict[str, Any],
        current_portfolio: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Run complete 4-stage validation

        Args:
            proposed_trade: Proposed trade details
            market_data: Current market data
            current_portfolio: Current portfolio state

        Returns:
            Validation result with approval/rejection
        """
        logger.info("="*60)
        logger.info("VALIDATION PIPELINE - 4 STAGES")
        logger.info("="*60)

        # Stage 1: Signal Quality
        logger.info("Stage 1: Signal Quality Validation")
        stage1 = self.signal_validator.validate(proposed_trade, market_data)

        if not stage1['passed']:
            return self._reject(1, stage1['reason'], {
                'signal_quality': stage1
            })

        logger.success(f"  ✓ Stage 1 passed (score: {stage1['score']:.2%})")

        # Stage 2: Risk Parameters (handled by Risk Agent in orchestrator)
        # This stage is a placeholder - actual validation done by RiskAgent.validate_trade()
        logger.info("Stage 2: Risk Parameters (handled by Risk Agent)")
        stage2 = {'passed': True, 'reason': 'Risk validation delegated to Risk Agent'}
        logger.success("  ✓ Stage 2 delegated to Risk Agent")

        # Stage 3: Conflict Detection
        logger.info("Stage 3: Conflict Detection")
        stage3 = self.conflict_detector.detect(proposed_trade, current_portfolio)

        if not stage3['passed']:
            return self._reject(3, stage3['reason'], {
                'signal_quality': stage1,
                'risk_parameters': stage2,
                'conflict_detection': stage3
            })

        logger.success(f"  ✓ Stage 3 passed (no conflicts)")

        # Stage 4: Market Conditions
        logger.info("Stage 4: Market Conditions")
        stage4 = self._validate_market_conditions(market_data, proposed_trade)

        if not stage4['passed']:
            return self._reject(4, stage4['reason'], {
                'signal_quality': stage1,
                'risk_parameters': stage2,
                'conflict_detection': stage3,
                'market_conditions': stage4
            })

        logger.success(f"  ✓ Stage 4 passed")

        # All stages passed
        logger.success("="*60)
        logger.success("VALIDATION COMPLETE - ALL STAGES PASSED")
        logger.success("="*60)

        return {
            'approved': True,
            'passed': True,
            'stages_passed': 4,
            'total_stages': 4,
            'stages': {
                'signal_quality': stage1,
                'risk_parameters': stage2,
                'conflict_detection': stage3,
                'market_conditions': stage4
            },
            'timestamp': datetime.now()
        }

    def _validate_market_conditions(
        self,
        market_data: Dict[str, Any],
        trade: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Stage 4: Validate market conditions"""
        checks = []

        # Volatility check (VIX or ATR)
        indicators = market_data.get('technical_indicators', {})
        atr = indicators.get('atr', 0)

        if atr > 0.03:  # High volatility
            checks.append({
                'passed': False,
                'check': 'volatility',
                'reason': f"High volatility (ATR: {atr:.4f})"
            })
        else:
            checks.append({'passed': True, 'check': 'volatility'})

        # Liquidity check
        volume = indicators.get('volume')
        avg_volume = indicators.get('volume_sma')

        if volume and avg_volume:
            volume_ratio = volume / avg_volume

            if volume_ratio < self.min_volume_ratio:
                checks.append({
                    'passed': False,
                    'check': 'liquidity',
                    'reason': f"Low volume ({volume_ratio:.2f}x average)"
                })
            else:
                checks.append({'passed': True, 'check': 'liquidity'})

        # Spread check
        spread = trade.get('spread', 0)
        avg_spread = trade.get('avg_spread', 0.0001)

        if spread > avg_spread * self.max_spread_multiplier:
            checks.append({
                'passed': False,
                'check': 'spread',
                'reason': f"Wide spread ({spread:.5f} vs avg {avg_spread:.5f})"
            })
        else:
            checks.append({'passed': True, 'check': 'spread'})

        # Economic events check
        economic_events = market_data.get('economic_events', {})
        should_avoid = economic_events.get('should_avoid_trading', False)

        if should_avoid:
            checks.append({
                'passed': False,
                'check': 'economic_events',
                'reason': "High-impact economic event imminent"
            })
        else:
            checks.append({'passed': True, 'check': 'economic_events'})

        # Overall result
        failed_checks = [c for c in checks if not c['passed']]

        if failed_checks:
            reasons = [c['reason'] for c in failed_checks]
            return {
                'passed': False,
                'reason': f"Market conditions unfavorable: {'; '.join(reasons)}",
                'checks': checks
            }

        return {
            'passed': True,
            'reason': 'Market conditions favorable',
            'checks': checks
        }

    def _reject(self, stage: int, reason: str, stages: Dict[str, Any]) -> Dict[str, Any]:
        """Reject trade at specific stage"""
        logger.warning(f"✗ VALIDATION FAILED at Stage {stage}")
        logger.warning(f"  Reason: {reason}")

        return {
            'approved': False,
            'passed': False,
            'failed_stage': stage,
            'reason': reason,
            'stages': stages,
            'timestamp': datetime.now()
        }
