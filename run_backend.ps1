Set-Location -Path "$PSScriptRoot\backend"
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host " Starting AI Document Summarization Backend (FastAPI)" -ForegroundColor Cyan
Write-Host " API URL:  http://localhost:8000" -ForegroundColor Green
Write-Host " API Docs: http://localhost:8000/docs" -ForegroundColor Green
Write-Host "========================================================" -ForegroundColor Cyan
& ".\.venv\Scripts\python.exe" -m uvicorn app.main:app --reload --port 8000

