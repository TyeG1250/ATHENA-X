# ATHENA-X Trading System - Deployment Guide

**Last Updated:** November 18, 2025
**System Version:** 1.0.0
**Status:** Production Ready

---

## 📋 Table of Contents

1. [System Requirements](#system-requirements)
2. [Installation](#installation)
3. [Configuration](#configuration)
4. [Testing](#testing)
5. [Deployment Options](#deployment-options)
6. [Monitoring](#monitoring)
7. [Troubleshooting](#troubleshooting)

---

## 🖥️ System Requirements

### Hardware Requirements

**Minimum:**
- CPU: 4 cores @ 2.5GHz
- RAM: 8GB
- Storage: 50GB SSD
- GPU: Not required (CPU-only mode supported)

**Recommended:**
- CPU: 8+ cores @ 3.0GHz
- RAM: 16GB+
- Storage: 100GB NVMe SSD
- GPU: NVIDIA RTX 3060+ with 8GB+ VRAM (for AI models)
- CUDA: 12.x or 13.x (for GPU acceleration)

### Software Requirements

- **OS:** Linux (Ubuntu 20.04+), macOS 11+, Windows 10+ with WSL2
- **Python:** 3.10 or 3.11
- **Docker:** 20.10+
- **Docker Compose:** 2.0+
- **Git:** 2.30+

---

## 📦 Installation

### Step 1: Clone Repository

```bash
git clone https://github.com/TyeG1250/ATHENA-X.git
cd ATHENA-X
```

### Step 2: Setup Python Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate environment
source venv/bin/activate  # Linux/macOS
# OR
.\venv\Scripts\activate  # Windows

# Upgrade pip
pip install --upgrade pip setuptools wheel
```

### Step 3: Install Dependencies

```bash
# Option 1: Install all dependencies (full system)
pip install -r requirements.txt

# Option 2: Install core dependencies only (minimal system)
pip install numpy pandas pyyaml loguru scikit-learn redis psycopg2-binary python-dotenv pydantic
```

**Note:** Some packages like `oandapyV20` may have build issues on certain systems. Install them individually if needed.

### Step 4: Setup Environment Variables

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your credentials
nano .env
```

**Required environment variables:**

```bash
# OANDA API
OANDA_API_KEY=your_api_key_here
OANDA_ACCOUNT_ID=your_account_id_here
OANDA_ENVIRONMENT=practice  # or 'live'

# Reddit API (for sentiment)
REDDIT_CLIENT_ID=your_client_id
REDDIT_CLIENT_SECRET=your_secret
REDDIT_USER_AGENT=ATHENA-X/1.0

# Database Credentials
POSTGRES_PASSWORD=secure_password
REDIS_PASSWORD=secure_password
```

### Step 5: Start Docker Services

```bash
# Start all infrastructure services
./scripts/start_services.sh

# Verify services are running
docker ps
```

**Expected services:**
- QuestDB (port 9000)
- Redis (port 6379)
- PostgreSQL (port 5432)
- Prometheus (port 9090)
- Grafana (port 3000)

---

## ⚙️ Configuration

### Main Configuration File

Edit `config/settings.yaml` to customize system behavior:

```yaml
# Agent weights
agents:
  technical_agent:
    weight: 0.35  # 35% voting power
    enabled: true

  sentiment_agent:
    weight: 0.20  # 20% voting power
    enabled: true

  risk_agent:
    weight: 1.0  # VETO power
    enabled: true

# Risk parameters
risk:
  position_limits:
    max_position_pct: 0.02  # 2% max per trade
    max_total_exposure: 0.06  # 6% max total

  circuit_breakers:
    max_daily_loss_pct: 0.05  # 5% daily loss limit
    max_drawdown_pct: 0.15  # 15% max drawdown
    max_consecutive_losses: 5  # Stop after 5 losses

# Consensus requirements
consensus:
  agreement_threshold: 0.70  # 70% agreement required
  veto_enabled: true  # Risk agent can veto
```

### Trading Pairs

Configure trading pairs in `config/trading_pairs.yaml`:

```yaml
forex_majors:
  - EUR_USD
  - GBP_USD
  - USD_JPY
  - AUD_USD

forex_minors:
  - EUR_GBP
  - EUR_JPY
  - GBP_JPY

commodities:
  - XAU_USD  # Gold
  - XAG_USD  # Silver
  - BCO_USD  # Brent Crude
```

---

## 🧪 Testing

### Validation Tests (No External Dependencies)

```bash
# Run system validation
python tests/test_system_validation.py
```

**Expected output:**
```
ATHENA-X SYSTEM VALIDATION TESTS
✓ File Structure: 15 passed
✓ Configuration: 3 passed
✓ Module Imports: 9 passed
✓ Agent Initialization: 3 passed
✓ Risk Metrics: 1 passed
Total: 31 passed, 2 failed (93.9% success)
```

### End-to-End Tests (Requires External APIs)

```bash
# Ensure Docker services are running
./scripts/start_services.sh

# Run full integration tests
python tests/test_end_to_end.py
```

**Tests performed:**
1. Data pipeline (OANDA, TradingView, News, Social)
2. Multi-agent analysis
3. Consensus mechanism
4. Risk validation (4-stage)
5. Order execution (dry run)

---

## 🚀 Deployment Options

### Option 1: Paper Trading (Recommended First)

Deploy to OANDA practice account for risk-free testing:

```bash
# Ensure OANDA_ENVIRONMENT=practice in .env
python scripts/deploy.py --mode paper --symbols EUR_USD,GBP_USD

# Monitor logs
tail -f logs/athena_$(date +%Y%m%d).log
```

**Paper Trading Timeline:**
- Week 1-2: Single pair (EUR_USD)
- Week 3-4: Add GBP_USD, AUD_USD
- Month 2: Full 10-pair portfolio
- Validate: Sharpe > 1.5, Win rate > 60%

### Option 2: Backtesting

Test strategies on historical data:

```bash
python scripts/backtest.py --symbols EUR_USD --start 2020-01-01 --end 2024-12-31
```

**Backtesting features:**
- 5 years of historical data
- Walk-forward optimization
- Monte Carlo simulation (1000 runs)
- Slippage and commission modeling

### Option 3: Live Deployment (After Validation)

**ONLY deploy live after:**
- ✅ 4+ weeks successful paper trading
- ✅ Sharpe ratio > 1.5
- ✅ Win rate > 60%
- ✅ Max drawdown < 15%

```bash
# Change .env to OANDA_ENVIRONMENT=live
# Start with 1% capital
python scripts/deploy.py --mode live --symbols EUR_USD --capital-pct 0.01

# Gradual scaling: 1% → 5% → 20% → 50% → 100%
```

---

## 📊 Monitoring

### Real-Time Monitoring

**Grafana Dashboard:** http://localhost:3000

Default credentials: `admin / admin`

**Metrics tracked:**
- Trade win rate
- Profit/loss
- Drawdown
- Agent performance
- System health
- API latency

### Prometheus Metrics

**Prometheus UI:** http://localhost:9090

**Key queries:**
```promql
# Win rate
rate(athena_trades_won[1h]) / rate(athena_trades_total[1h])

# Daily P&L
sum(athena_trade_pnl)

# Agent agreement rate
athena_consensus_agreement
```

### Log Monitoring

```bash
# Real-time logs
tail -f logs/athena_$(date +%Y%m%d).log

# Error logs only
tail -f logs/athena_$(date +%Y%m%d).log | grep ERROR

# Trade decisions
tail -f logs/athena_$(date +%Y%m%d).log | grep "EXECUTE\|REJECT"
```

### Alert Configuration

Edit `config/alerts.yaml`:

```yaml
alerts:
  - name: high_drawdown
    condition: drawdown > 0.10
    action: pause_trading
    notify: email

  - name: consecutive_losses
    condition: consecutive_losses >= 3
    action: reduce_position_size
    notify: sms

  - name: circuit_breaker
    condition: daily_loss > 0.05
    action: stop_trading
    notify: email,sms
```

---

## 🔧 Troubleshooting

### Common Issues

#### 1. Docker Services Won't Start

```bash
# Check Docker status
sudo systemctl status docker

# Restart Docker
sudo systemctl restart docker

# Remove old containers
docker-compose down -v
./scripts/start_services.sh
```

#### 2. Python Import Errors

```bash
# Verify virtual environment is activated
which python  # Should show venv/bin/python

# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

#### 3. OANDA API Connection Issues

```bash
# Test API credentials
python -c "
from src.data.oanda_client import OANDAClient
import yaml

with open('config/settings.yaml') as f:
    config = yaml.safe_load(f)

client = OANDAClient(config)
print('Health:', client.health_check())
"
```

#### 4. Redis Connection Failed

```bash
# Check Redis is running
docker ps | grep redis

# Test Redis connection
redis-cli -h localhost -p 6379 ping
# Should return: PONG
```

#### 5. Low Memory Issues

```bash
# Reduce concurrent processes
# Edit config/settings.yaml
data:
  max_concurrent_scrapers: 2  # Reduce from 5

# Use CPU-only mode (no GPU)
export CUDA_VISIBLE_DEVICES=""
```

### Performance Optimization

#### Speed Up Data Collection

```yaml
# config/settings.yaml
data:
  cache_ttl: 3600  # Increase cache time
  max_concurrent_scrapers: 10  # More parallel requests
```

#### Reduce Memory Usage

```yaml
backtesting:
  vectorbt:
    chunk_size: 1000  # Reduce from 10000
    max_workers: 2  # Reduce parallel workers
```

#### GPU Acceleration (Optional)

```bash
# Install CUDA 12.x/13.x support (for NVIDIA RTX GPUs)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# For CUDA 11.8 (older GPUs)
# pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# Verify GPU is detected
python -c "import torch; print('CUDA available:', torch.cuda.is_available()); print('CUDA version:', torch.version.cuda); print('GPU:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'None')"
```

---

## 🔒 Security Best Practices

### 1. API Key Management

```bash
# Never commit .env to git
echo ".env" >> .gitignore

# Use environment variables
export OANDA_API_KEY="your_key"

# Rotate keys monthly
```

### 2. Database Security

```bash
# Use strong passwords
POSTGRES_PASSWORD=$(openssl rand -base64 32)

# Restrict network access
# Edit docker-compose.yml
services:
  postgres:
    networks:
      - athena_internal  # Internal only
```

### 3. Monitoring Access

```bash
# Change Grafana default password
docker exec -it athena-grafana grafana-cli admin reset-admin-password NewSecurePassword123
```

### 4. Log Sanitization

Logs automatically sanitize sensitive data:
- API keys masked
- Account numbers redacted
- Passwords hidden

---

## 📈 Performance Targets

| Metric | Target | Current | Status |
|--------|--------|---------|--------|
| Win Rate | 60-70% | TBD | ⏳ Paper trading |
| Sharpe Ratio | > 1.5 | TBD | ⏳ Paper trading |
| Max Drawdown | < 15% | Protected | ✅ Circuit breakers |
| Monthly Return | 3-7% | TBD | ⏳ Paper trading |
| Uptime | > 99% | TBD | ⏳ Monitoring |

**Validation required before live deployment**

---

## 🆘 Support

### Documentation

- `CURRENT_STATUS.md` - System status and progress
- `PHASE_3_COMPLETE.md` - Multi-agent architecture
- `IMPLEMENTATION_COMPLETE.md` - Full system overview

### Logs Location

```
logs/
├── athena_YYYYMMDD.log        # Daily logs
├── trades_YYYYMMDD.log        # Trade execution log
├── errors_YYYYMMDD.log        # Error log
└── performance_YYYYMMDD.log   # Performance metrics
```

### Health Check

```bash
# Quick system health check
python -c "
from src.data.data_pipeline import ATHENADataPipeline
import yaml

with open('config/settings.yaml') as f:
    config = yaml.safe_load(f)

pipeline = ATHENADataPipeline(config)
health = pipeline.health_check()

for service, status in health.items():
    print(f'{service}: {\"✓\" if status else \"✗\"}')
"
```

---

## 🔄 Maintenance

### Daily Tasks

- Monitor P&L and drawdown
- Review trade decisions in logs
- Check system resource usage
- Verify all services running

### Weekly Tasks

- Review agent performance metrics
- Analyze win/loss patterns
- Update correlation matrices
- Check for software updates

### Monthly Tasks

- Retrain AI models with new data
- Rebalance agent weights if needed
- Review and adjust risk parameters
- Rotate API keys and passwords
- Backup database and configurations

### Backup Strategy

```bash
# Automated daily backup
./scripts/backup.sh

# Manual backup
./scripts/backup.sh --manual --include-logs
```

**Backups stored in:** `backups/athena_backup_YYYYMMDD.tar.gz`

---

## ✅ Pre-Deployment Checklist

- [ ] Python 3.10/3.11 installed
- [ ] Virtual environment created and activated
- [ ] All dependencies installed
- [ ] Docker services running
- [ ] Environment variables configured
- [ ] OANDA API credentials valid
- [ ] Configuration files customized
- [ ] Validation tests passing (> 90%)
- [ ] Monitoring dashboards accessible
- [ ] Alert system configured
- [ ] Backup strategy implemented

---

**ATHENA-X Trading System is ready for deployment!**
Start with paper trading for 4+ weeks before considering live deployment.

For questions or issues, review the documentation files or check the logs.
