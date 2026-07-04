@echo off
cd /d "%~dp0"

echo ========================================
echo   Lancement de Facture-IA
echo ========================================
echo.

call venv\Scripts\activate

echo [1/2] Demarrage du backend (port 8000)...
start "Backend Facture-IA" cmd /k "uvicorn main:app --reload --port 8000"

timeout /t 3 /nobreak >nul

echo [2/2] Demarrage du frontend (port 5173)...
cd frontend
start "Frontend Facture-IA" cmd /k "npm run dev"

echo.
echo ========================================
echo   Backend  : http://localhost:8000
echo   Frontend : http://localhost:5173
echo ========================================
echo.
pause
