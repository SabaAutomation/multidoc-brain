# One-click setup for Windows PowerShell. Run from inside the project folder:
#   powershell -ExecutionPolicy Bypass -File .\setup_and_run.ps1
# Optional: add -Answer to also test your local model (slow on a CPU).
param([switch]$Answer, [string]$Model = "qwen2.5-coder:7b")
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Test-Path .\venv)) { Write-Host "Creating virtual environment..." -ForegroundColor Cyan; python -m venv venv }
& .\venv\Scripts\python.exe -m pip install --quiet --upgrade pip
& .\venv\Scripts\python.exe -m pip install --quiet -r requirements.txt

Write-Host "`nSelf-test (no Ollama needed)..." -ForegroundColor Cyan
& .\venv\Scripts\python.exe selfcheck.py

Write-Host "`nRetrieval experiment (seconds)..." -ForegroundColor Cyan
& .\venv\Scripts\python.exe run_experiment.py

if ($Answer) {
  Write-Host "`nAsking the local model (resumable, press Ctrl+C any time and re-run to continue)..." -ForegroundColor Cyan
  & .\venv\Scripts\python.exe run_experiment.py --answer --model $Model
}

& .\venv\Scripts\python.exe make_report.py | Out-Null
& .\venv\Scripts\python.exe make_dashboard.py
Write-Host "`nDone. Opening the dashboard..." -ForegroundColor Green
Start-Process .\results\dashboard.html
