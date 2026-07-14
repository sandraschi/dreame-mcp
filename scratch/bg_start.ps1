$root = "D:\Dev\repos\dreame-mcp"
$p = Start-Process -FilePath "$root\.venv\Scripts\python.exe" -ArgumentList "-m", "dreame_mcp", "--mode", "dual", "--port", "10794" -WindowStyle Hidden -PassThru -WorkingDirectory $root
$p.Id | Out-File "$root\server_bg.pid" -Force
Write-Host "Server PID=$($p.Id)"
