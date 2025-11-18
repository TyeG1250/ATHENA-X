"""
ATHENA-X Signal Quality Validator
Validates trading signal quality using LLM reasoning analysis
"""

from typing import Dict, Any, Optional
from loguru import logger
import re


class SignalQualityValidator:
    """
    Validates trading signal quality

    Checks:
    - Confidence thresholds
    - Agent consensus
    - Data recency
    - Reasoning quality
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize signal quality validator

        Args:
            config: Validation configuration
        """
        self.config = config

        # Thresholds
        self.min_confidence = config.get('signal_quality', {}).get('min_confidence', 0.80)
        self.min_consensus = config.get('signal_quality', {}).get('min_consensus', 0.70)
        self.max_data_age = config.get('signal_quality', {}).get('max_data_age_seconds', 300)
        self.min_reasoning_score = config.get('signal_quality', {}).get('min_reasoning_score', 0.70)

        logger.info(f"Signal quality validator initialized (min confidence: {self.min_confidence:.0%})")

    def validate(
        self,
        proposed_trade: Dict[str, Any],
        market_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validate signal quality

        Args:
            proposed_trade: Proposed trade details
            market_data: Market data used for decision

        Returns:
            Validation result
        """
        logger.debug("Validating signal quality...")

        checks = {
            'confidence': self._check_confidence(proposed_trade),
            'consensus': self._check_consensus(proposed_trade),
            'data_recency': self._check_data_recency(market_data),
            'reasoning': self._check_reasoning(proposed_trade)
        }

        # Calculate overall score
        passed_checks = sum(1 for v in checks.values() if v['passed'])
        total_checks = len(checks)
        score = passed_checks / total_checks if total_checks > 0 else 0

        # All checks must pass
        passed = all(check['passed'] for check in checks.values())

        if not passed:
            failed = [k for k, v in checks.items() if not v['passed']]
            reason = f"Signal quality checks failed: {', '.join(failed)}"
            logger.warning(reason)
        else:
            reason = "All signal quality checks passed"
            logger.debug(reason)

        return {
            'passed': passed,
            'score': score,
            'reason': reason,
            'checks': checks
        }

    def _check_confidence(self, trade: Dict[str, Any]) -> Dict[str, Any]:
        """Check confidence threshold"""
        confidence = trade.get('confidence', 0.0)

        passed = confidence >= self.min_confidence

        return {
            'passed': passed,
            'confidence': confidence,
            'threshold': self.min_confidence,
            'reason': f"Confidence {confidence:.2%} {'≥' if passed else '<'} {self.min_confidence:.2%}"
        }

    def _check_consensus(self, trade: Dict[str, Any]) -> Dict[str, Any]:
        """Check agent consensus"""
        agreement = trade.get('agreement', 0.0)

        passed = agreement >= self.min_consensus

        return {
            'passed': passed,
            'agreement': agreement,
            'threshold': self.min_consensus,
            'reason': f"Consensus {agreement:.2%} {'≥' if passed else '<'} {self.min_consensus:.2%}"
        }

    def _check_data_recency(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Check data recency"""
        from datetime import datetime

        timestamp = market_data.get('timestamp')

        if not timestamp:
            return {
                'passed': False,
                'reason': 'No timestamp in market data'
            }

        # Calculate age
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)

        age_seconds = (datetime.now() - timestamp).total_seconds()

        passed = age_seconds <= self.max_data_age

        return {
            'passed': passed,
            'age_seconds': age_seconds,
            'max_age': self.max_data_age,
            'reason': f"Data age {age_seconds:.0f}s {'≤' if passed else '>'} {self.max_data_age}s"
        }

    def _check_reasoning(self, trade: Dict[str, Any]) -> Dict[str, Any]:
        """Check reasoning quality"""
        # Get agent analyses
        analyses = trade.get('analyses', {})

        if not analyses:
            return {
                'passed': False,
                'score': 0.0,
                'reason': 'No analyses available'
            }

        # Simple reasoning quality check
        # In production, this could use an LLM to evaluate reasoning
        reasoning_scores = []

        for agent_name, analysis in analyses.items():
            # Check if analysis has key components
            score = 0.0

            # Has score/confidence
            if 'confidence' in analysis or 'score' in analysis:
                score += 0.3

            # Has signals/reasoning
            if 'signals' in analysis or 'reasoning' in analysis:
                score += 0.4

            # Has specific metrics
            if any(k in analysis for k in ['trend', 'momentum', 'sentiment', 'risk_level']):
                score += 0.3

            reasoning_scores.append(score)

        avg_score = sum(reasoning_scores) / len(reasoning_scores) if reasoning_scores else 0.0

        passed = avg_score >= self.min_reasoning_score

        return {
            'passed': passed,
            'score': avg_score,
            'threshold': self.min_reasoning_score,
            'reason': f"Reasoning quality {avg_score:.2%} {'≥' if passed else '<'} {self.min_reasoning_score:.2%}"
        }
