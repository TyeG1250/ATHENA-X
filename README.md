# ATHENA-X Trading System

**Version:** 1.0.0
**Environment:** Windows 11 + WSL2 (Ubuntu 24.04)
**Hardware:** NVIDIA RTX 3080 10GB VRAM
**Status:** Phase 1 Complete ✅

---

## 🚀 Overview

ATHENA-X is an advanced multi-agent AI trading system that combines cutting-edge machine learning, real-time data acquisition, and sophisticated risk management to execute profitable trades across forex, commodities, and indices.

### Key Features

- **Multi-Agent Architecture** - Hierarchical agents with contest mechanisms
- **Local AI Models** - Llama 3.1-8B, FinBERT, Phi-3-mini running on RTX 3080
- **Real-Time Data** - TradingView, OANDA, news, social sentiment
- **Advanced Risk Management** - Kelly Criterion, VaR, circuit breakers
- **Comprehensive Backtesting** - VectorBT integration with walk-forward optimization
- **Zero Cloud Costs** - Runs entirely on local hardware

### Performance Targets

- ✅ 65-70% win rate
- ✅ Sharpe ratio >1.5
- ✅ Maximum drawdown <20%
- ✅ Average 3-7% monthly returns
- ✅ Starting capital: $250-300

---

## 📋 Table of Contents

1. [System Requirements](#system-requirements)
2. [Installation](#installation)
3. [Configuration](#configuration)
4. [Quick Start](#quick-start)
5. [Architecture](#architecture)
6. [Development Phases](#development-phases)
7. [Usage](#usage)
8. [Monitoring](#monitoring)
9. [Troubleshooting](#troubleshooting)
10. [Contributing](#contributing)

---

## 💻 System Requirements

### Hardware (Minimum)
- **CPU:** Intel i5-10400 or AMD Ryzen 5 3600 (6 cores)
- **GPU:** NVIDIA RTX 3080 10GB VRAM (required)
- **RAM:** 32GB DDR4
- **Storage:** 500GB NVMe SSD
- **Network:** 100 Mbps stable connection

### Software
- Windows 11 Pro
- WSL2 (Ubuntu 24.04 LTS)
- CUDA 12.1 Toolkit
- cuDNN 8.9
- Docker Desktop for Windows
- Git 2.40+
- Python 3.10+

---

## 🔧 Installation

### 1. Clone Repository

```bash
git clone https://github.com/yourusername/ATHENA-X.git
cd ATHENA-X
```

### 2. Run Setup Script

```bash
chmod +x scripts/setup_environment.sh
./scripts/setup_environment.sh
```

This script will:
- Install system dependencies
- Set up Python virtual environment
- Install Docker and Docker Compose
- Install CUDA toolkit
- Install TA-Lib
- Create necessary directories

### 3. Configure Environment

```bash
cp docker/.env.example docker/.env
nano docker/.env  # Edit with your API credentials
```

Required credentials:
- OANDA API key and account ID
- Reddit API credentials (optional)
- Twitter API bearer token (optional)

### 4. Start Services

```bash
./scripts/start_services.sh
```

This starts:
- QuestDB (time-series database)
- Redis (caching layer)
- PostgreSQL (metadata storage)
- Prometheus (metrics)
- Grafana (dashboards)

### 5. Download AI Models

```bash
source venv/bin/activate
./scripts/download_models.sh
```

Downloads:
- FinBERT (sentiment analysis) - ~450MB
- Llama 3.1-8B-Instruct (trading analysis) - ~5GB
- Phi-3-mini (fast inference) - ~2.5GB
- Sentence Transformer (embeddings) - ~80MB

**Total:** ~8GB disk space

---

## ⚙️ Configuration

### Main Configuration (`config/settings.yaml`)

```yaml
system:
  environment: "development"  # development, paper, live

trading:
  initial_capital: 250.0
  symbols:
    - "EUR_USD"
    - "GBP_USD"
    - "XAU_USD"

risk:
  daily_loss_limit: 0.05  # 5%
  max_drawdown: 0.15  # 15%
  fractional_kelly: 0.5
```

### Agent Configuration (`config/agents_config.yaml`)

```yaml
technical_agent:
  weight: 0.35
  confidence_threshold: 0.75

sentiment_agent:
  weight: 0.20
  confidence_threshold: 0.80
```

### Risk Parameters (`config/risk_params.yaml`)

```yaml
position_sizing:
  max_position_pct: 0.02  # 2% per trade
  max_total_exposure: 0.06  # 6% total
```

---

## 🚀 Quick Start

### Activate Virtual Environment

```bash
source venv/bin/activate
```

### Test Data Pipeline

```bash
python -c "
from src.data.data_pipeline import ATHENADataPipeline
import yaml

with open('config/settings.yaml') as f:
    config = yaml.safe_load(f)

pipeline = ATHENADataPipeline(config)

# Health check
health = pipeline.health_check()
print('System Health:', health)

# Get market data
data = pipeline.get_complete_market_data('EUR_USD')
print('EUR/USD Data:', data['price_data'])
"
```

### Run Paper Trading (Phase 9+)

```bash
python main.py
```

### Run Backtest

```bash
python scripts/run_backtest.py --strategy multi_agent --start-date 2023-01-01 --capital 10000
```

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    ATHENA-X TRADING SYSTEM                   │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌──────────────┐    ┌──────────────────┐    ┌──────────────┐
│ DATA LAYER   │───▶│  AGENT SWARM     │───▶│ EXECUTION    │
│              │    │                  │    │ LAYER        │
│ - TradingView│    │ - Analysis Team  │    │              │
│ - News Scrape│    │ - Decision Team  │    │ - OANDA API  │
│ - Social Med │    │ - Risk Team      │    │ - Order Mgmt │
│ - OANDA Feed │    │ - Contest Mech   │    │ - Position   │
└──────────────┘    └──────────────────┘    └──────────────┘
```

### Component Breakdown

**Data Layer:**
- TradingView (price + indicators)
- OANDA (broker data feed)
- News scrapers (Reuters, CNBC, MarketWatch)
- Social media (Reddit, Twitter)
- Economic calendar (ForexFactory)

**Agent Layer:**
- Technical Analysis Agent
- Sentiment Analysis Agent
- Fundamental Analysis Agent
- Regime Detection Agent
- Risk Management Agent (veto power)

**Storage Layer:**
- QuestDB (time-series data)
- Redis (caching)
- PostgreSQL (metadata)

---

## 📊 Development Phases

### ✅ Phase 1: Foundation (Weeks 1-2) - **COMPLETE**

- ✅ Project structure created
- ✅ Docker services configured
- ✅ Data pipeline implemented
- ✅ OANDA client working
- ✅ TradingView scraper functional
- ✅ Storage layer (QuestDB, Redis, PostgreSQL)
- ✅ Logging and metrics system

### 🔄 Phase 2: Data Pipeline (Weeks 3-4) - **NEXT**

- News scrapers (Reuters, CNBC, MarketWatch)
- Economic calendar scraper
- Social media scrapers (Reddit, Twitter)
- Data validation layer

### 📅 Phase 3-10: Upcoming

- Agent architecture
- Model training
- Validation systems
- Sentiment integration
- Risk management
- Backtesting
- Paper trading
- Live deployment

---

## 📖 Usage

### Import Data Pipeline

```python
from src.data.data_pipeline import ATHENADataPipeline
import yaml

# Load configuration
with open('config/settings.yaml') as f:
    config = yaml.safe_load(f)

# Initialize pipeline
pipeline = ATHENADataPipeline(config)

# Get market data
data = pipeline.get_complete_market_data('EUR_USD')

print(data['price_data'])
print(data['technical_indicators'])
print(data['tradingview_analysis'])
```

### Use OANDA Client Directly

```python
from src.data.oanda_client import OANDAClient
import os

client = OANDAClient(
    api_key=os.getenv('OANDA_API_KEY'),
    account_id=os.getenv('OANDA_ACCOUNT_ID'),
    environment='practice'
)

# Get account info
account = client.get_account_summary()
print(f"Balance: ${account['balance']}")

# Get historical data
candles = client.get_candles('EUR_USD', granularity='M15', count=100)
print(candles.head())

# Get current price
prices = client.get_current_price(['EUR_USD', 'GBP_USD'])
print(prices)
```

### Use TradingView Scraper

```python
from src.data.tradingview_scraper import TradingViewClient

tv = TradingViewClient({})

# Get analysis
analysis = tv.get_analysis('EUR_USD', interval='15m')
print(f"Recommendation: {analysis['recommendation']['overall']}")
print(f"RSI: {analysis['indicators']['rsi']}")

# Check trend alignment
alignment = tv.check_trend_alignment('EUR_USD', intervals=['15m', '1h', '4h'])
print(f"Aligned: {alignment['aligned']}, Direction: {alignment['direction']}")
```

---

## 📈 Monitoring

### Access Dashboards

- **QuestDB Console:** http://localhost:9000
- **Grafana Dashboards:** http://localhost:3000 (admin/athena_admin)
- **Prometheus Metrics:** http://localhost:9090

### View Logs

```bash
# Real-time logs
tail -f logs/athena_$(date +%Y-%m-%d).log

# Error logs only
tail -f logs/errors_$(date +%Y-%m-%d).log

# Trading activity
tail -f logs/trades_$(date +%Y-%m-%d).log
```

### Check Service Status

```bash
cd docker
docker-compose ps
docker-compose logs -f
```

---

## 🐛 Troubleshooting

### Docker Services Won't Start

```bash
# Check Docker is running
docker info

# Restart services
cd docker
docker-compose down
docker-compose up -d

# Check logs
docker-compose logs
```

### OANDA Connection Failed

1. Verify API credentials in `docker/.env`
2. Check account ID format (include full ID)
3. Verify environment setting (practice vs live)
4. Test connection:

```python
from src.data.oanda_client import OANDAClient
import os

client = OANDAClient(
    api_key=os.getenv('OANDA_API_KEY'),
    account_id=os.getenv('OANDA_ACCOUNT_ID'),
    environment='practice'
)

print(client.get_account_summary())
```

### GPU Not Detected

```bash
# Check CUDA
nvcc --version
nvidia-smi

# Verify PyTorch CUDA
python -c "import torch; print(torch.cuda.is_available())"
```

### Redis Connection Refused

```bash
# Check Redis is running
docker exec athena-redis redis-cli ping

# Should return: PONG

# If fails, restart
docker-compose restart redis
```

---

## 🤝 Contributing

This is a personal trading system. Contributions are not currently accepted.

---

## ⚠️ Disclaimer

**IMPORTANT:** This software is for educational and research purposes only. Trading financial instruments carries significant risk. Past performance does not guarantee future results. Only trade with money you can afford to lose.

The authors and contributors are not responsible for any financial losses incurred through the use of this software.

---

## 📝 License

Proprietary - All Rights Reserved

---

## 📧 Contact

For questions or support, please open an issue in the GitHub repository.

---

**Built with ❤️ and Python**
*Making AI trading accessible to everyone*
