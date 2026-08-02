# Drishti local environment setup (Windows, CPU-only)
# Creates .venv with Python 3.12 and installs core dependencies.

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (Test-Path ".venv") {
    Write-Host ".venv already exists - skipping creation"
} else {
    if (Get-Command uv -ErrorAction SilentlyContinue) {
        Write-Host "Creating venv with uv (Python 3.12)..."
        uv venv -p 3.12 .venv
    } else {
        Write-Host "Creating venv with py launcher (Python 3.12)..."
        py -V:Astral/CPython3.12.13 -m venv .venv
        if (-not (Test-Path ".venv")) { py -3.12 -m venv .venv }
    }
}

Write-Host "Installing core requirements (CPU torch)..."
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt

Write-Host ""
Write-Host "Done. Activate with:  .\.venv\Scripts\Activate.ps1"
Write-Host "Python: $(& .\.venv\Scripts\python.exe --version)"
