"""
ATHENA-X Order Manager
Handles order execution, tracking, and management
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from loguru import logger
import time

from ..data.oanda_client import OANDAClient


class OrderManager:
    """
    Order execution and management

    Features:
    - Market and limit orders
    - Stop loss / take profit management
    - Order modification
    - Position tracking
    - Execution quality monitoring
    """

    def __init__(self, config: Dict[str, Any], oanda_client: Optional[OANDAClient] = None):
        """
        Initialize order manager

        Args:
            config: Configuration dictionary
            oanda_client: OANDA client instance
        """
        self.config = config
        self.oanda = oanda_client

        # Order tracking
        self.pending_orders = {}
        self.filled_orders = {}
        self.rejected_orders = {}

        # Execution statistics
        self.total_orders = 0
        self.filled_count = 0
        self.rejected_count = 0

        logger.info("Order manager initialized")

    def execute_trade(
        self,
        decision: Dict[str, Any],
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Execute trading decision

        Args:
            decision: Trading decision from orchestrator
            dry_run: If True, simulate execution without placing real order

        Returns:
            Execution result
        """
        symbol = decision.get('symbol')
        direction = decision.get('direction')
        size = decision.get('position_size_units', 0)

        logger.info(f"Executing trade: {direction} {size} units of {symbol}")

        if dry_run:
            return self._simulate_execution(decision)

        if not self.oanda:
            logger.error("OANDA client not available")
            return {
                'success': False,
                'error': 'OANDA client not initialized'
            }

        # Build order
        order_result = self._place_market_order(
            symbol=symbol,
            units=size if direction == 'BUY' else -size,
            stop_loss=decision.get('stop_loss'),
            take_profit=decision.get('take_profit')
        )

        # Track order
        self.total_orders += 1

        if order_result['success']:
            self.filled_count += 1
            order_id = order_result.get('order_id')
            self.filled_orders[order_id] = {
                'decision': decision,
                'result': order_result,
                'timestamp': datetime.now()
            }
            logger.success(f"Order filled: {order_id}")
        else:
            self.rejected_count += 1
            error = order_result.get('error', 'Unknown error')
            self.rejected_orders[symbol] = {
                'decision': decision,
                'error': error,
                'timestamp': datetime.now()
            }
            logger.error(f"Order rejected: {error}")

        return order_result

    def _place_market_order(
        self,
        symbol: str,
        units: float,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Place market order via OANDA

        Args:
            symbol: Trading symbol
            units: Position size (positive for buy, negative for sell)
            stop_loss: Stop loss price
            take_profit: Take profit price

        Returns:
            Order result
        """
        try:
            # Use OANDA client to place order
            from oandapyV20.endpoints.orders import OrderCreate

            order_data = {
                "order": {
                    "type": "MARKET",
                    "instrument": symbol,
                    "units": str(int(units)),
                    "timeInForce": "FOK",  # Fill or Kill
                    "positionFill": "DEFAULT"
                }
            }

            # Add stop loss
            if stop_loss:
                order_data["order"]["stopLossOnFill"] = {
                    "price": str(round(stop_loss, 5)),
                    "timeInForce": "GTC"
                }

            # Add take profit
            if take_profit:
                order_data["order"]["takeProfitOnFill"] = {
                    "price": str(round(take_profit, 5)),
                    "timeInForce": "GTC"
                }

            # Execute order
            request = OrderCreate(accountID=self.oanda.account_id, data=order_data)
            response = self.oanda.client.request(request)

            # Parse response
            fill_transaction = response.get('orderFillTransaction', {})

            return {
                'success': True,
                'order_id': fill_transaction.get('id'),
                'trade_id': fill_transaction.get('tradeOpened', {}).get('tradeID'),
                'fill_price': float(fill_transaction.get('price', 0)),
                'filled_units': int(fill_transaction.get('units', 0)),
                'timestamp': fill_transaction.get('time')
            }

        except Exception as e:
            logger.error(f"Order execution failed: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    def _simulate_execution(self, decision: Dict[str, Any]) -> Dict[str, Any]:
        """
        Simulate order execution (for testing)

        Args:
            decision: Trading decision

        Returns:
            Simulated execution result
        """
        import uuid

        simulated_order_id = str(uuid.uuid4())[:8]
        simulated_trade_id = str(uuid.uuid4())[:8]

        # Simulate slippage
        entry_price = decision.get('entry_price', 0)
        slippage = 0.0001  # 1 pip
        fill_price = entry_price + slippage if decision['direction'] == 'BUY' else entry_price - slippage

        result = {
            'success': True,
            'order_id': simulated_order_id,
            'trade_id': simulated_trade_id,
            'fill_price': fill_price,
            'filled_units': decision.get('position_size_units', 0),
            'timestamp': datetime.now().isoformat(),
            'simulated': True
        }

        logger.info(f"Simulated execution: {result}")

        return result

    def modify_order(
        self,
        trade_id: str,
        new_stop_loss: Optional[float] = None,
        new_take_profit: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Modify existing order/position

        Args:
            trade_id: Trade ID to modify
            new_stop_loss: New stop loss price
            new_take_profit: New take profit price

        Returns:
            Modification result
        """
        if not self.oanda:
            return {'success': False, 'error': 'OANDA client not available'}

        try:
            from oandapyV20.endpoints.trades import TradeCRCDO

            modifications = {}

            if new_stop_loss:
                modifications['stopLoss'] = {'price': str(round(new_stop_loss, 5))}

            if new_take_profit:
                modifications['takeProfit'] = {'price': str(round(new_take_profit, 5))}

            request = TradeCRCDO(
                accountID=self.oanda.account_id,
                tradeID=trade_id,
                data=modifications
            )

            response = self.oanda.client.request(request)

            logger.info(f"Modified trade {trade_id}")

            return {'success': True, 'trade_id': trade_id}

        except Exception as e:
            logger.error(f"Order modification failed: {str(e)}")
            return {'success': False, 'error': str(e)}

    def close_position(self, trade_id: str, units: Optional[int] = None) -> Dict[str, Any]:
        """
        Close position (full or partial)

        Args:
            trade_id: Trade ID to close
            units: Number of units to close (None = close all)

        Returns:
            Close result
        """
        if not self.oanda:
            return {'success': False, 'error': 'OANDA client not available'}

        try:
            from oandapyV20.endpoints.trades import TradeClose

            close_data = {}
            if units:
                close_data['units'] = str(units)

            request = TradeClose(accountID=self.oanda.account_id, tradeID=trade_id, data=close_data)
            response = self.oanda.client.request(request)

            # Parse P&L
            fill_transaction = response.get('orderFillTransaction', {})
            realized_pl = float(fill_transaction.get('pl', 0))

            logger.info(f"Closed trade {trade_id}: P&L ${realized_pl:.2f}")

            return {
                'success': True,
                'trade_id': trade_id,
                'realized_pl': realized_pl,
                'timestamp': fill_transaction.get('time')
            }

        except Exception as e:
            logger.error(f"Position close failed: {str(e)}")
            return {'success': False, 'error': str(e)}

    def get_open_positions(self) -> List[Dict[str, Any]]:
        """
        Get all open positions

        Returns:
            List of open positions
        """
        if not self.oanda:
            return []

        try:
            from oandapyV20.endpoints.positions import OpenPositions

            request = OpenPositions(accountID=self.oanda.account_id)
            response = self.oanda.client.request(request)

            positions = []

            for pos in response.get('positions', []):
                # Parse position data
                long_units = int(pos.get('long', {}).get('units', 0))
                short_units = int(pos.get('short', {}).get('units', 0))

                net_units = long_units + short_units

                if net_units != 0:
                    positions.append({
                        'symbol': pos.get('instrument'),
                        'units': net_units,
                        'direction': 'LONG' if net_units > 0 else 'SHORT',
                        'unrealized_pl': float(pos.get('unrealizedPL', 0))
                    })

            return positions

        except Exception as e:
            logger.error(f"Failed to get open positions: {str(e)}")
            return []

    def get_execution_statistics(self) -> Dict[str, Any]:
        """
        Get execution statistics

        Returns:
            Execution statistics
        """
        fill_rate = self.filled_count / self.total_orders if self.total_orders > 0 else 0

        return {
            'total_orders': self.total_orders,
            'filled_orders': self.filled_count,
            'rejected_orders': self.rejected_count,
            'fill_rate': fill_rate,
            'recent_filled': list(self.filled_orders.values())[-10:],
            'recent_rejected': list(self.rejected_orders.values())[-10:]
        }
