set windows-shell := ["powershell.exe", "-NoProfile", "-Command"]
import 'scripts/just/fleet.just'

# ── Dashboard ─────────────────────────────────────────────────────────────────

# Open the interactive recipe dashboard in the browser
default:
    @just --list

# ── Quality ───────────────────────────────────────────────────────────────────

# Execute Ruff (Python) and Biome (Webapp) SOTA v14.1 linting
lint:
    uv run ruff check .
    cd webapp; npm run lint

# Execute Ruff and Biome SOTA v14.1 fix and formatting
fix:
    uv run ruff check . --fix --unsafe-fixes
    uv run ruff format .
    cd webapp; npm run fix

# ── Hardening ─────────────────────────────────────────────────────────────────

# Execute Bandit security audit
check-sec:
    Set-Location '{{justfile_directory()}}'
    uv run bandit -r src/

# Execute safety audit of dependencies
audit-deps:
    Set-Location '{{justfile_directory()}}'
    uv run safety check

# ── Testing ───────────────────────────────────────────────────────────────────

# Run e2e Playwright tests
e2e:
    powershell.exe -NoProfile -NoProfile -ExecutionPolicy Bypass -File "D:\Dev\repos\mcp-central-docs\scripts\playwright-audit.ps1" -RepoPath "{{justfile_directory()}}"

# ── Operations ────────────────────────────────────────────────────────────────

# Extract DID and miIO Tokens from DreameHome Cloud
extract-tokens:
    uv run python scripts/extract_tokens.py

# Launch the hybrid MCP bridge (Local + Cloud)
start-hybrid:
    uv run python -m dreame_mcp --mode dual --port 10794

# Perform a raw UDP discovery probe to check vacuum responsiveness
check-discovery:
	uv run python -m miio discover

# ── Native (Tauri) ──────────────────────────────────────────────────────────

# Build the Tauri NSIS desktop installer (full pipeline: frontend -> Rust -> NSIS)
build-native:
	$env:Path = "$env:USERPROFILE\.cargo\bin;$env:Path"
	Set-Location '{{justfile_directory()}}\native'
	npx @tauri-apps/cli build --bundles nsis

