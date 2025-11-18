"""
ATHENA-X Correlation Risk Manager
Manages correlation-based risk and position concentration
"""

from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd
from loguru import logger


class CorrelationManager:
    """
    Correlation-based risk management

    Features:
    - Correlation matrix tracking
    - Position concentration limits
    - Diversification scoring
    - Correlation-based position sizing
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize correlation manager

        Args:
            config: Configuration dictionary
        """
        self.config = config

        # Limits
        self.max_correlation = config.get('correlation', {}).get('max_correlation', 0.7)
        self.max_correlated_exposure = config.get('correlation', {}).get('max_correlated_exposure', 0.10)

        # Correlation matrix (will be updated with historical data)
        self.correlation_matrix = {}

        logger.info(f"Correlation manager initialized (max correlation: {self.max_correlation})")

    def calculate_correlation(
        self,
        symbol1: str,
        symbol2: str,
        returns1: Optional[List[float]] = None,
        returns2: Optional[List[float]] = None
    ) -> float:
        """
        Calculate correlation between two symbols

        Args:
            symbol1: First symbol
            symbol2: Second symbol
            returns1: Historical returns for symbol1 (optional)
            returns2: Historical returns for symbol2 (optional)

        Returns:
            Correlation coefficient (-1 to 1)
        """
        # Check cache first
        cache_key = tuple(sorted([symbol1, symbol2]))
        if cache_key in self.correlation_matrix:
            return self.correlation_matrix[cache_key]

        # If returns provided, calculate correlation
        if returns1 and returns2 and len(returns1) == len(returns2) and len(returns1) > 1:
            try:
                corr = np.corrcoef(returns1, returns2)[0, 1]
                self.correlation_matrix[cache_key] = corr
                return corr
            except Exception as e:
                logger.error(f"Correlation calculation failed: {str(e)}")

        # Otherwise, use heuristic correlation
        corr = self._heuristic_correlation(symbol1, symbol2)
        self.correlation_matrix[cache_key] = corr

        return corr

    def _heuristic_correlation(self, symbol1: str, symbol2: str) -> float:
        """
        Heuristic correlation estimation (fallback)

        Args:
            symbol1: First symbol
            symbol2: Second symbol

        Returns:
            Estimated correlation
        """
        # Same symbol = perfect correlation
        if symbol1 == symbol2:
            return 1.0

        # Forex pairs with shared currencies
        if '_' in symbol1 and '_' in symbol2:
            parts1 = symbol1.split('_')
            parts2 = symbol2.split('_')

            # Same pair = perfect correlation
            if set(parts1) == set(parts2):
                return 1.0 if parts1 == parts2 else -0.9  # Inverse pair

            # One shared currency = moderate correlation
            shared = set(parts1) & set(parts2)
            if len(shared) == 1:
                return 0.6

        # Same asset class correlation
        asset_class1 = self._get_asset_class(symbol1)
        asset_class2 = self._get_asset_class(symbol2)

        if asset_class1 == asset_class2:
            if asset_class1 == 'forex':
                return 0.4  # Forex pairs moderately correlated
            elif asset_class1 == 'metals':
                return 0.7  # Metals highly correlated
            elif asset_class1 == 'indices':
                return 0.8  # Indices highly correlated
            elif asset_class1 == 'energy':
                return 0.6  # Energy commodities moderately correlated

        # Different asset classes = low correlation
        return 0.2

    def _get_asset_class(self, symbol: str) -> str:
        """Get asset class for symbol"""
        if '_' in symbol:
            parts = symbol.split('_')
            if len(parts) == 2:
                # Metals
                if parts[0] in ['XAU', 'XAG', 'XPT', 'XPD']:
                    return 'metals'
                # Currencies
                return 'forex'

        # Indices
        if symbol in ['SPX500_USD', 'NAS100_USD', 'US30_USD', 'UK100_GBP']:
            return 'indices'

        # Energy
        if symbol in ['BCO_USD', 'WTI_USD', 'NATGAS_USD']:
            return 'energy'

        return 'unknown'

    def check_correlation_risk(
        self,
        proposed_symbol: str,
        proposed_exposure: float,
        current_positions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Check correlation risk for proposed trade

        Args:
            proposed_symbol: Symbol to trade
            proposed_exposure: Proposed position exposure
            current_positions: Current portfolio positions

        Returns:
            Correlation risk assessment
        """
        high_corr_positions = []
        total_corr_exposure = 0.0

        for pos in current_positions:
            pos_symbol = pos.get('symbol')
            pos_exposure = pos.get('exposure', 0.0)

            # Calculate correlation
            corr = self.calculate_correlation(proposed_symbol, pos_symbol)

            if abs(corr) > self.max_correlation:
                high_corr_positions.append({
                    'symbol': pos_symbol,
                    'correlation': corr,
                    'exposure': pos_exposure
                })
                total_corr_exposure += pos_exposure

        # Add proposed exposure
        total_corr_exposure += proposed_exposure

        # Check if exceeds limit
        risk_exceeded = total_corr_exposure > self.max_correlated_exposure

        return {
            'risk_exceeded': risk_exceeded,
            'total_correlated_exposure': total_corr_exposure,
            'max_allowed': self.max_correlated_exposure,
            'highly_correlated_positions': high_corr_positions,
            'position_count': len(high_corr_positions),
            'recommendation': 'REJECT' if risk_exceeded else 'APPROVE'
        }

    def calculate_diversification_score(
        self,
        positions: List[Dict[str, Any]]
    ) -> float:
        """
        Calculate portfolio diversification score

        Args:
            positions: List of positions

        Returns:
            Diversification score (0-1, higher is better)
        """
        if len(positions) <= 1:
            return 0.0  # No diversification with single position

        # Build correlation matrix
        symbols = [p.get('symbol') for p in positions]
        n = len(symbols)

        corr_matrix = np.zeros((n, n))

        for i in range(n):
            for j in range(n):
                if i == j:
                    corr_matrix[i, j] = 1.0
                else:
                    corr_matrix[i, j] = self.calculate_correlation(symbols[i], symbols[j])

        # Average correlation (excluding diagonal)
        avg_corr = (np.sum(corr_matrix) - n) / (n * n - n)

        # Diversification score = 1 - avg_correlation
        # Perfect diversification (corr = 0) = score 1.0
        # Perfect correlation (corr = 1) = score 0.0
        diversification_score = 1.0 - abs(avg_corr)

        return max(0.0, min(1.0, diversification_score))

    def adjust_position_size_for_correlation(
        self,
        proposed_size: float,
        proposed_symbol: str,
        current_positions: List[Dict[str, Any]]
    ) -> float:
        """
        Adjust position size based on correlation

        Args:
            proposed_size: Original position size
            proposed_symbol: Symbol to trade
            current_positions: Current positions

        Returns:
            Adjusted position size
        """
        if not current_positions:
            return proposed_size  # No adjustment needed

        # Calculate average correlation with existing positions
        correlations = []

        for pos in current_positions:
            pos_symbol = pos.get('symbol')
            corr = abs(self.calculate_correlation(proposed_symbol, pos_symbol))
            correlations.append(corr)

        avg_corr = np.mean(correlations)

        # Reduce size for high correlation
        # If avg correlation > 0.7, reduce by up to 50%
        if avg_corr > self.max_correlation:
            reduction_factor = 0.5  # Reduce to 50%
        elif avg_corr > 0.5:
            # Linear reduction between 0.5 and 0.7 correlation
            reduction_factor = 1.0 - (avg_corr - 0.5) * 2.5
        else:
            reduction_factor = 1.0  # No reduction

        adjusted_size = proposed_size * reduction_factor

        if adjusted_size < proposed_size:
            logger.info(
                f"Position size adjusted for correlation: "
                f"{proposed_size:.2%} → {adjusted_size:.2%} "
                f"(avg corr: {avg_corr:.2f})"
            )

        return adjusted_size

    def update_correlation_matrix(
        self,
        symbols: List[str],
        returns_data: Dict[str, List[float]]
    ):
        """
        Update correlation matrix with new data

        Args:
            symbols: List of symbols
            returns_data: Dictionary mapping symbol to returns
        """
        logger.info(f"Updating correlation matrix for {len(symbols)} symbols")

        for i, symbol1 in enumerate(symbols):
            for symbol2 in symbols[i:]:
                if symbol1 in returns_data and symbol2 in returns_data:
                    returns1 = returns_data[symbol1]
                    returns2 = returns_data[symbol2]

                    # Calculate and cache correlation
                    self.calculate_correlation(symbol1, symbol2, returns1, returns2)

        logger.info(f"Correlation matrix updated ({len(self.correlation_matrix)} pairs)")

    def get_correlation_matrix_df(self, symbols: List[str]) -> pd.DataFrame:
        """
        Get correlation matrix as DataFrame

        Args:
            symbols: List of symbols

        Returns:
            Correlation matrix DataFrame
        """
        n = len(symbols)
        matrix = np.zeros((n, n))

        for i, symbol1 in enumerate(symbols):
            for j, symbol2 in enumerate(symbols):
                matrix[i, j] = self.calculate_correlation(symbol1, symbol2)

        df = pd.DataFrame(matrix, index=symbols, columns=symbols)
        return df
