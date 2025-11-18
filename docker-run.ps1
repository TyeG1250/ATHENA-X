# ATHENA-X Docker Management Script for Windows
# Usage: .\docker-run.ps1 <command>

param(
    [Parameter(Position=0)]
    [string]$Command = "help"
)

$ErrorActionPreference = "Stop"

function Show-Help {
    Write-Host ""
    Write-Host "ATHENA-X Docker Management" -ForegroundColor Cyan
    Write-Host "============================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Usage: .\docker-run.ps1 <command>" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Available commands:" -ForegroundColor Green
    Write-Host "  build         - Build the ATHENA-X Docker image"
    Write-Host "  up            - Start all services (infrastructure + app)"
    Write-Host "  down          - Stop all services"
    Write-Host "  restart       - Restart all services"
    Write-Host "  logs          - Show logs from all services"
    Write-Host "  logs-app      - Show logs from athena-app only"
    Write-Host "  test          - Run system validation tests"
    Write-Host "  test-e2e      - Run end-to-end tests"
    Write-Host "  shell         - Open bash shell in athena-app container"
    Write-Host "  python        - Open Python REPL in athena-app container"
    Write-Host "  status        - Show status of all containers"
    Write-Host "  clean         - Remove all containers and volumes"
    Write-Host ""
    Write-Host "Examples:" -ForegroundColor Yellow
    Write-Host "  .\docker-run.ps1 build"
    Write-Host "  .\docker-run.ps1 up"
    Write-Host "  .\docker-run.ps1 test"
    Write-Host ""
}

function Build-Image {
    Write-Host "Building ATHENA-X Docker image..." -ForegroundColor Cyan
    Set-Location docker
    docker-compose build athena-app
    Set-Location ..
    Write-Host "Build complete!" -ForegroundColor Green
}

function Start-Services {
    Write-Host "Starting ATHENA-X services..." -ForegroundColor Cyan
    Set-Location docker
    docker-compose up -d
    Set-Location ..
    Write-Host ""
    Write-Host "Services started!" -ForegroundColor Green
    Write-Host ""
    Show-Status
}

function Stop-Services {
    Write-Host "Stopping ATHENA-X services..." -ForegroundColor Cyan
    Set-Location docker
    docker-compose down
    Set-Location ..
    Write-Host "Services stopped!" -ForegroundColor Green
}

function Restart-Services {
    Write-Host "Restarting ATHENA-X services..." -ForegroundColor Cyan
    Stop-Services
    Start-Sleep -Seconds 2
    Start-Services
}

function Show-Logs {
    Set-Location docker
    docker-compose logs -f
    Set-Location ..
}

function Show-AppLogs {
    Set-Location docker
    docker-compose logs -f athena-app
    Set-Location ..
}

function Run-Tests {
    Write-Host "Running system validation tests..." -ForegroundColor Cyan
    docker exec athena-app python tests/test_system_validation.py
}

function Run-E2ETests {
    Write-Host "Running end-to-end tests..." -ForegroundColor Cyan
    docker exec athena-app python tests/test_end_to_end.py
}

function Open-Shell {
    Write-Host "Opening bash shell in athena-app..." -ForegroundColor Cyan
    docker exec -it athena-app /bin/bash
}

function Open-Python {
    Write-Host "Opening Python REPL in athena-app..." -ForegroundColor Cyan
    docker exec -it athena-app python
}

function Show-Status {
    Write-Host "Container Status:" -ForegroundColor Cyan
    docker ps --filter "name=athena-" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
}

function Clean-All {
    Write-Host "WARNING: This will remove all ATHENA-X containers and volumes!" -ForegroundColor Red
    $confirmation = Read-Host "Are you sure? (yes/no)"
    if ($confirmation -eq "yes") {
        Write-Host "Cleaning up..." -ForegroundColor Cyan
        Set-Location docker
        docker-compose down -v
        Set-Location ..
        Write-Host "Cleanup complete!" -ForegroundColor Green
    } else {
        Write-Host "Cancelled." -ForegroundColor Yellow
    }
}

# Main command dispatcher
switch ($Command.ToLower()) {
    "build"     { Build-Image }
    "up"        { Start-Services }
    "down"      { Stop-Services }
    "restart"   { Restart-Services }
    "logs"      { Show-Logs }
    "logs-app"  { Show-AppLogs }
    "test"      { Run-Tests }
    "test-e2e"  { Run-E2ETests }
    "shell"     { Open-Shell }
    "python"    { Open-Python }
    "status"    { Show-Status }
    "clean"     { Clean-All }
    "help"      { Show-Help }
    default     {
        Write-Host "Unknown command: $Command" -ForegroundColor Red
        Show-Help
        exit 1
    }
}
