Param([switch]$Headless)

# --- SOTA Headless Standard ---
if ($Headless -and ($Host.UI.RawUI.WindowTitle -notmatch 'Hidden')) {
    Start-Process pwsh -ArgumentList '-NoProfile', '-File', $PSCommandPath, '-Headless' -WindowStyle Hidden
    exit
}
$WindowStyle = if ($Headless) { 'Hidden' } else { 'Normal' }
# ------------------------------

# Dreame D20 Pro Plus MCP - backend + webapp startup
# Ports: 10794 backend (MCP SSE + REST), 10895 frontend (Vite)
# Requires: Windows PowerShell 5.1+, uv, Node/npm

$APP_PORT    = 10794
$WEBAPP_PORT = 10795
$WEBAPP_DIR  = if ($PSScriptRoot) { $PSScriptRoot } else { Split-Path -Parent $MyInvocation.MyCommand.Path }
$ROOT_DIR    = Split-Path -Parent $WEBAPP_DIR
$TEMP_DIR    = "D:\Dev\repos\temp"
$serverProc    = $null
$dashboardProc = $null

function Stop-Tracked {
    if ($serverProc    -and -not $serverProc.HasExited)    { Stop-Process -Id $serverProc.Id    -Force -ErrorAction SilentlyContinue }
    if ($dashboardProc -and -not $dashboardProc.HasExited) { Stop-Process -Id $dashboardProc.Id -Force -ErrorAction SilentlyContinue }
}

try {
    Write-Host "[DREAME-MCP] Webapp : $WEBAPP_DIR" -ForegroundColor DarkGray
    Write-Host "[DREAME-MCP] Root   : $ROOT_DIR"   -ForegroundColor DarkGray

    # --- Robust .env Loading ---
    $envPath = $null
    $potentialPaths = @(
        (Join-Path $WEBAPP_DIR ".env"),             # Local to script
        (Join-Path $ROOT_DIR ".env"),               # Root of repo
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

    # Refresh PATH - critical when launched from .bat without full shell env
    $env:PATH = [System.Environment]::GetEnvironmentVariable("PATH","Machine") + ";" +
                [System.Environment]::GetEnvironmentVariable("PATH","User")

    # --- Locate uv ---
    $uvCmd = Get-Command "uv.exe" -ErrorAction SilentlyContinue
    $uvExe = if ($uvCmd) { $uvCmd.Source } else { "D:\Dev\repos\uv-install\uv.exe" }
    if (-not (Test-Path $uvExe)) {
        Write-Host "[ERROR] uv.exe not found. Checked PATH and D:\Dev\repos\uv-install\uv.exe" -ForegroundColor Red
        Read-Host "Press Enter to close"
        exit 1
    }
    Write-Host "[DREAME-MCP] uv  : $uvExe" -ForegroundColor DarkGray

    # --- Locate npm ---
    $npmCmd = Get-Command "npm.cmd" -ErrorAction SilentlyContinue
    $npmExe = if ($npmCmd) { $npmCmd.Source } else { "npm.cmd" }
    Write-Host "[DREAME-MCP] npm : $npmExe" -ForegroundColor DarkGray

    # --- Port safety ---
    Write-Host "[DREAME-MCP] Port safety..." -ForegroundColor Cyan
    foreach ($p in @($APP_PORT, $WEBAPP_PORT)) {
        $conns = Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue
        if ($conns) {
            $ownerPids = $conns | Select-Object -ExpandProperty OwningProcess -Unique
            foreach ($ownerPid in $ownerPids) {
                if ($ownerPid -and $ownerPid -ne 0) {
                    Stop-Process -Id $ownerPid -Force -ErrorAction SilentlyContinue
                    Write-Host "  Port $p killed PID $ownerPid" -ForegroundColor Yellow
                }
            }
            Start-Sleep -Milliseconds 400
        } else {
            Write-Host "  Port $p clean" -ForegroundColor Green
        }
    }

    # --- Python deps (blocking) ---
    Write-Host "[DREAME-MCP] Syncing Python deps..." -ForegroundColor Cyan
    $ts    = Get-Date -Format 'HHmmss'
    $uvOut = "$TEMP_DIR\dreame_uv_out_$ts.txt"
    $uvErr = "$TEMP_DIR\dreame_uv_err_$ts.txt"
    Start-Process -FilePath $uvExe `
        -ArgumentList "sync" `
        -WorkingDirectory $ROOT_DIR `
        -NoNewWindow -Wait `
        -RedirectStandardOutput $uvOut `
        -RedirectStandardError  $uvErr
    if (Test-Path $uvOut) { Remove-Item $uvOut -Force -ErrorAction SilentlyContinue }
    if (Test-Path $uvErr) { Remove-Item $uvErr -Force -ErrorAction SilentlyContinue }
    Write-Host "  Python deps OK" -ForegroundColor Green

    # --- npm ci (blocking, only if node_modules missing) ---
    Write-Host "[DREAME-MCP] Checking node_modules..." -ForegroundColor Cyan
    if (-not (Test-Path "$WEBAPP_DIR\node_modules")) {
        Write-Host "  node_modules missing - npm install (~60s, please wait)..." -ForegroundColor Yellow
        $ts2     = Get-Date -Format 'HHmmss'
        $npmOut  = "$TEMP_DIR\dreame_npm_out_$ts2.txt"
        $npmErr  = "$TEMP_DIR\dreame_npm_err_$ts2.txt"
        Start-Process -FilePath "cmd.exe" `
            -ArgumentList "/c", "`"$npmExe`" install --legacy-peer-deps" `
            -WorkingDirectory $WEBAPP_DIR `
            -NoNewWindow -Wait `
            -RedirectStandardOutput $npmOut `
            -RedirectStandardError  $npmErr
        # Verify by checking node_modules was actually created
        if (-not (Test-Path "$WEBAPP_DIR\node_modules")) {
            Write-Host "[ERROR] npm install failed - node_modules still missing." -ForegroundColor Red
            if (Test-Path $npmErr) { Get-Content $npmErr | Select-Object -Last 20 | ForEach-Object { Write-Host $_ -ForegroundColor DarkRed } }
            if (Test-Path $npmOut) { Get-Content $npmOut | Select-Object -Last 10 | ForEach-Object { Write-Host $_ -ForegroundColor DarkYellow } }
            if (Test-Path $npmErr) { Remove-Item $npmErr -Force -ErrorAction SilentlyContinue }
            if (Test-Path $npmOut) { Remove-Item $npmOut -Force -ErrorAction SilentlyContinue }
            Read-Host "Press Enter to close"
            exit 1
        }
        if (Test-Path $npmErr) { Remove-Item $npmErr -Force -ErrorAction SilentlyContinue }
        if (Test-Path $npmOut) { Remove-Item $npmOut -Force -ErrorAction SilentlyContinue }
        Write-Host "  npm ci complete." -ForegroundColor Green
    } else {
        Write-Host "  node_modules present." -ForegroundColor Green
    }

    # Credentials - only set if not already in environment
    if (-not $env:DREAME_USER)     { Write-Host "[WARNING] DREAME_USER not set." -ForegroundColor Yellow }
    if (-not $env:DREAME_PASSWORD) { Write-Host "[WARNING] DREAME_PASSWORD not set." -ForegroundColor Yellow }
    if (-not $env:DREAME_COUNTRY)  { $env:DREAME_COUNTRY  = "eu" }
    if (-not $env:DREAME_DID)      { Write-Host "[INFO] DREAME_DID not set - using auto-discovery." -ForegroundColor Cyan }

    # --- Backend (async) ---
    Write-Host "[DREAME-MCP] Starting backend on $APP_PORT..." -ForegroundColor Green
    $serverProc = Start-Process -FilePath $uvExe `
        -ArgumentList "run","python","-m","dreame_mcp","--mode","dual","--port","$APP_PORT" `
        -WorkingDirectory $ROOT_DIR -NoNewWindow -PassThru
    Start-Sleep -Seconds 3
    if ($serverProc.HasExited) {
        Write-Host "[WARNING] Backend exited immediately. Check DREAME_USER + DREAME_PASSWORD." -ForegroundColor Yellow
    } else {
        Write-Host "  Backend PID $($serverProc.Id) running." -ForegroundColor Green
    }

    # --- Vite (async) ---
    Write-Host "[DREAME-MCP] Starting Vite on $WEBAPP_PORT..." -ForegroundColor Green
    $dashboardProc = Start-Process -FilePath "cmd.exe" `
        -ArgumentList "/c", "`"$npmExe`" run dev" `
        -WorkingDirectory $WEBAPP_DIR -NoNewWindow -PassThru
    Start-Sleep -Seconds 4

    Write-Host ""
    Write-Host "[SUCCESS] Dreame D20 Pro Plus MCP active." -ForegroundColor Green
    Write-Host "  Backend  : http://localhost:$APP_PORT"
    Write-Host "  Dashboard: http://localhost:$WEBAPP_PORT"
    Write-Host "  Health   : http://localhost:$APP_PORT/api/v1/health"
    Write-Host "  Swagger  : http://localhost:$APP_PORT/docs"
    Write-Host "  MCP      : { url: 'http://localhost:$APP_PORT/sse', transport: 'sse' }"
    Write-Host ""
    Write-Host "Press Ctrl+C to stop."

# 4b. Launch background task to open browser once frontend is ready (Auto-opened by Antigravity)
$frontendUrl = "http://127.0.0.1:$WEBAPP_PORT/"
$pollAndOpen = "for (`$i = 0; `$i -lt 60; `$i++) { try { `$null = Invoke-WebRequest -Uri '$frontendUrl' -TimeoutSec 2 -UseBasicParsing -ErrorAction Stop; Start-Process '$frontendUrl'; exit } catch { Start-Sleep -Seconds 1 } }"
Start-Process powershell -ArgumentList "-NoProfile", "-WindowStyle", "Hidden", "-Command", $pollAndOpen


    while ($true) { Start-Sleep -Seconds 1 }

} catch {
    Write-Host ""
    Write-Host "[FATAL] $_" -ForegroundColor Red
    Write-Host $_.ScriptStackTrace -ForegroundColor DarkRed
    Read-Host "Press Enter to close"
} finally {
    Stop-Tracked
    Write-Host "[DONE] Dreame MCP stopped." -ForegroundColor Green
}



