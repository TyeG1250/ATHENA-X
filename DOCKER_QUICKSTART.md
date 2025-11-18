# ATHENA-X Docker Quick Start Guide

**For Windows Users (and Linux/macOS)**

This guide helps you run ATHENA-X entirely in Docker containers.

---

## Prerequisites

- Docker Desktop installed and running
- Git (optional, if cloning repository)

**Verify Docker is running:**
```powershell
docker --version
docker-compose --version
```

---

## Quick Start (PowerShell Script - Windows)

### Step 1: Build the Docker Image

```powershell
.\docker-run.ps1 build
```

This builds the `athena-app` container with all Python dependencies.

### Step 2: Start All Services

```powershell
.\docker-run.ps1 up
```

This starts:
- `athena-app` - Python application
- `athena-questdb` - Time-series database
- `athena-redis` - Cache
- `athena-postgres` - Metadata storage
- `athena-prometheus` - Metrics
- `athena-grafana` - Dashboards

### Step 3: Check Status

```powershell
.\docker-run.ps1 status
```

**Expected output:**
```
NAMES               STATUS              PORTS
athena-app          Up 2 minutes
athena-grafana      Up 2 minutes        0.0.0.0:3000->3000/tcp
athena-postgres     Up 2 minutes        0.0.0.0:5432->5432/tcp
athena-prometheus   Up 2 minutes        0.0.0.0:9090->9090/tcp
athena-questdb      Up 2 minutes        0.0.0.0:8812->8812/tcp, 0.0.0.0:9000->9000/tcp, 0.0.0.0:9009->9009/tcp
athena-redis        Up 2 minutes        0.0.0.0:6379->6379/tcp
```

### Step 4: Run System Validation Tests

```powershell
.\docker-run.ps1 test
```

**Expected result:** 93.9% pass rate (31/33 tests)

### Step 5: Open Interactive Shell (Optional)

```powershell
.\docker-run.ps1 shell
```

This opens a bash shell inside the container where you can run Python commands directly.

---

## Manual Commands (If not using PowerShell script)

### Build Image

```powershell
cd docker
docker-compose build athena-app
cd ..
```

### Start Services

```powershell
cd docker
docker-compose up -d
cd ..
```

### Run Tests

```powershell
docker exec athena-app python tests/test_system_validation.py
```

### Run End-to-End Tests

```powershell
docker exec athena-app python tests/test_end_to_end.py
```

### Open Shell

```powershell
docker exec -it athena-app /bin/bash
```

### View Logs

```powershell
# All services
cd docker
docker-compose logs -f

# Just the app
docker-compose logs -f athena-app
cd ..
```

### Stop Services

```powershell
cd docker
docker-compose down
cd ..
```

---

## PowerShell Script Commands Reference

| Command | Description |
|---------|-------------|
| `.\docker-run.ps1 build` | Build the ATHENA-X Docker image |
| `.\docker-run.ps1 up` | Start all services |
| `.\docker-run.ps1 down` | Stop all services |
| `.\docker-run.ps1 restart` | Restart all services |
| `.\docker-run.ps1 logs` | Show logs from all services |
| `.\docker-run.ps1 logs-app` | Show logs from app only |
| `.\docker-run.ps1 test` | Run system validation tests |
| `.\docker-run.ps1 test-e2e` | Run end-to-end tests |
| `.\docker-run.ps1 shell` | Open bash shell in container |
| `.\docker-run.ps1 python` | Open Python REPL in container |
| `.\docker-run.ps1 status` | Show container status |
| `.\docker-run.ps1 clean` | Remove all containers/volumes |

---

## Accessing Services

Once services are running:

| Service | URL | Credentials |
|---------|-----|-------------|
| **Grafana** | http://localhost:3000 | admin / athena_admin |
| **Prometheus** | http://localhost:9090 | - |
| **QuestDB** | http://localhost:9000 | - |
| **PostgreSQL** | localhost:5432 | athena_user / athena_postgres_password |
| **Redis** | localhost:6379 | Password: athena_redis_password |

---

## Running the Trading System

### Paper Trading (Inside Container)

```powershell
# Open shell
.\docker-run.ps1 shell

# Inside container:
python scripts/deploy.py --mode paper --symbols EUR_USD --capital 250
```

### Or directly:

```powershell
docker exec -it athena-app python scripts/deploy.py --mode paper --symbols EUR_USD --capital 250
```

---

## Troubleshooting

### Container Not Found

If you get "No such container: athena-app":

1. Build the image first:
   ```powershell
   .\docker-run.ps1 build
   ```

2. Start the services:
   ```powershell
   .\docker-run.ps1 up
   ```

3. Verify it's running:
   ```powershell
   .\docker-run.ps1 status
   ```

### Build Errors

If build fails due to Python dependencies:

```powershell
# Clean everything and rebuild
.\docker-run.ps1 clean
.\docker-run.ps1 build
```

### Port Already in Use

If you get "port is already allocated":

```powershell
# Stop other services using those ports, or modify docker-compose.yml ports
# Common conflicts: PostgreSQL (5432), Redis (6379), Grafana (3000)
```

### Out of Memory

Docker Desktop default memory limit may be too low:

1. Open Docker Desktop
2. Settings → Resources
3. Increase Memory to at least 4GB (8GB recommended)
4. Apply & Restart

---

## File Synchronization

The Docker container mounts your local `ATHENA-X` directory, so:

- **Code changes on Windows are immediately visible in the container**
- **You can edit files in VS Code on Windows and test in Docker**
- **Logs written by container appear in your local `logs/` folder**

---

## Development Workflow

### Recommended workflow:

1. **Start services once:**
   ```powershell
   .\docker-run.ps1 up
   ```

2. **Edit code on Windows** (VS Code, PyCharm, etc.)

3. **Run tests in Docker:**
   ```powershell
   .\docker-run.ps1 test
   ```

4. **Check logs:**
   ```powershell
   .\docker-run.ps1 logs-app
   ```

5. **When done:**
   ```powershell
   .\docker-run.ps1 down
   ```

---

## Alternative: Running Without Docker

If you prefer to run natively on Windows:

### Option 1: WSL2 (Recommended)

```powershell
# Install WSL2 and Ubuntu
wsl --install

# Open Ubuntu terminal
wsl

# Follow the deployment guide (DEPLOYMENT_GUIDE.md)
cd /mnt/g/Users/TMG/ATHENA-X
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python tests/test_system_validation.py
```

### Option 2: Native Windows Python

```powershell
# Create virtual environment
python -m venv venv

# Activate (PowerShell)
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Run tests
python tests\test_system_validation.py
```

**Note:** Some packages (like `oandapyV20`) may have build issues on Windows. Using Docker or WSL2 avoids these problems.

---

## Next Steps

1. ✅ **Build and start services** - `.\docker-run.ps1 build && .\docker-run.ps1 up`
2. ✅ **Run validation tests** - `.\docker-run.ps1 test`
3. ⏳ **Configure OANDA credentials** - Edit `.env` file
4. ⏳ **Deploy to paper trading** - `docker exec -it athena-app python scripts/deploy.py --mode paper`
5. ⏳ **Monitor performance** - http://localhost:3000 (Grafana)

---

## Quick Reference

**Start everything:**
```powershell
.\docker-run.ps1 up
```

**Run tests:**
```powershell
.\docker-run.ps1 test
```

**Interactive shell:**
```powershell
.\docker-run.ps1 shell
```

**Stop everything:**
```powershell
.\docker-run.ps1 down
```

---

**You're now ready to run ATHENA-X in Docker! 🐳🚀**

For more details, see:
- `DEPLOYMENT_GUIDE.md` - Complete deployment guide
- `SESSION_SUMMARY.md` - Latest updates
- `CURRENT_STATUS.md` - System status
