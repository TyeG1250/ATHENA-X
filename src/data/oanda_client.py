"""
ATHENA-X OANDA API Client
Market data and order execution via OANDA
"""

import oandapyV20
from oandapyV20 import API
from oandapyV20.endpoints.pricing import PricingStream, PricingInfo
from oandapyV20.endpoints.instruments import InstrumentsCandles
from oandapyV20.endpoints.accounts import AccountSummary, AccountInstruments
from oandapyV20.endpoints.orders import OrderCreate, OrderList
from oandapyV20.endpoints.trades import TradesList, TradeDetails, TradeClose
from oandapyV20.endpoints.positions import PositionsList, PositionDetails

from typing import Dict, Any, List, Optional, Callable
from datetime import datetime
import pandas as pd
from loguru import logger
import time


class OANDAClient:
    """
    OANDA API client for ATHENA-X
    """

    def __init__(self, api_key: str, account_id: str, environment: str = "practice"):
        """
        Initialize OANDA client

        Args:
            api_key: OANDA API key
            account_id: OANDA account ID
            environment: 'practice' or 'live'
        """
        self.api_key = api_key
        self.account_id = account_id
        self.environment = environment

        # Initialize API client
        if environment == "live":
            self.client = API(access_token=api_key, environment="live")
            logger.warning("🔴 OANDA Live Environment - Real money trading!")
        else:
            self.client = API(access_token=api_key, environment="practice")
            logger.info("🟢 OANDA Practice Environment")

        # Test connection
        self._test_connection()

    def _test_connection(self):
        """Test API connection"""
        try:
            r = AccountSummary(accountID=self.account_id)
            self.client.request(r)
            logger.info(f"Connected to OANDA - Account: {self.account_id}")

        except Exception as e:
            logger.error(f"OANDA connection failed: {str(e)}")
            raise

    # Market Data Methods

    def get_candles(
        self,
        instrument: str,
        granularity: str = "M15",
        count: int = 500,
        from_time: Optional[datetime] = None,
        to_time: Optional[datetime] = None
    ) -> pd.DataFrame:
        """
        Get historical candlestick data

        Args:
            instrument: Instrument name (e.g., "EUR_USD")
            granularity: Candle size (M1, M5, M15, H1, H4, D)
            count: Number of candles
            from_time: Start time
            to_time: End time

        Returns:
            DataFrame with OHLCV data
        """
        params = {
            "granularity": granularity,
            "count": min(count, 5000)  # OANDA max
        }

        if from_time:
            params["from"] = from_time.isoformat() + "Z"

        if to_time:
            params["to"] = to_time.isoformat() + "Z"

        try:
            r = InstrumentsCandles(instrument=instrument, params=params)
            response = self.client.request(r)

            candles = response.get('candles', [])

            if not candles:
                logger.warning(f"No candles returned for {instrument}")
                return pd.DataFrame()

            # Parse candles
            data = []
            for candle in candles:
                if candle['complete']:
                    data.append({
                        'timestamp': pd.to_datetime(candle['time']),
                        'open': float(candle['mid']['o']),
                        'high': float(candle['mid']['h']),
                        'low': float(candle['mid']['l']),
                        'close': float(candle['mid']['c']),
                        'volume': int(candle['volume'])
                    })

            df = pd.DataFrame(data)
            df.set_index('timestamp', inplace=True)

            logger.debug(f"Fetched {len(df)} candles for {instrument} ({granularity})")
            return df

        except Exception as e:
            logger.error(f"Failed to get candles for {instrument}: {str(e)}")
            return pd.DataFrame()

    def get_current_price(self, instruments: List[str]) -> Dict[str, Any]:
        """
        Get current prices for instruments

        Args:
            instruments: List of instrument names

        Returns:
            Dictionary of current prices
        """
        params = {"instruments": ",".join(instruments)}

        try:
            r = PricingInfo(accountID=self.account_id, params=params)
            response = self.client.request(r)

            prices = {}
            for price in response.get('prices', []):
                instrument = price['instrument']
                prices[instrument] = {
                    'bid': float(price['bids'][0]['price']),
                    'ask': float(price['asks'][0]['price']),
                    'spread': float(price['asks'][0]['price']) - float(price['bids'][0]['price']),
                    'timestamp': pd.to_datetime(price['time'])
                }

            return prices

        except Exception as e:
            logger.error(f"Failed to get prices: {str(e)}")
            return {}

    def stream_prices(
        self,
        instruments: List[str],
        callback: Callable[[Dict[str, Any]], None],
        stop_event: Optional[Any] = None
    ):
        """
        Stream real-time prices

        Args:
            instruments: List of instruments to stream
            callback: Function to call with each price update
            stop_event: Event to signal stop (e.g., threading.Event)
        """
        params = {"instruments": ",".join(instruments)}

        try:
            r = PricingStream(accountID=self.account_id, params=params)

            logger.info(f"Starting price stream for: {', '.join(instruments)}")

            for tick in self.client.request(r):
                if stop_event and stop_event.is_set():
                    logger.info("Price stream stopped")
                    break

                if tick['type'] == 'PRICE':
                    price_data = {
                        'instrument': tick['instrument'],
                        'bid': float(tick['bids'][0]['price']),
                        'ask': float(tick['asks'][0]['price']),
                        'spread': float(tick['asks'][0]['price']) - float(tick['bids'][0]['price']),
                        'timestamp': pd.to_datetime(tick['time'])
                    }

                    callback(price_data)

        except Exception as e:
            logger.error(f"Price stream error: {str(e)}")

    # Account Methods

    def get_account_summary(self) -> Dict[str, Any]:
        """Get account summary"""
        try:
            r = AccountSummary(accountID=self.account_id)
            response = self.client.request(r)

            account = response.get('account', {})

            return {
                'balance': float(account.get('balance', 0)),
                'nav': float(account.get('NAV', 0)),
                'unrealized_pl': float(account.get('unrealizedPL', 0)),
                'realized_pl': float(account.get('pl', 0)),
                'margin_used': float(account.get('marginUsed', 0)),
                'margin_available': float(account.get('marginAvailable', 0)),
                'open_trade_count': int(account.get('openTradeCount', 0)),
                'open_position_count': int(account.get('openPositionCount', 0)),
                'currency': account.get('currency', 'USD')
            }

        except Exception as e:
            logger.error(f"Failed to get account summary: {str(e)}")
            return {}

    def get_available_instruments(self) -> List[str]:
        """Get list of tradeable instruments"""
        try:
            r = AccountInstruments(accountID=self.account_id)
            response = self.client.request(r)

            instruments = [instr['name'] for instr in response.get('instruments', [])]

            logger.info(f"Found {len(instruments)} available instruments")
            return instruments

        except Exception as e:
            logger.error(f"Failed to get instruments: {str(e)}")
            return []

    # Trading Methods

    def create_market_order(
        self,
        instrument: str,
        units: int,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Create market order

        Args:
            instrument: Instrument to trade
            units: Number of units (positive = buy, negative = sell)
            stop_loss: Stop loss price
            take_profit: Take profit price

        Returns:
            Order response
        """
        order_data = {
            "order": {
                "type": "MARKET",
                "instrument": instrument,
                "units": str(units),
                "timeInForce": "FOK",  # Fill or Kill
                "positionFill": "DEFAULT"
            }
        }

        # Add stop loss
        if stop_loss:
            order_data["order"]["stopLossOnFill"] = {
                "price": str(stop_loss)
            }

        # Add take profit
        if take_profit:
            order_data["order"]["takeProfitOnFill"] = {
                "price": str(take_profit)
            }

        try:
            r = OrderCreate(accountID=self.account_id, data=order_data)
            response = self.client.request(r)

            logger.info(
                f"Market order created: {instrument} {units} units"
            )

            return {
                'success': True,
                'order_id': response.get('orderFillTransaction', {}).get('id'),
                'trade_id': response.get('orderFillTransaction', {}).get('tradeOpened', {}).get('tradeID'),
                'fill_price': float(response.get('orderFillTransaction', {}).get('price', 0)),
                'response': response
            }

        except Exception as e:
            logger.error(f"Failed to create order: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    def close_position(self, instrument: str, units: Optional[str] = "ALL") -> Dict[str, Any]:
        """
        Close position

        Args:
            instrument: Instrument to close
            units: Number of units to close ("ALL" or specific number)

        Returns:
            Close response
        """
        # First, get current position
        try:
            r = PositionDetails(accountID=self.account_id, instrument=instrument)
            position = self.client.request(r)

            long_units = position['position']['long']['units']
            short_units = position['position']['short']['units']

            # Determine which side to close
            if long_units != "0":
                order_units = f"-{long_units}" if units == "ALL" else f"-{units}"
            elif short_units != "0":
                order_units = short_units if units == "ALL" else units
            else:
                return {'success': False, 'error': 'No position to close'}

            # Create closing market order
            return self.create_market_order(instrument, int(order_units))

        except Exception as e:
            logger.error(f"Failed to close position: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    def get_open_positions(self) -> List[Dict[str, Any]]:
        """Get all open positions"""
        try:
            r = PositionsList(accountID=self.account_id)
            response = self.client.request(r)

            positions = []
            for pos in response.get('positions', []):
                if pos['long']['units'] != "0" or pos['short']['units'] != "0":
                    positions.append({
                        'instrument': pos['instrument'],
                        'long_units': float(pos['long']['units']),
                        'short_units': float(pos['short']['units']),
                        'unrealized_pl': float(pos['unrealizedPL'])
                    })

            return positions

        except Exception as e:
            logger.error(f"Failed to get positions: {str(e)}")
            return []

    def get_open_trades(self) -> List[Dict[str, Any]]:
        """Get all open trades"""
        try:
            r = TradesList(accountID=self.account_id)
            response = self.client.request(r)

            trades = []
            for trade in response.get('trades', []):
                trades.append({
                    'id': trade['id'],
                    'instrument': trade['instrument'],
                    'units': float(trade['currentUnits']),
                    'price': float(trade['price']),
                    'unrealized_pl': float(trade['unrealizedPL']),
                    'open_time': pd.to_datetime(trade['openTime'])
                })

            return trades

        except Exception as e:
            logger.error(f"Failed to get trades: {str(e)}")
            return []

    def close_trade(self, trade_id: str) -> Dict[str, Any]:
        """Close specific trade"""
        try:
            r = TradeClose(accountID=self.account_id, tradeID=trade_id)
            response = self.client.request(r)

            logger.info(f"Trade closed: {trade_id}")

            return {
                'success': True,
                'realized_pl': float(response.get('orderFillTransaction', {}).get('pl', 0)),
                'response': response
            }

        except Exception as e:
            logger.error(f"Failed to close trade: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    def close_all_positions(self):
        """Close all open positions"""
        positions = self.get_open_positions()

        for position in positions:
            instrument = position['instrument']
            logger.info(f"Closing position: {instrument}")
            self.close_position(instrument)

    # Utility Methods

    def calculate_position_size(
        self,
        risk_amount: float,
        entry_price: float,
        stop_loss: float,
        pip_value: float = 10.0
    ) -> int:
        """
        Calculate position size based on risk

        Args:
            risk_amount: Amount to risk
            entry_price: Entry price
            stop_loss: Stop loss price
            pip_value: Value per pip (default 10 for standard lot)

        Returns:
            Position size in units
        """
        stop_distance_pips = abs(entry_price - stop_loss) * 10000

        if stop_distance_pips == 0:
            return 0

        units = int(risk_amount / (stop_distance_pips * pip_value))

        return units
