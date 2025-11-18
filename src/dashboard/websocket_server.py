#!/usr/bin/env python3
"""
ATHENA-X Real-Time Dashboard WebSocket Server
Streams trading state, agent decisions, market data, and KPIs
"""

import asyncio
import json
from typing import Dict, Any, List, Set
from datetime import datetime
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from loguru import logger
import psycopg2
from contextlib import asynccontextmanager
import os


class DashboardBroadcaster:
    """Manages WebSocket connections and broadcasts trading state"""

    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self.questdb_host = os.getenv('QUESTDB_HOST', 'questdb')
        self.questdb_port = int(os.getenv('QUESTDB_PG_PORT', 8812))
        self.redis_host = os.getenv('REDIS_HOST', 'redis')
        self.redis_port = int(os.getenv('REDIS_PORT', 6379))

    async def connect(self, websocket: WebSocket):
        """Register new WebSocket connection"""
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(f"Dashboard client connected. Total: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        """Remove WebSocket connection"""
        self.active_connections.remove(websocket)
        logger.info(f"Dashboard client disconnected. Total: {len(self.active_connections)}")

    async def broadcast(self, message: Dict[str, Any]):
        """Broadcast message to all connected clients"""
        if not self.active_connections:
            return

        # Convert to JSON
        json_message = json.dumps(message, default=str)

        # Send to all clients
        disconnected = set()
        for connection in self.active_connections:
            try:
                await connection.send_text(json_message)
            except Exception as e:
                logger.error(f"Failed to send to client: {e}")
                disconnected.add(connection)

        # Clean up disconnected clients
        self.active_connections -= disconnected

    def get_questdb_data(self, symbol: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Fetch recent candles from QuestDB"""
        try:
            conn = psycopg2.connect(
                host=self.questdb_host,
                port=self.questdb_port,
                user='admin',
                password='quest',
                database='qdb'
            )
            cursor = conn.cursor()

            cursor.execute(f"""
                SELECT timestamp, open, high, low, close, volume
                FROM market_data
                WHERE symbol = %s
                ORDER BY timestamp DESC
                LIMIT %s
            """, (symbol, limit))

            rows = cursor.fetchall()
            cursor.close()
            conn.close()

            return [{
                'time': row[0].timestamp(),
                'open': float(row[1]),
                'high': float(row[2]),
                'low': float(row[3]),
                'close': float(row[4]),
                'volume': float(row[5])
            } for row in reversed(rows)]

        except Exception as e:
            logger.error(f"QuestDB query failed: {e}")
            return []


# Global broadcaster instance
broadcaster = DashboardBroadcaster()


# FastAPI lifecycle management
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    logger.info("🚀 Dashboard WebSocket server starting...")

    # Start background task to broadcast updates
    task = asyncio.create_task(broadcast_loop())

    yield

    # Shutdown
    logger.info("🛑 Dashboard WebSocket server shutting down...")
    task.cancel()


# Create FastAPI app
app = FastAPI(title="ATHENA-X Dashboard API", lifespan=lifespan)

# CORS for React dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time dashboard updates"""
    await broadcaster.connect(websocket)

    try:
        # Send initial state
        initial_state = get_current_state()
        await websocket.send_json(initial_state)

        # Keep connection alive and handle client messages
        while True:
            data = await websocket.receive_json()

            # Handle client requests
            if data.get('type') == 'subscribe_symbol':
                symbol = data.get('symbol')
                candles = broadcaster.get_questdb_data(symbol)
                await websocket.send_json({
                    'type': 'historical_data',
                    'symbol': symbol,
                    'candles': candles
                })

    except WebSocketDisconnect:
        broadcaster.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        broadcaster.disconnect(websocket)


@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "connected_clients": len(broadcaster.active_connections),
        "timestamp": datetime.now().isoformat()
    }


@app.get("/api/symbols/{symbol}/history")
async def get_symbol_history(symbol: str, limit: int = 100):
    """Get historical data for a symbol"""
    candles = broadcaster.get_questdb_data(symbol, limit)
    return {
        "symbol": symbol,
        "candles": candles,
        "count": len(candles)
    }


def get_current_state() -> Dict[str, Any]:
    """
    Get current trading state
    In production, this would read from Redis/shared memory
    """
    return {
        'type': 'state_update',
        'timestamp': datetime.now().isoformat(),
        'portfolio': {
            'balance': 10000.00,
            'equity': 10250.50,
            'margin_used': 500.00,
            'margin_available': 9750.50,
            'pnl_today': 250.50,
            'pnl_percent': 2.51
        },
        'positions': [
            {
                'symbol': 'EUR_USD',
                'side': 'long',
                'units': 10000,
                'entry_price': 1.0850,
                'current_price': 1.0875,
                'pnl': 25.00,
                'pnl_percent': 0.23
            }
        ],
        'agents': {
            'technical': {
                'vote': 'BUY',
                'confidence': 0.75,
                'signals': ['EMA_CROSS', 'RSI_OVERSOLD']
            },
            'sentiment': {
                'vote': 'NEUTRAL',
                'confidence': 0.60,
                'score': 0.05
            },
            'risk': {
                'vote': 'HOLD',
                'confidence': 0.80,
                'exposure': 0.05
            }
        },
        'system': {
            'status': 'RUNNING',
            'uptime': 3600,
            'loop_count': 60,
            'last_update': datetime.now().isoformat()
        }
    }


async def broadcast_loop():
    """Background task to broadcast updates every second"""
    while True:
        try:
            state = get_current_state()
            await broadcaster.broadcast(state)
            await asyncio.sleep(1)  # Update every second
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Broadcast loop error: {e}")
            await asyncio.sleep(5)


if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("  ATHENA-X Dashboard WebSocket Server")
    logger.info("=" * 60)
    logger.info("  WebSocket: ws://localhost:8765/ws")
    logger.info("  API:       http://localhost:8765/api")
    logger.info("=" * 60)

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8765,
        log_level="info"
    )
