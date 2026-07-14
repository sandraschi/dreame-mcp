$root = "D:\Dev\repos\dreame-mcp"
$p = Start-Process -FilePath "$root\.venv\Scripts\python.exe" -ArgumentList "-m", "dreame_mcp", "--mode", "dual", "--port", "10794" -NoNewWindow -PassThru -WorkingDirectory $root
Write-Host "PID=$($p.Id)"
$p.Id | Out-File "$root\server_pid.txt" -Force
