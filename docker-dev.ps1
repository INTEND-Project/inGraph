# PowerShell script for Docker development commands

param(
    [Parameter(Mandatory=$true)]
    [ValidateSet("up", "down", "build", "logs", "restart", "status")]
    [string]$Action
)

switch ($Action) {
    "up" {
        Write-Host "Starting development environment..." -ForegroundColor Green
        docker-compose up -d
        Write-Host "Services started!" -ForegroundColor Green
        Write-Host "GraphDB: http://localhost:7200" -ForegroundColor Cyan
        Write-Host "Flask App: http://localhost:5000" -ForegroundColor Cyan
        Write-Host "Health Check: http://localhost:5000/health" -ForegroundColor Cyan
    }
    "down" {
        Write-Host "Stopping development environment..." -ForegroundColor Yellow
        docker-compose down
        Write-Host "Services stopped!" -ForegroundColor Green
    }
    "build" {
        Write-Host "Building application container..." -ForegroundColor Blue
        docker-compose build app
        Write-Host "Build complete!" -ForegroundColor Green
    }
    "logs" {
        Write-Host "Showing logs..." -ForegroundColor Blue
        docker-compose logs -f
    }
    "restart" {
        Write-Host "Restarting services..." -ForegroundColor Yellow
        docker-compose restart
        Write-Host "Services restarted!" -ForegroundColor Green
    }
    "status" {
        Write-Host "Service status:" -ForegroundColor Blue
        docker-compose ps
    }
}
