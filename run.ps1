# Karnataka Tourism AI Guide PowerShell Launcher
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host " Starting Karnataka Tourism Smart AI Guide Platform" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan

# 1. MySQL Service Check
$mysqlService = Get-Service -Name "MySQL80" -ErrorAction SilentlyContinue
if ($mysqlService -and $mysqlService.Status -ne "Running") {
    Write-Host "[INFO] Starting MySQL80 service..." -ForegroundColor Yellow
    Start-Service -Name "MySQL80"
} else {
    Write-Host "[OK] MySQL80 service is active." -ForegroundColor Green
}

# 2. Ollama Check
$ollamaProc = Get-Process -Name "ollama" -ErrorAction SilentlyContinue
if (-not $ollamaProc) {
    Write-Host "[INFO] Starting Ollama in the background..." -ForegroundColor Yellow
    Start-Process "ollama" -ArgumentList "serve" -WindowStyle Hidden
} else {
    Write-Host "[OK] Ollama service is active." -ForegroundColor Green
}

# 3. Launch Backend & Frontend
Write-Host "[INFO] Starting Backend and Frontend processes..." -ForegroundColor Cyan

Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$PSScriptRoot'; `$host.UI.RawUI.WindowTitle = 'Backend Server'; & '$PSScriptRoot\backend\.venv\Scripts\python.exe' -m uvicorn backend.src.main:app --host 127.0.0.1 --port 8000"

Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$PSScriptRoot\frontend'; `$host.UI.RawUI.WindowTitle = 'Frontend UI'; npm run dev"

Write-Host ""
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "Both servers launched successfully!" -ForegroundColor Green
Write-Host "  * Frontend UI:   http://127.0.0.1:3000" -ForegroundColor White
Write-Host "  * Backend API:   http://127.0.0.1:8000" -ForegroundColor White
Write-Host "  * Swagger Docs:  http://127.0.0.1:8000/docs" -ForegroundColor White
Write-Host "  * Admin Login:   admin / AdminPassword123!" -ForegroundColor White
Write-Host "======================================================================" -ForegroundColor Cyan

Start-Sleep -Seconds 4
Start-Process "http://127.0.0.1:3000"
