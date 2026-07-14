$p = Start-Process -FilePath "D:\Dev\repos\dreame-mcp\.venv\Scripts\python.exe" -ArgumentList "-m","dreame_mcp","--mode","dual","--port","10794" -WindowStyle Hidden -PassThru -WorkingDirectory "D:\Dev\repos\dreame-mcp"
$p.Id | Out-File "D:\Dev\repos\dreame-mcp\server_bg.pid" -Force
Write-Host $p.Id
