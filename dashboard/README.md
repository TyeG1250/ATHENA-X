# ATHENA-X OmniView Dashboard

🚀 **Real-Time Trading Command Center**

A Bloomberg Terminal-killer dashboard for ATHENA-X institutional trading system.

## Features

- **Real-Time WebSocket Data** - Live trading state updates
- **TradingView Charts** - Lightweight, GPU-accelerated candlestick charts
- **Agent Consensus Visualization** - See what your AI agents are thinking
- **Portfolio Tracking** - P&L, positions, margin in real-time
- **System Health Monitoring** - CPU, GPU, memory, data pipeline status
- **Order Flow Analysis** - Volume profile and bid/ask imbalances
- **Black & Gold Theme** - Cyberpunk war room aesthetic

## Quick Start

### 1. Start WebSocket Server (Backend)

```bash
cd /home/user/ATHENA-X
python src/dashboard/websocket_server.py
```

Server will start on `http://localhost:8765`

### 2. Start React Dashboard (Frontend)

```bash
cd dashboard
npm install
npm run dev
```

Dashboard will be available at `http://localhost:3000`

## Architecture

```
┌──────────────────┐
│  React Dashboard │  ← User Interface (Port 3000)
│   (Vite + React) │
└────────┬─────────┘
         │ WebSocket
         ↓
┌──────────────────┐
│ FastAPI WS Server│  ← Real-time Data Streaming (Port 8765)
│   (Python)       │
└────────┬─────────┘
         │
    ┌────┴────┬────────┬─────────┐
    ↓         ↓        ↓         ↓
┌────────┐ ┌─────┐ ┌───────┐ ┌────────┐
│QuestDB │ │Redis│ │ OANDA │ │ ATHENA │
│        │ │     │ │  API  │ │   AI   │
└────────┘ └─────┘ └───────┘ └────────┘
```

## Development

### Install Dependencies

```bash
# Frontend
cd dashboard
npm install

# Backend (if not already installed)
cd ..
pip install -r requirements.txt
```

### Run in Development Mode

**Terminal 1 - Backend:**
```bash
python src/dashboard/websocket_server.py
```

**Terminal 2 - Frontend:**
```bash
cd dashboard
npm run dev
```

### Build for Production

```bash
cd dashboard
npm run build
```

Built files will be in `dashboard/dist/`

## Environment Variables

The WebSocket server reads from environment variables:

```bash
QUESTDB_HOST=questdb
QUESTDB_PG_PORT=8812
REDIS_HOST=redis
REDIS_PORT=6379
```

## Components

### Main Layout
- **Header** - System status, connection indicator, time
- **Left Sidebar** - Portfolio, positions, agent panel
- **Center** - Main trading chart, order flow
- **Right Sidebar** - System health, QuestDB, Redis, data pipeline

### Key Components
- `TradingChart.jsx` - TradingView Lightweight Charts integration
- `AgentPanel.jsx` - Multi-agent consensus visualization
- `PortfolioPanel.jsx` - Real-time P&L and margin tracking
- `SystemHealth.jsx` - Hardware telemetry (CPU, GPU, memory)
- `OrderFlow.jsx` - Volume profile and bid/ask analysis
- `QuestDBMonitor.jsx` - Database metrics and partition info

## WebSocket Message Format

### State Update (Server → Client)
```json
{
  "type": "state_update",
  "timestamp": "2025-11-18T20:00:00Z",
  "portfolio": {
    "balance": 10000.00,
    "equity": 10250.50,
    "pnl_today": 250.50,
    "pnl_percent": 2.51
  },
  "positions": [...],
  "agents": {
    "technical": { "vote": "BUY", "confidence": 0.75 },
    "sentiment": { "vote": "NEUTRAL", "confidence": 0.60 },
    "risk": { "vote": "HOLD", "confidence": 0.80 }
  },
  "system": {
    "status": "RUNNING",
    "uptime": 3600,
    "loop_count": 60
  }
}
```

### Subscribe to Symbol (Client → Server)
```json
{
  "type": "subscribe_symbol",
  "symbol": "EUR_USD"
}
```

## Tech Stack

### Frontend
- **React 18** - UI framework
- **Vite** - Build tool
- **TailwindCSS** - Styling
- **Lightweight Charts** - TradingView charting library
- **Framer Motion** - Animations
- **Zustand** - State management (planned)
- **Lucide React** - Icons

### Backend
- **FastAPI** - WebSocket server
- **Uvicorn** - ASGI server
- **psycopg2** - QuestDB connection
- **aiohttp** - Async HTTP client

## Roadmap

### Phase 1 (Current)
- [x] Basic WebSocket server
- [x] React dashboard structure
- [x] TradingView charts
- [x] Agent visualization
- [x] Portfolio tracking
- [x] System health monitoring

### Phase 2 (Next)
- [ ] Regime-aware chart backgrounds (HMM states)
- [ ] Ghost candles (Llama predictions)
- [ ] Stream of consciousness terminal (agent logs)
- [ ] Sentiment engine (word clouds, velocity)
- [ ] Footprint charts (bid/ask clusters)
- [ ] Agent consensus radar (spider plot)

### Phase 3 (Future)
- [ ] WebAssembly Python kernel (client-side backtesting)
- [ ] 3D options analytics (vol surface)
- [ ] Historical tick replay
- [ ] Multi-monitor support
- [ ] Mobile responsive design

## Performance

- **Chart FPS**: 60fps (WebGL rendering)
- **WebSocket Latency**: < 50ms
- **State Update Frequency**: 1 Hz (1 update/second)
- **Memory Usage**: ~200MB (React app)

## Troubleshooting

### WebSocket Connection Failed
- Check backend is running on port 8765
- Verify no firewall blocking connections
- Check browser console for errors

### Chart Not Rendering
- Ensure `lightweight-charts` is installed
- Check browser console for WebGL errors
- Verify chart data format is correct

### Slow Performance
- Reduce state update frequency in backend
- Limit number of active chart indicators
- Close unused browser tabs

## License

Proprietary - ATHENA-X Trading System

## Support

For issues or questions, contact the development team.
