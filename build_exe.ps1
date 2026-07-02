$ErrorActionPreference = "Stop"
Write-Host "Building PlanPracy application"

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "Python was not found in PATH."
    exit 1
}

if (Test-Path build) { Remove-Item build -Recurse -Force }
if (Test-Path dist) { Remove-Item dist -Recurse -Force }

python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install --upgrade cryptography
python -m PyInstaller --clean --noconfirm plan_pracy.spec

Write-Host "Done. EXE file: dist\PlanPracy\PlanPracy.exe"
Read-Host "Press Enter to exit"
