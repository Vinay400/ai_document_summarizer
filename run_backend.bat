@echo off
cd /d "%~dp0backend"
echo ========================================================
echo  Starting AI Document Summarization Backend (FastAPI)
echo  API URL:  http://localhost:8000
echo  API Docs: http://localhost:8000/docs
echo ========================================================
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
pause

