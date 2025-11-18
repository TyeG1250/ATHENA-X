"""
ATHENA-X QuestDB Client
Time-series database for market data
"""

import requests
import psycopg2
from typing import List, Dict, Any, Optional
from datetime import datetime
import pandas as pd
from loguru import logger


class QuestDBClient:
    """
    QuestDB client for storing and querying time-series data
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize QuestDB client

        Args:
            config: Database configuration
        """
        self.config = config
        self.host = config.get('host', 'localhost')
        self.http_port = config.get('http_port', 9000)
        self.pg_port = config.get('pg_port', 8812)
        self.influx_port = config.get('influx_port', 9009)

        self.http_url = f"http://{self.host}:{self.http_port}"
        self.pg_conn = None

        logger.info(f"Initialized QuestDB client: {self.http_url}")

    def _get_pg_connection(self):
        """Get PostgreSQL wire protocol connection"""
        if self.pg_conn is None or self.pg_conn.closed:
            self.pg_conn = psycopg2.connect(
                host=self.host,
                port=self.pg_port,
                user='admin',
                password='quest',
                database='qdb'
            )
        return self.pg_conn

    def execute_query(self, sql: str) -> pd.DataFrame:
        """
        Execute SQL query and return results as DataFrame

        Args:
            sql: SQL query

        Returns:
            Query results as DataFrame
        """
        try:
            response = requests.get(
                f"{self.http_url}/exec",
                params={'query': sql}
            )
            response.raise_for_status()

            data = response.json()

            if 'dataset' in data:
                columns = [col['name'] for col in data['columns']]
                return pd.DataFrame(data['dataset'], columns=columns)
            else:
                return pd.DataFrame()

        except Exception as e:
            logger.error(f"Query execution failed: {str(e)}")
            raise

    def create_table(self, table_name: str, schema: Dict[str, str], partitioned_by: str = 'DAY'):
        """
        Create time-series table

        Args:
            table_name: Table name
            schema: Column definitions {column_name: data_type}
            partitioned_by: Partition strategy (NONE, DAY, MONTH, YEAR)

        Example:
            create_table('prices', {
                'timestamp': 'TIMESTAMP',
                'symbol': 'SYMBOL',
                'price': 'DOUBLE',
                'volume': 'LONG'
            })
        """
        columns = ', '.join([f"{name} {dtype}" for name, dtype in schema.items()])

        sql = f"CREATE TABLE IF NOT EXISTS {table_name} ({columns})"

        if 'timestamp' in schema:
            sql += f", timestamp(timestamp) PARTITION BY {partitioned_by}"

        try:
            self.execute_query(sql)
            logger.info(f"Table '{table_name}' created successfully")
        except Exception as e:
            logger.error(f"Failed to create table '{table_name}': {str(e)}")
            raise

    def insert_dataframe(self, table_name: str, df: pd.DataFrame):
        """
        Insert DataFrame into table using PostgreSQL protocol

        Args:
            table_name: Target table
            df: Data to insert
        """
        if df.empty:
            return

        try:
            conn = self._get_pg_connection()
            cursor = conn.cursor()

            # Prepare column list
            columns = df.columns.tolist()
            placeholders = ', '.join(['%s'] * len(columns))
            column_list = ', '.join(columns)

            insert_sql = f"INSERT INTO {table_name} ({column_list}) VALUES ({placeholders})"

            # Insert rows
            for _, row in df.iterrows():
                cursor.execute(insert_sql, tuple(row))

            conn.commit()
            logger.debug(f"Inserted {len(df)} rows into {table_name}")

        except Exception as e:
            logger.error(f"Failed to insert data into {table_name}: {str(e)}")
            if self.pg_conn:
                self.pg_conn.rollback()
            raise

    def insert_tick(
        self,
        table_name: str,
        symbol: str,
        timestamp: datetime,
        price: float,
        volume: float = 0,
        **kwargs
    ):
        """
        Insert single tick data using InfluxDB Line Protocol (fastest)

        Args:
            table_name: Target table
            symbol: Trading symbol
            timestamp: Tick timestamp
            price: Price
            volume: Volume
            **kwargs: Additional fields
        """
        # Convert to InfluxDB Line Protocol format
        # Format: table_name,symbol=XXX price=1.234,volume=100 timestamp

        fields = [f"price={price}", f"volume={volume}"]
        for key, value in kwargs.items():
            fields.append(f"{key}={value}")

        timestamp_ns = int(timestamp.timestamp() * 1_000_000_000)
        line = f"{table_name},symbol={symbol} {','.join(fields)} {timestamp_ns}"

        try:
            response = requests.post(
                f"http://{self.host}:{self.influx_port}/write",
                data=line
            )
            response.raise_for_status()

        except Exception as e:
            logger.error(f"Failed to insert tick: {str(e)}")
            raise

    def get_latest_price(self, table_name: str, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get latest price for a symbol

        Args:
            table_name: Table name
            symbol: Trading symbol

        Returns:
            Latest price data
        """
        sql = f"""
            SELECT * FROM {table_name}
            WHERE symbol = '{symbol}'
            ORDER BY timestamp DESC
            LIMIT 1
        """

        try:
            df = self.execute_query(sql)
            if not df.empty:
                return df.iloc[0].to_dict()
            return None

        except Exception as e:
            logger.error(f"Failed to get latest price: {str(e)}")
            return None

    def get_ohlc(
        self,
        table_name: str,
        symbol: str,
        interval: str = '15m',
        limit: int = 100
    ) -> pd.DataFrame:
        """
        Get OHLC candlestick data

        Args:
            table_name: Table name
            symbol: Trading symbol
            interval: Time interval (1m, 5m, 15m, 1h, 1d)
            limit: Number of candles

        Returns:
            OHLC DataFrame
        """
        # Convert interval to QuestDB SAMPLE BY syntax
        interval_map = {
            '1m': '1m',
            '5m': '5m',
            '15m': '15m',
            '1h': '1h',
            '4h': '4h',
            '1d': '1d'
        }

        sample_interval = interval_map.get(interval, '15m')

        sql = f"""
            SELECT
                timestamp,
                first(price) as open,
                max(price) as high,
                min(price) as low,
                last(price) as close,
                sum(volume) as volume
            FROM {table_name}
            WHERE symbol = '{symbol}'
            SAMPLE BY {sample_interval}
            LIMIT {limit}
        """

        try:
            df = self.execute_query(sql)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df.set_index('timestamp', inplace=True)
            return df

        except Exception as e:
            logger.error(f"Failed to get OHLC data: {str(e)}")
            return pd.DataFrame()

    def get_historical_data(
        self,
        table_name: str,
        symbol: str,
        start_time: datetime,
        end_time: datetime
    ) -> pd.DataFrame:
        """
        Get historical data for a time range

        Args:
            table_name: Table name
            symbol: Trading symbol
            start_time: Start timestamp
            end_time: End timestamp

        Returns:
            Historical data DataFrame
        """
        sql = f"""
            SELECT * FROM {table_name}
            WHERE symbol = '{symbol}'
            AND timestamp >= '{start_time.isoformat()}'
            AND timestamp <= '{end_time.isoformat()}'
            ORDER BY timestamp
        """

        try:
            df = self.execute_query(sql)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            return df

        except Exception as e:
            logger.error(f"Failed to get historical data: {str(e)}")
            return pd.DataFrame()

    def cleanup_old_data(self, table_name: str, days_to_keep: int = 90):
        """
        Delete data older than specified days

        Args:
            table_name: Table name
            days_to_keep: Number of days to retain
        """
        sql = f"""
            DELETE FROM {table_name}
            WHERE timestamp < dateadd('d', -{days_to_keep}, now())
        """

        try:
            self.execute_query(sql)
            logger.info(f"Cleaned up data older than {days_to_keep} days from {table_name}")

        except Exception as e:
            logger.error(f"Failed to cleanup old data: {str(e)}")
            raise

    def close(self):
        """Close connections"""
        if self.pg_conn and not self.pg_conn.closed:
            self.pg_conn.close()
            logger.info("QuestDB connection closed")
