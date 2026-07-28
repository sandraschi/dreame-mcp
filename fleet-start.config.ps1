# Per-repo fleet start config for dreame-mcp
# Edit ports/backend target here - start.ps1 is fleet-standard.
@{
    Name         = 'dreame-mcp'
    BackendPort  = 10894
    FrontendPort = 10895
    HealthPath   = '/api/v1/health'
    WebRoot      = 'D:\Dev\repos\dreame-mcp\webapp'
    Backend = @{
        Kind          = 'uvicorn'
        UvicornTarget = 'dreame_mcp.server:app'
        Env           = @{ WEB_PORT = '10894' }
    }
    Frontend = @{
        Kind           = 'vite-npm'
        PackageManager = 'npm'
        PortEnvVar     = 'VITE_PORT'
        ApiTargetEnv   = 'VITE_API_TARGET'
    }
}
