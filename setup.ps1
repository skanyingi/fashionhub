# Project Setup for Windows
$VENV_PATH = ".venv"

if (!(Test-Path $VENV_PATH)) {
    Write-Host "[+] Creating virtual environment..." -ForegroundColor Cyan
    python -m venv $VENV_PATH
}

Write-Host "[+] Running setup script..." -ForegroundColor Cyan
& ".\$VENV_PATH\Scripts\python.exe" setup_project.py

Write-Host "[+] Setup complete! To start the server, run:" -ForegroundColor Green
Write-Host ".\$VENV_PATH\Scripts\activate"
Write-Host "python manage.py runserver"
