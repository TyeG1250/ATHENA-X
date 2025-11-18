"""
ATHENA-X PostgreSQL Client
Metadata and configuration storage
"""

import psycopg2
import psycopg2.extras
from typing import Dict, Any, List, Optional
from datetime import datetime
from loguru import logger


class PostgreSQLClient:
    """
    PostgreSQL client for metadata storage
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize PostgreSQL client

        Args:
            config: Database configuration
        """
        self.config = config
        self.host = config.get('host', 'localhost')
        self.port = config.get('port', 5432)
        self.database = config.get('database', 'athena_db')
        self.user = config.get('user', 'athena_user')
        self.password = config.get('password')

        self.conn = None
        self._connect()

        # Initialize schema
        self._init_schema()

    def _connect(self):
        """Establish database connection"""
        try:
            self.conn = psycopg2.connect(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password
            )
            logger.info(f"Connected to PostgreSQL at {self.host}:{self.port}/{self.database}")

        except Exception as e:
            logger.error(f"Failed to connect to PostgreSQL: {str(e)}")
            raise

    def _init_schema(self):
        """Initialize database schema"""
        schema_sql = """
        -- Trades table
        CREATE TABLE IF NOT EXISTS trades (
            id SERIAL PRIMARY KEY,
            timestamp TIMESTAMP NOT NULL,
            symbol VARCHAR(20) NOT NULL,
            direction VARCHAR(10) NOT NULL,
            entry_price DECIMAL(20, 8) NOT NULL,
            exit_price DECIMAL(20, 8),
            position_size DECIMAL(20, 8) NOT NULL,
            stop_loss DECIMAL(20, 8),
            take_profit DECIMAL(20, 8),
            profit_loss DECIMAL(20, 8),
            profit_pct DECIMAL(10, 4),
            status VARCHAR(20) NOT NULL,
            strategy VARCHAR(50),
            entry_reason TEXT,
            exit_reason TEXT,
            duration_seconds INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_trades_timestamp ON trades(timestamp);
        CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trades(symbol);
        CREATE INDEX IF NOT EXISTS idx_trades_status ON trades(status);

        -- Agent performance table
        CREATE TABLE IF NOT EXISTS agent_performance (
            id SERIAL PRIMARY KEY,
            agent_name VARCHAR(50) NOT NULL,
            timestamp TIMESTAMP NOT NULL,
            trade_id INTEGER REFERENCES trades(id),
            vote VARCHAR(20) NOT NULL,
            confidence DECIMAL(5, 4) NOT NULL,
            correct BOOLEAN,
            sharpe_ratio DECIMAL(10, 4),
            win_rate DECIMAL(5, 4),
            profit_factor DECIMAL(10, 4),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_agent_perf_agent ON agent_performance(agent_name);
        CREATE INDEX IF NOT EXISTS idx_agent_perf_timestamp ON agent_performance(timestamp);

        -- Strategy performance table
        CREATE TABLE IF NOT EXISTS strategy_performance (
            id SERIAL PRIMARY KEY,
            strategy_name VARCHAR(50) NOT NULL,
            period VARCHAR(20) NOT NULL,
            total_trades INTEGER NOT NULL,
            winning_trades INTEGER NOT NULL,
            losing_trades INTEGER NOT NULL,
            win_rate DECIMAL(5, 4) NOT NULL,
            total_profit DECIMAL(20, 8) NOT NULL,
            sharpe_ratio DECIMAL(10, 4),
            max_drawdown DECIMAL(5, 4),
            profit_factor DECIMAL(10, 4),
            avg_trade_duration INTEGER,
            timestamp TIMESTAMP NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_strategy_perf_name ON strategy_performance(strategy_name);
        CREATE INDEX IF NOT EXISTS idx_strategy_perf_timestamp ON strategy_performance(timestamp);

        -- System events table
        CREATE TABLE IF NOT EXISTS system_events (
            id SERIAL PRIMARY KEY,
            timestamp TIMESTAMP NOT NULL,
            event_type VARCHAR(50) NOT NULL,
            severity VARCHAR(20) NOT NULL,
            component VARCHAR(50),
            message TEXT NOT NULL,
            data JSONB,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_events_timestamp ON system_events(timestamp);
        CREATE INDEX IF NOT EXISTS idx_events_type ON system_events(event_type);
        CREATE INDEX IF NOT EXISTS idx_events_severity ON system_events(severity);

        -- Configuration table
        CREATE TABLE IF NOT EXISTS configuration (
            key VARCHAR(100) PRIMARY KEY,
            value JSONB NOT NULL,
            description TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """

        try:
            cursor = self.conn.cursor()
            cursor.execute(schema_sql)
            self.conn.commit()
            logger.info("Database schema initialized")

        except Exception as e:
            logger.error(f"Failed to initialize schema: {str(e)}")
            self.conn.rollback()
            raise

    def execute_query(self, sql: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        """
        Execute SELECT query

        Args:
            sql: SQL query
            params: Query parameters

        Returns:
            List of result dictionaries
        """
        try:
            cursor = self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute(sql, params)
            results = cursor.fetchall()
            return [dict(row) for row in results]

        except Exception as e:
            logger.error(f"Query execution failed: {str(e)}")
            raise

    def execute_update(self, sql: str, params: Optional[tuple] = None) -> int:
        """
        Execute INSERT/UPDATE/DELETE query

        Args:
            sql: SQL query
            params: Query parameters

        Returns:
            Number of rows affected
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute(sql, params)
            self.conn.commit()
            return cursor.rowcount

        except Exception as e:
            logger.error(f"Update execution failed: {str(e)}")
            self.conn.rollback()
            raise

    # Trade methods

    def insert_trade(self, trade_data: Dict[str, Any]) -> int:
        """
        Insert new trade record

        Args:
            trade_data: Trade details

        Returns:
            Trade ID
        """
        sql = """
        INSERT INTO trades (
            timestamp, symbol, direction, entry_price, position_size,
            stop_loss, take_profit, status, strategy, entry_reason
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
        """

        params = (
            trade_data.get('timestamp', datetime.now()),
            trade_data['symbol'],
            trade_data['direction'],
            trade_data['entry_price'],
            trade_data['position_size'],
            trade_data.get('stop_loss'),
            trade_data.get('take_profit'),
            trade_data.get('status', 'OPEN'),
            trade_data.get('strategy'),
            trade_data.get('entry_reason')
        )

        try:
            cursor = self.conn.cursor()
            cursor.execute(sql, params)
            trade_id = cursor.fetchone()[0]
            self.conn.commit()

            logger.info(f"Trade inserted: ID {trade_id}")
            return trade_id

        except Exception as e:
            logger.error(f"Failed to insert trade: {str(e)}")
            self.conn.rollback()
            raise

    def update_trade(self, trade_id: int, updates: Dict[str, Any]):
        """
        Update trade record

        Args:
            trade_id: Trade ID
            updates: Fields to update
        """
        set_clause = ', '.join([f"{key} = %s" for key in updates.keys()])
        sql = f"UPDATE trades SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE id = %s"

        params = tuple(updates.values()) + (trade_id,)

        try:
            self.execute_update(sql, params)
            logger.info(f"Trade updated: ID {trade_id}")

        except Exception as e:
            logger.error(f"Failed to update trade: {str(e)}")
            raise

    def close_trade(
        self,
        trade_id: int,
        exit_price: float,
        profit_loss: float,
        exit_reason: str = ""
    ):
        """Close a trade"""
        updates = {
            'exit_price': exit_price,
            'profit_loss': profit_loss,
            'status': 'CLOSED',
            'exit_reason': exit_reason
        }
        self.update_trade(trade_id, updates)

    def get_open_trades(self) -> List[Dict[str, Any]]:
        """Get all open trades"""
        sql = "SELECT * FROM trades WHERE status = 'OPEN' ORDER BY timestamp DESC"
        return self.execute_query(sql)

    def get_trade_history(
        self,
        symbol: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get trade history

        Args:
            symbol: Filter by symbol (None = all)
            limit: Maximum number of records

        Returns:
            Trade history
        """
        if symbol:
            sql = "SELECT * FROM trades WHERE symbol = %s ORDER BY timestamp DESC LIMIT %s"
            params = (symbol, limit)
        else:
            sql = "SELECT * FROM trades ORDER BY timestamp DESC LIMIT %s"
            params = (limit,)

        return self.execute_query(sql, params)

    # Agent performance methods

    def record_agent_decision(
        self,
        agent_name: str,
        trade_id: int,
        vote: str,
        confidence: float
    ):
        """Record agent decision"""
        sql = """
        INSERT INTO agent_performance (agent_name, timestamp, trade_id, vote, confidence)
        VALUES (%s, %s, %s, %s, %s)
        """

        params = (agent_name, datetime.now(), trade_id, vote, confidence)
        self.execute_update(sql, params)

    def update_agent_performance(
        self,
        agent_name: str,
        metrics: Dict[str, float]
    ):
        """Update agent performance metrics"""
        # Implementation depends on how you track agent performance
        pass

    # System events

    def log_event(
        self,
        event_type: str,
        severity: str,
        message: str,
        component: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None
    ):
        """
        Log system event

        Args:
            event_type: Event type
            severity: Event severity
            message: Event message
            component: System component
            data: Additional data
        """
        import json

        sql = """
        INSERT INTO system_events (timestamp, event_type, severity, component, message, data)
        VALUES (%s, %s, %s, %s, %s, %s)
        """

        params = (
            datetime.now(),
            event_type,
            severity,
            component,
            message,
            json.dumps(data) if data else None
        )

        try:
            self.execute_update(sql, params)

        except Exception as e:
            logger.error(f"Failed to log event: {str(e)}")

    # Statistics

    def get_performance_stats(self, period: str = 'all') -> Dict[str, Any]:
        """
        Get performance statistics

        Args:
            period: Time period (all, today, week, month)

        Returns:
            Performance statistics
        """
        where_clause = ""
        if period == 'today':
            where_clause = "WHERE DATE(timestamp) = CURRENT_DATE"
        elif period == 'week':
            where_clause = "WHERE timestamp >= CURRENT_DATE - INTERVAL '7 days'"
        elif period == 'month':
            where_clause = "WHERE timestamp >= CURRENT_DATE - INTERVAL '30 days'"

        sql = f"""
        SELECT
            COUNT(*) as total_trades,
            COUNT(*) FILTER (WHERE profit_loss > 0) as winning_trades,
            COUNT(*) FILTER (WHERE profit_loss < 0) as losing_trades,
            COALESCE(SUM(profit_loss), 0) as total_profit,
            COALESCE(AVG(profit_loss), 0) as avg_profit,
            COALESCE(MAX(profit_loss), 0) as max_profit,
            COALESCE(MIN(profit_loss), 0) as max_loss
        FROM trades
        WHERE status = 'CLOSED'
        {where_clause}
        """

        results = self.execute_query(sql)
        return results[0] if results else {}

    def close(self):
        """Close database connection"""
        if self.conn and not self.conn.closed:
            self.conn.close()
            logger.info("PostgreSQL connection closed")
