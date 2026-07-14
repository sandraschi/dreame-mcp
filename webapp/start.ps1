param(
    [switch]$Headless,
    [switch]$BackendOnly,
    [switch]$NoBrowser,
    [switch]$ReuseIfRunning)

$BackendPort = 10894
$FrontendPort = 10895
$WebappDir = $PSScriptRoot
$ProjectRoot = Split-Path -Parent $WebappDir

$FleetStartPath = Join-Path $ProjectRoot "scripts\FleetStartMode.ps1"
if (-not (Test-Path -LiteralPath $FleetStartPath)) {
    Write-Host "ERROR: Missing vendored launcher helper: $FleetStartPath" -ForegroundColor Red
    exit 1
}
. $FleetStartPath
$FleetStart = Initialize-FleetStartMode @PSBoundParameters
Enter-FleetHeadlessConsole -Headless:$Headless -BackendOnly:$BackendOnly

$portResolve = @{
    Ports      = @($BackendPort, $FrontendPort)
    Label      = "dreame-mcp"
    AllowReuse = $ReuseIfRunning
}
if ($ReuseIfRunning) {
    $portResolve.HealthChecks = @{
        $BackendPort = "http://127.0.0.1:$BackendPort/api/v1/health"
        $FrontendPort = "http://127.0.0.1:$FrontendPort/"
    }
}
$portState = Resolve-FleetPortConflict @portResolve
if ($portState.Action -eq 'Blocked') { exit 1 }
if ($portState.Reuse) { return }

foreach ($envPath in @((Join-Path $ProjectRoot ".env"), (Join-Path $WebappDir ".env"))) {
    if (-not (Test-Path $envPath)) { continue }
    Get-Content $envPath | ForEach-Object {
        $line = $_.Trim()
        if ($line -and -not $line.StartsWith("#") -and $line -match "^([^=]+)=(.*)$") {
            $name = $matches[1].Trim()
            $val = $matches[2].Trim().Trim('"').Trim("'")
            if ($val) { Set-Item -Path "Env:$name" -Value $val }
        }
    }
    break
}

if (-not $env:DREAME_COUNTRY) { $env:DREAME_COUNTRY = "eu" }
$env:DREAME_MCP_HOST = "127.0.0.1"

Write-Host "[dreame-mcp] Starting backend on $BackendPort ..." -ForegroundColor Cyan
$backendCmd = "Set-Location '$ProjectRoot'; `$env:DREAME_MCP_HOST='127.0.0.1'; uv run --project '$ProjectRoot' python -m dreame_mcp --mode dual --port $BackendPort"
Start-Process powershell -ArgumentList "-NoProfile", "-WindowStyle", "Normal", "-Command", $backendCmd

$healthUrl = "http://127.0.0.1:$BackendPort/api/v1/health"
$attempt = 0
while ($attempt -lt 60) {
    try {
        $null = Invoke-WebRequest -Uri $healthUrl -UseBasicParsing -TimeoutSec 3 -ErrorAction Stop
        Write-Host "Backend ready at $healthUrl" -ForegroundColor Green
        break
    } catch {
        Start-Sleep -Seconds 2
        $attempt++
    }
}

if (-not $FleetStart.RunFrontend) {
    while ($true) { Start-Sleep -Seconds 60 }
}

Set-Location $WebappDir
if (-not (Test-Path "node_modules")) { npm install }

if (-not $NoBrowser) {
    $frontendUrl = "http://127.0.0.1:$FrontendPort/"
    $pollAndOpen = "for (`$i = 0; `$i -lt 60; `$i++) { try { `$null = Invoke-WebRequest -Uri '$frontendUrl' -TimeoutSec 2 -UseBasicParsing -ErrorAction Stop; Start-Process '$frontendUrl'; exit } catch { Start-Sleep -Seconds 1 } }"
    Start-Process powershell -ArgumentList "-NoProfile", "-WindowStyle", "Hidden", "-Command", $pollAndOpen
}

Write-Host "[dreame-mcp] Starting Vite on $FrontendPort ..." -ForegroundColor Green
npm run dev -- --host 127.0.0.1 --port $FrontendPort --strictPort


