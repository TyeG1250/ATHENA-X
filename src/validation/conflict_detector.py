"""
ATHENA-X Conflict Detector
Detects conflicts between proposed trades and existing positions
"""

from typing import Dict, Any, List
from loguru import logger


class ConflictDetector:
    """
    Detects trade conflicts

    Checks:
    - Opposite positions in same symbol
    - Sector concentration
    - Correlation limits
    - Position overlap
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize conflict detector

        Args:
            config: Configuration dictionary
        """
        self.config = config

        # Limits
        self.max_sector_exposure = config.get('conflict_detection', {}).get('max_sector_exposure', 0.15)
        self.max_correlation = config.get('conflict_detection', {}).get('max_correlation', 0.7)
        self.allow_opposite_positions = config.get('conflict_detection', {}).get('allow_opposite_positions', False)

        logger.info(f"Conflict detector initialized (max sector: {self.max_sector_exposure:.0%})")

    def detect(
        self,
        proposed_trade: Dict[str, Any],
        current_portfolio: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Detect conflicts

        Args:
            proposed_trade: Proposed trade
            current_portfolio: Current portfolio state

        Returns:
            Conflict detection result
        """
        logger.debug(f"Checking conflicts for {proposed_trade.get('symbol')}")

        conflicts = []

        # Check opposite positions
        opposite_check = self._check_opposite_positions(proposed_trade, current_portfolio)
        if not opposite_check['passed']:
            conflicts.append(opposite_check)

        # Check sector concentration
        sector_check = self._check_sector_concentration(proposed_trade, current_portfolio)
        if not sector_check['passed']:
            conflicts.append(sector_check)

        # Check correlation
        correlation_check = self._check_correlation(proposed_trade, current_portfolio)
        if not correlation_check['passed']:
            conflicts.append(correlation_check)

        # Overall result
        passed = len(conflicts) == 0

        if not passed:
            reasons = [c['reason'] for c in conflicts]
            reason = f"Conflicts detected: {'; '.join(reasons)}"
            logger.warning(reason)
        else:
            reason = "No conflicts detected"
            logger.debug(reason)

        return {
            'passed': passed,
            'reason': reason,
            'conflicts': conflicts,
            'score': 1.0 if passed else 0.0
        }

    def _check_opposite_positions(
        self,
        trade: Dict[str, Any],
        portfolio: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Check for opposite positions in same symbol"""
        symbol = trade.get('symbol')
        direction = trade.get('direction')

        positions = portfolio.get('positions', [])

        for pos in positions:
            if pos.get('symbol') == symbol:
                pos_direction = pos.get('direction')

                if pos_direction != direction and not self.allow_opposite_positions:
                    return {
                        'passed': False,
                        'type': 'opposite_position',
                        'reason': f"Opposite {pos_direction} position exists in {symbol}"
                    }

        return {'passed': True}

    def _check_sector_concentration(
        self,
        trade: Dict[str, Any],
        portfolio: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Check sector concentration"""
        symbol = trade.get('symbol')
        sector = self._get_sector(symbol)

        if not sector:
            return {'passed': True}  # Unknown sector

        # Calculate current sector exposure
        positions = portfolio.get('positions', [])
        sector_exposure = sum(
            pos.get('exposure', 0)
            for pos in positions
            if self._get_sector(pos.get('symbol')) == sector
        )

        # Add proposed trade
        proposed_exposure = trade.get('position_size_pct', 0.0)
        total_sector_exposure = sector_exposure + proposed_exposure

        if total_sector_exposure > self.max_sector_exposure:
            return {
                'passed': False,
                'type': 'sector_concentration',
                'reason': f"Sector {sector} exposure {total_sector_exposure:.2%} exceeds max {self.max_sector_exposure:.2%}"
            }

        return {'passed': True}

    def _check_correlation(
        self,
        trade: Dict[str, Any],
        portfolio: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Check correlation with existing positions"""
        symbol = trade.get('symbol')
        positions = portfolio.get('positions', [])

        high_corr_positions = []

        for pos in positions:
            pos_symbol = pos.get('symbol')

            # Calculate correlation (simplified)
            corr = self._get_correlation(symbol, pos_symbol)

            if abs(corr) > self.max_correlation:
                high_corr_positions.append({
                    'symbol': pos_symbol,
                    'correlation': corr,
                    'exposure': pos.get('exposure', 0)
                })

        if high_corr_positions:
            total_corr_exposure = sum(p['exposure'] for p in high_corr_positions)

            if total_corr_exposure > 0.10:  # 10% of account
                return {
                    'passed': False,
                    'type': 'high_correlation',
                    'reason': f"High correlation with {len(high_corr_positions)} positions (total exposure: {total_corr_exposure:.2%})",
                    'correlated_positions': high_corr_positions
                }

        return {'passed': True}

    def _get_sector(self, symbol: str) -> str:
        """Get sector for symbol (simplified mapping)"""
        # Forex pairs
        if '_' in symbol:
            parts = symbol.split('_')
            if len(parts) == 2:
                return 'forex'

        # Commodities
        if symbol in ['XAU_USD', 'XAG_USD']:
            return 'metals'
        if symbol in ['BCO_USD', 'NATGAS_USD']:
            return 'energy'

        # Indices
        if symbol in ['SPX500_USD', 'NAS100_USD', 'US30_USD']:
            return 'indices'

        return 'unknown'

    def _get_correlation(self, symbol1: str, symbol2: str) -> float:
        """
        Get correlation between two symbols (simplified)

        In production, this would use historical correlation matrix
        """
        # Same symbol = perfect correlation
        if symbol1 == symbol2:
            return 1.0

        # Forex pairs with shared currencies
        if '_' in symbol1 and '_' in symbol2:
            parts1 = symbol1.split('_')
            parts2 = symbol2.split('_')

            # Shared currency = some correlation
            if parts1[0] == parts2[0] or parts1[1] == parts2[1]:
                return 0.6

        # Same sector = moderate correlation
        if self._get_sector(symbol1) == self._get_sector(symbol2):
            return 0.5

        # Default: low correlation
        return 0.2
