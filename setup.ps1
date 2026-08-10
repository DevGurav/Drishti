# Drishti local environment setup (Windows, CPU-only)
# Creates .venv with Python 3.12 and installs core dependencies.
#
# Python 3.12 rather than the system 3.14: parts of the ML stack still have no 3.14 wheels.

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$hasUv = [bool](Get-Command uv -ErrorAction SilentlyContinue)
$py = ".\.venv\Scripts\python.exe"

if (Test-Path ".venv") {
    Write-Host ".venv already exists - skipping creation"
} elseif ($hasUv) {
    Write-Host "Creating venv with uv (Python 3.12)..."
    # --seed installs pip into the venv. Without it `uv venv` produces an environment
    # with no pip at all, and `python -m pip install` then fails with "No module named
    # pip" while the script carries on and reports success -- which is exactly what
    # happened on 2026-08-10, leaving an empty venv that looked installed.
    uv venv --seed -p 3.12 .venv
} else {
    Write-Host "Creating venv with py launcher (Python 3.12)..."
    py -V:Astral/CPython3.12.13 -m venv .venv
    if (-not (Test-Path ".venv")) { py -3.12 -m venv .venv }
}

Write-Host "Installing core requirements (CPU torch)..."
if ($hasUv) {
    # uv resolves and downloads far faster, and needs no pip inside the venv.
    uv pip install --python $py -r requirements.txt
} else {
    & $py -m pip install --upgrade pip
    & $py -m pip install -r requirements.txt
}
if ($LASTEXITCODE -ne 0) { throw "dependency installation failed (exit $LASTEXITCODE)" }

# Verify rather than assume. A setup script that prints "Done" over a failed install is
# worse than one that crashes: the failure resurfaces later as a ModuleNotFoundError in
# whatever you were actually trying to do.
Write-Host "Verifying imports..."
$check = @'
import importlib.util, sys   # importlib alone does not expose .util
required = ['torch', 'torchvision', 'PIL', 'numpy', 'flask', 'transformers', 'accelerate']
missing = [m for m in required if importlib.util.find_spec(m) is None]
if missing:
    print('MISSING: ' + ', '.join(missing))
    sys.exit(1)
import torch, torchvision
print(f'torch {torch.__version__} · torchvision {torchvision.__version__}')
'@
& $py -c $check
if ($LASTEXITCODE -ne 0) { throw "install completed but required packages are missing" }

Write-Host ""
Write-Host "Done. Activate with:  .\.venv\Scripts\Activate.ps1"
Write-Host "Python: $(& $py --version)"
Write-Host ""
Write-Host "Staged engine installs (each pulls models on first use):"
Write-Host "  OCR    : uv pip install --python $py paddlepaddle paddleocr"
Write-Host "  Speech : uv pip install --python $py IndicTransToolkit"
