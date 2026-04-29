# Export Project Data for Transfer
$VENV_PATH = ".venv"

if (!(Test-Path $VENV_PATH)) {
    Write-Host "[!] Virtual environment not found. Please run setup.ps1 first." -ForegroundColor Red
    exit
}

Write-Host "[+] Exporting database data to data.json..." -ForegroundColor Cyan
& ".\$VENV_PATH\Scripts\python.exe" export_helper.py

if (Test-Path "data.json") {
    Write-Host "[+] Success! data.json created." -ForegroundColor Green
    Write-Host "[+] You can now zip the project (including data.json) and move it to the new laptop." -ForegroundColor Green
} else {
    Write-Host "[!] Failed to create data.json." -ForegroundColor Red
}
