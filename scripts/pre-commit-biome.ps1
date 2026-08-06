# Runs Biome on the webapp when it exists (called by the local pre-commit hook).
# Detects webapp/, web_sota/, webapp/frontend/, or web/ and runs `biome check --write`.
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot

$candidates = @("webapp", "web_sota", "webapp/frontend", "web")
$webRoot = $null
foreach ($c in $candidates) {
    if (Test-Path (Join-Path $Root "$c\package.json")) {
        $webRoot = Join-Path $Root $c
        break
    }
}
if (-not $webRoot) {
    exit 0
}

Push-Location $webRoot
try {
    if (Test-Path "node_modules\.bin\biome.cmd") {
        & "node_modules\.bin\biome.cmd" check --write . 2>&1
        if ($LASTEXITCODE -ne 0) {
            Write-Host "Biome failed - run 'npm run fix' in $webRoot" -ForegroundColor Red
            exit $LASTEXITCODE
        }
    }
    else {
        npx biome check --write . 2>&1
        if ($LASTEXITCODE -ne 0) {
            Write-Host "Biome failed - run 'npm run fix' in $webRoot" -ForegroundColor Red
            exit $LASTEXITCODE
        }
    }
}
finally {
    Pop-Location
}
exit 0
