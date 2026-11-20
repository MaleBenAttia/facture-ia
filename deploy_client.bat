@echo off
rem Facture-IA - Deployment simple pour client (Windows)
rem 1. Clonage depuis git (dossier "facture-ia")
rem 2. Venv + dependances Python
rem 3. npm install + npm run build (frontend)
rem 4. Creation du .env vide
rem 5. Commande pour lancer le serveur : cd facture-ia && venv\Scripts\python.exe -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload

setlocal enabledelayedexpansion
set "REPO_URL=https://github.com/MaleBenAttia/facture-ia.git"
set "TARGET_DIR=facture-ia"

echo [1/5] Clonage depuis git...
git clone --quiet %REPO_URL% %TARGET_DIR%
if not exist %TARGET_DIR%\main.py (echo ERREUR: clone impossible; pause; exit /b 1)
cd %TARGET_DIR%

echo [2/5] Creation du venv...
python -m venv venv

echo [3/5] Installation des dependances Python...
venv\Scripts\pip install -r requirements.txt --quiet

echo [4/5] Installation et build du frontend...
cd frontend
npm install
npm run build
cd ..

echo [5/5] Creation du .env vide...
if not exist .env type nul > .env

echo.
echo ==========================================
echo Deploy termine ! Pour lancer le serveur :
echo   cd facture-ia
echo   venv\Scripts\python.exe -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
echo ==========================================
pause
