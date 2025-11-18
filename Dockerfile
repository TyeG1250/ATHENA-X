# ATHENA-X Trading System - Docker Image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for better caching)
COPY requirements.txt .

# Install Python dependencies
# Install core dependencies first
RUN pip install --no-cache-dir \
    numpy>=1.24.0 \
    pandas>=2.0.0 \
    scipy>=1.10.0 \
    scikit-learn>=1.3.0 \
    pyyaml>=6.0 \
    loguru>=0.7.0 \
    python-dotenv>=1.0.0 \
    pydantic>=2.5.0 \
    redis>=5.0.0 \
    psycopg2-binary>=2.9.9 \
    requests>=2.31.0 \
    beautifulsoup4>=4.12.0 \
    click>=8.1.0 \
    tqdm>=4.66.0 \
    prometheus-client>=0.19.0 \
    psutil>=5.9.0

# Install testing dependencies
RUN pip install --no-cache-dir \
    pytest>=7.4.0 \
    pytest-cov>=4.1.0 \
    pytest-asyncio>=0.21.0 \
    pytest-mock>=3.12.0

# Install web scraping dependencies
RUN pip install --no-cache-dir \
    feedparser>=6.0.10 \
    fake-useragent>=1.4.0 \
    selenium>=4.15.0 \
    yfinance>=0.2.0

# Install ML/AI dependencies (large packages)
RUN pip install --no-cache-dir \
    torch>=2.0.0 \
    transformers>=4.35.0 \
    sentence-transformers>=2.2.0 \
    accelerate>=0.24.0 \
    peft>=0.6.0 \
    bitsandbytes>=0.41.0 \
    datasets>=2.14.0

# Install financial analysis dependencies
RUN pip install --no-cache-dir \
    statsmodels>=0.14.0 \
    hmmlearn>=0.3.0

# Install optional dependencies (may fail on some systems)
RUN pip install --no-cache-dir \
    oandapyV20>=0.7.2 \
    tradingview-ta>=3.3.0 \
    praw>=7.7.1 \
    || echo "Warning: Some optional dependencies failed to install"

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p logs data/cache data/models config

# Set Python path
ENV PYTHONPATH=/app:$PYTHONPATH

# Default command
CMD ["python", "-m", "pytest", "--version"]
