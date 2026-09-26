$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
if (!(Test-Path '.venv/Scripts/python.exe')) { py -3 -m venv .venv }
& '.venv/Scripts/python.exe' -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed' }
if (!(Test-Path 'frontend/dist/index.html')) {
    Push-Location frontend
    npm.cmd ci
    npm.cmd run build
    if ($LASTEXITCODE -ne 0) { throw 'Frontend build failed' }
    Pop-Location
}
& '.venv/Scripts/python.exe' -m scripts.bootstrap
Write-Host 'Open http://127.0.0.1:8000 and choose Try interactive demo or Create an account. No separate simulator needed.'
& '.venv/Scripts/python.exe' -m uvicorn backend.app:app --host 127.0.0.1 --port 8000
