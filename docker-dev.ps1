# Docker Development Script for Knowledge Graph Visualizer
# This script helps with common Docker development tasks

param(
    [Parameter(Position=0)]
    [string]$Command = "help",
    [Parameter(Position=1)]
    [string]$Environment = "dev"
)

function Show-Help {
    Write-Host "Knowledge Graph Visualizer - Docker Development Script" -ForegroundColor Green
    Write-Host ""
    Write-Host "Usage: .\docker-dev.ps1 [command] [environment]" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Commands:" -ForegroundColor Cyan
    Write-Host "  start     - Start all services (GraphDB + Web Interface)"
    Write-Host "  stop      - Stop all services"
    Write-Host "  restart   - Restart all services"
    Write-Host "  build     - Build the application image"
    Write-Host "  rebuild   - Force rebuild without cache"
    Write-Host "  logs      - Show logs from all services"
    Write-Host "  logs-app  - Show logs from web interface only"
    Write-Host "  logs-db   - Show logs from GraphDB only"
    Write-Host "  clean     - Remove all containers and images"
    Write-Host "  status    - Show status of all services"
    Write-Host "  shell     - Open shell in web interface container"
    Write-Host "  health    - Check health of all services"
    Write-Host "  prod      - Start in production mode"
    Write-Host "  help      - Show this help message"
    Write-Host ""
    Write-Host "Environments:" -ForegroundColor Magenta
    Write-Host "  dev       - Development mode (default)"
    Write-Host "  prod      - Production mode"
    Write-Host ""
    Write-Host "Examples:" -ForegroundColor Magenta
    Write-Host "  .\docker-dev.ps1 start"
    Write-Host "  .\docker-dev.ps1 start prod"
    Write-Host "  .\docker-dev.ps1 logs-app"
    Write-Host "  .\docker-dev.ps1 shell"
    Write-Host "  .\docker-dev.ps1 prod"
}

function Get-ComposeFile {
    if ($Environment -eq "prod") {
        return "docker-compose.prod.yml"
    } else {
        return "docker-compose.yml"
    }
}

function Start-Services {
    $composeFile = Get-ComposeFile
    Write-Host "Starting Knowledge Graph Visualizer ($Environment mode)..." -ForegroundColor Green
    docker-compose -f $composeFile up -d
    
    Write-Host ""
    Write-Host "Waiting for services to be ready..." -ForegroundColor Yellow
    Start-Sleep -Seconds 10
    
    Write-Host ""
    Write-Host "Services started!" -ForegroundColor Green
    if ($Environment -eq "prod") {
        Write-Host "Web Interface: http://localhost" -ForegroundColor Cyan
    } else {
        Write-Host "Web Interface: http://localhost:5000" -ForegroundColor Cyan
    }
    Write-Host "GraphDB Workbench: http://localhost:7200" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Tip: Use '.\docker-dev.ps1 logs-app' to monitor the web interface logs" -ForegroundColor Blue
}

function Stop-Services {
    $composeFile = Get-ComposeFile
    Write-Host "Stopping all services..." -ForegroundColor Yellow
    docker-compose -f $composeFile down
    Write-Host "Services stopped!" -ForegroundColor Green
}

function Restart-Services {
    $composeFile = Get-ComposeFile
    Write-Host "Restarting all services..." -ForegroundColor Yellow
    docker-compose -f $composeFile restart
    Write-Host "Services restarted!" -ForegroundColor Green
}

function Build-Application {
    $composeFile = Get-ComposeFile
    Write-Host "Building application image ($Environment mode)..." -ForegroundColor Blue
    docker-compose -f $composeFile build
    Write-Host "Build completed!" -ForegroundColor Green
}

function Rebuild-Application {
    $composeFile = Get-ComposeFile
    Write-Host "Force rebuilding application image ($Environment mode)..." -ForegroundColor Blue
    docker-compose -f $composeFile build --no-cache
    Write-Host "Rebuild completed!" -ForegroundColor Green
}

function Show-Logs {
    $composeFile = Get-ComposeFile
    Write-Host "Showing logs from all services..." -ForegroundColor Blue
    docker-compose -f $composeFile logs -f
}

function Show-AppLogs {
    $composeFile = Get-ComposeFile
    Write-Host "Showing logs from web interface..." -ForegroundColor Blue
    docker-compose -f $composeFile logs -f kg-visualizer
}

function Show-DbLogs {
    $composeFile = Get-ComposeFile
    Write-Host "Showing logs from GraphDB..." -ForegroundColor Blue
    docker-compose -f $composeFile logs -f graphdb
}

function Clean-All {
    Write-Host "Cleaning up containers and images..." -ForegroundColor Red
    docker-compose -f docker-compose.yml down --rmi all --volumes --remove-orphans
    docker-compose -f docker-compose.prod.yml down --rmi all --volumes --remove-orphans
    Write-Host "Cleanup completed!" -ForegroundColor Green
}

function Show-Status {
    $composeFile = Get-ComposeFile
    Write-Host "Service Status ($Environment mode):" -ForegroundColor Cyan
    docker-compose -f $composeFile ps
}

function Show-Health {
    $composeFile = Get-ComposeFile
    Write-Host "Health Check:" -ForegroundColor Cyan
    Write-Host ""
    
    # Check GraphDB
    try {
        $graphdbResponse = Invoke-WebRequest -Uri "http://localhost:7200/rest/repositories" -TimeoutSec 5
        Write-Host "GraphDB: Healthy (Status: $($graphdbResponse.StatusCode))" -ForegroundColor Green
    } catch {
        Write-Host "GraphDB: Unhealthy" -ForegroundColor Red
    }
    
    # Check Web Interface
    try {
        $port = if ($Environment -eq "prod") { "80" } else { "5000" }
        $webResponse = Invoke-WebRequest -Uri "http://localhost:$port/health" -TimeoutSec 5
        Write-Host "Web Interface: Healthy (Status: $($webResponse.StatusCode))" -ForegroundColor Green
    } catch {
        Write-Host "Web Interface: Unhealthy" -ForegroundColor Red
    }
}

function Open-Shell {
    $composeFile = Get-ComposeFile
    Write-Host "Opening shell in web interface container..." -ForegroundColor Blue
    docker-compose -f $composeFile exec kg-visualizer /bin/bash
}

function Start-Production {
    $Environment = "prod"
    Start-Services
}

# Main script logic
switch ($Command.ToLower()) {
    "start" { Start-Services }
    "stop" { Stop-Services }
    "restart" { Restart-Services }
    "build" { Build-Application }
    "rebuild" { Rebuild-Application }
    "logs" { Show-Logs }
    "logs-app" { Show-AppLogs }
    "logs-db" { Show-DbLogs }
    "clean" { Clean-All }
    "status" { Show-Status }
    "health" { Show-Health }
    "shell" { Open-Shell }
    "prod" { Start-Production }
    "help" { Show-Help }
    default { 
        Write-Host "Unknown command: $Command" -ForegroundColor Red
        Write-Host ""
        Show-Help 
    }
}
