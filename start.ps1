# Dreame D20 Pro Plus MCP - backend only
# Use webapp\start.bat to start backend + frontend together.
# Ports: 10794 backend, 10895 frontend

$PORT = 10794

Write-Host "--- Dreame-MCP Backend ---" -ForegroundColor Cyan

$zombie = Get-NetTCPConnection -LocalPort $PORT -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
if ($zombie) {
    Write-Host "Clearing port $PORT (PID $($zombie.OwningProcess))..." -ForegroundColor Yellow
    Stop-Process -Id $zombie.OwningProcess -Force -ErrorAction SilentlyContinue
    Start-Sleep -Milliseconds 400
}

# --- Robust .env Loading ---
$envPath = $null
$potentialPaths = @(
    (Join-Path $PSScriptRoot ".env"),           # Script Directory
    (Join-Path (Get-Location) ".env")           # Current Working Directory
)

foreach ($p in $potentialPaths) {
    if (Test-Path $p) {
        $envPath = (Resolve-Path $p).Path
        break
    }
}

if ($envPath) {
    Write-Host "[DREAME-MCP] Loading .env from: $envPath" -ForegroundColor Gray
    foreach ($line in Get-Content $envPath) {
        $line = $line.Trim()
        if ($line -and -not $line.StartsWith("#") -and $line -match "^([^=]+)=(.*)$") {
            $name = $matches[1].Trim()
            $val  = $matches[2].Trim()
            # Remove quotes if present
            $val = $val -replace "^['""]|['""]$", ""
            if ($val) {
                Set-Item -Path "Env:$name" -Value $val
            }
        }
    }
} else {
    Write-Host "[DREAME-MCP] No .env found in potential paths." -ForegroundColor DarkGray
}

# $env:DREAME_USER     = "your@email.com"
# $env:DREAME_PASSWORD = "yourpassword"
# $env:DREAME_COUNTRY  = "eu"
# $env:DREAME_DID      = "2045852486"

Write-Host "Starting backend on port $PORT..." -ForegroundColor Green
Set-Location $PSScriptRoot
uv run python -m dreame_mcp --mode dual --port $PORT
