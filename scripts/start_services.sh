#!/bin/bash
# Start JARVIS-X Services (Docker containers)

set -e

echo "=================================================="
echo "JARVIS-X - Starting Services"
echo "=================================================="

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    print_error "Docker is not running. Please start Docker first."
    exit 1
fi

# Navigate to docker directory
cd "$(dirname "$0")/../docker"

# Check if .env file exists
if [ ! -f ".env" ]; then
    print_warning ".env file not found. Creating from example..."
    cp .env.example .env
    print_warning "Please edit docker/.env with your credentials before continuing"
    exit 1
fi

# Stop any existing containers
print_info "Stopping existing containers..."
docker-compose down

# Start services
print_info "Starting JARVIS-X services..."
docker-compose up -d

# Wait for services to be ready
print_info "Waiting for services to be ready..."
sleep 10

# Check service health
print_info "Checking service health..."

# Check QuestDB
if curl -f http://localhost:9000 > /dev/null 2>&1; then
    print_info "✓ QuestDB is running on http://localhost:9000"
else
    print_error "✗ QuestDB failed to start"
fi

# Check Redis
if docker exec jarvis-redis redis-cli ping > /dev/null 2>&1; then
    print_info "✓ Redis is running on localhost:6379"
else
    print_error "✗ Redis failed to start"
fi

# Check PostgreSQL
if docker exec jarvis-postgres pg_isready > /dev/null 2>&1; then
    print_info "✓ PostgreSQL is running on localhost:5432"
else
    print_error "✗ PostgreSQL failed to start"
fi

# Check Prometheus (if enabled)
if curl -f http://localhost:9090/-/healthy > /dev/null 2>&1; then
    print_info "✓ Prometheus is running on http://localhost:9090"
fi

# Check Grafana (if enabled)
if curl -f http://localhost:3000/api/health > /dev/null 2>&1; then
    print_info "✓ Grafana is running on http://localhost:3000"
    print_info "  Default credentials: admin / jarvis_admin"
fi

print_info "=================================================="
print_info "Services started successfully!"
print_info "=================================================="
print_info ""
print_info "Service URLs:"
print_info "- QuestDB Console: http://localhost:9000"
print_info "- PostgreSQL: localhost:5432"
print_info "- Redis: localhost:6379"
print_info "- Prometheus: http://localhost:9090"
print_info "- Grafana: http://localhost:3000"
print_info ""
print_info "To stop services: docker-compose down"
print_info "To view logs: docker-compose logs -f"
