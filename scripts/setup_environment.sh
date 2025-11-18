#!/bin/bash
# JARVIS-X Environment Setup Script
# For WSL2 Ubuntu 24.04

set -e  # Exit on error

echo "=================================================="
echo "JARVIS-X Trading System - Environment Setup"
echo "=================================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running on WSL2
print_info "Checking WSL2 environment..."
if grep -qi microsoft /proc/version; then
    print_info "WSL2 detected"
else
    print_warning "Not running on WSL2, continuing anyway..."
fi

# Update system packages
print_info "Updating system packages..."
sudo apt update
sudo apt upgrade -y

# Install essential build tools
print_info "Installing build essentials..."
sudo apt install -y \
    build-essential \
    git \
    curl \
    wget \
    ca-certificates \
    gnupg \
    lsb-release

# Install Python 3.10+
print_info "Checking Python version..."
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    print_info "Python $PYTHON_VERSION found"
else
    print_info "Installing Python 3.10..."
    sudo apt install -y python3.10 python3.10-venv python3-pip
fi

# Install Docker
print_info "Checking Docker installation..."
if command -v docker &> /dev/null; then
    print_info "Docker already installed"
else
    print_info "Installing Docker..."

    # Add Docker's official GPG key
    sudo mkdir -p /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

    # Set up the repository
    echo \
      "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
      $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

    # Install Docker Engine
    sudo apt update
    sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

    # Add user to docker group
    sudo usermod -aG docker $USER
    print_info "Docker installed. You may need to log out and back in for group changes to take effect."
fi

# Install Docker Compose
print_info "Checking Docker Compose..."
if command -v docker-compose &> /dev/null; then
    print_info "Docker Compose already installed"
else
    print_info "Installing Docker Compose..."
    sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
fi

# Install CUDA Toolkit (for WSL2)
print_info "Checking CUDA installation..."
if command -v nvcc &> /dev/null; then
    CUDA_VERSION=$(nvcc --version | grep "release" | awk '{print $5}' | cut -d',' -f1)
    print_info "CUDA $CUDA_VERSION found"
else
    print_warning "CUDA not found. Please install CUDA Toolkit 12.1+ manually from NVIDIA"
    print_info "Visit: https://developer.nvidia.com/cuda-downloads"
fi

# Install Python virtual environment
print_info "Creating Python virtual environment..."
cd "$(dirname "$0")/.."
python3 -m venv venv

# Activate virtual environment
print_info "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
print_info "Upgrading pip..."
pip install --upgrade pip setuptools wheel

# Install TA-Lib dependencies
print_info "Installing TA-Lib dependencies..."
sudo apt install -y \
    libta-lib0-dev \
    libatlas-base-dev \
    libopenblas-dev \
    liblapack-dev

# Download and install TA-Lib
if [ ! -f "/usr/local/lib/libta_lib.so" ]; then
    print_info "Installing TA-Lib from source..."
    cd /tmp
    wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz
    tar -xzf ta-lib-0.4.0-src.tar.gz
    cd ta-lib/
    ./configure --prefix=/usr/local
    make
    sudo make install
    cd -
fi

# Return to project directory
cd "$(dirname "$0")/.."

# Install Python requirements
print_info "Installing Python requirements..."
pip install -r requirements.txt

# Create .env file from example
if [ ! -f "docker/.env" ]; then
    print_info "Creating .env file from example..."
    cp docker/.env.example docker/.env
    print_warning "Please edit docker/.env with your actual credentials"
fi

# Create necessary directories
print_info "Creating data directories..."
mkdir -p data/raw data/processed data/models data/backtest
mkdir -p logs

# Set permissions
print_info "Setting permissions..."
chmod +x scripts/*.sh

# Install Jupyter kernel
print_info "Installing Jupyter kernel..."
python -m ipykernel install --user --name=jarvis-x --display-name "JARVIS-X"

print_info "=================================================="
print_info "Environment setup complete!"
print_info "=================================================="
print_info ""
print_info "Next steps:"
print_info "1. Edit docker/.env with your API credentials"
print_info "2. Run: ./scripts/start_services.sh (to start databases)"
print_info "3. Run: ./scripts/download_models.sh (to download AI models)"
print_info "4. Activate venv: source venv/bin/activate"
print_info ""
print_warning "If Docker commands fail, log out and back in to apply group changes"
