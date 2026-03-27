# Dreame D20 Pro Plus MCP - backend only
# Use webapp\start.bat to start backend + frontend together.
# Ports: 10894 backend, 10895 frontend

$PORT = 10894

Write-Host "--- Dreame-MCP Backend ---" -ForegroundColor Cyan

$zombie = Get-NetTCPConnection -LocalPort $PORT -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
if ($zombie) {
    Write-Host "Clearing port $PORT (PID $($zombie.OwningProcess))..." -ForegroundColor Yellow
    Stop-Process -Id $zombie.OwningProcess -Force -ErrorAction SilentlyContinue
    Start-Sleep -Milliseconds 400
}

# $env:DREAME_USER     = "your@email.com"
# $env:DREAME_PASSWORD = "yourpassword"
# $env:DREAME_COUNTRY  = "eu"
# $env:DREAME_DID      = "2045852486"

Write-Host "Starting backend on port $PORT..." -ForegroundColor Green
Set-Location $PSScriptRoot
uv run python -m dreame_mcp --mode dual --port $PORT
