# ============================================================
# SCRIPT D'INSTALLATION — PC DU BUREAU
# Copier ce fichier sur le PC du bureau et lancer :
#   powershell -ExecutionPolicy Bypass -File setup_pc_bureau.ps1
# ============================================================

Write-Host "=== Installation Facture-IA ===" -ForegroundColor Cyan

# 1. Supprime l'ancien dossier
Write-Host "`n[1/7] Suppression ancien dossier..." -ForegroundColor Yellow
Remove-Item -Recurse -Force "C:\Users\SOFIENE\Desktop\facture-ia-main" -ErrorAction SilentlyContinue

# 2. Installe Python 3.11
Write-Host "`n[2/7] Installation Python 3.11..." -ForegroundColor Yellow
winget install Python.Python.3.11 --accept-source-agreements --accept-package-agreements

# 3. Installe Git
Write-Host "`n[3/7] Installation Git..." -ForegroundColor Yellow
winget install Git.Git --accept-source-agreements --accept-package-agreements

# 4. Refresh PATH
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")

# 5. Clone le repo
Write-Host "`n[4/7] Clonage du depot..." -ForegroundColor Yellow
cd "C:\Users\SOFIENE\Desktop"
git clone https://github.com/MaleBenAttia/facture-ia.git facture-ia-main

# 6. Crée le venv avec Python 3.11
Write-Host "`n[5/7] Creation du venv Python 3.11..." -ForegroundColor Yellow
cd facture-ia-main
& "C:\Python311\python.exe" -m venv venv 2>$null
if ($LASTEXITCODE -ne 0) {
    py -3.11 -m venv venv
}

# 7. Installe les dépendances
Write-Host "`n[6/7] Installation des dependances..." -ForegroundColor Yellow
& ".\venv\Scripts\activate"
pip install -r requirements.txt

# 8. Frontend
Write-Host "`n[7/7] Installation du frontend..." -ForegroundColor Yellow
cd frontend
npm install
npm run build
cd ..

Write-Host "`n=== Installation terminee ! ===" -ForegroundColor Green
Write-Host "Lance l'application avec : start.bat" -ForegroundColor Green
