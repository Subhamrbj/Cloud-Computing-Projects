$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
if (!(Test-Path '.venv/Scripts/python.exe')) { py -3.12 -m venv .venv }
& '.venv/Scripts/python.exe' -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed' }
if (!(Test-Path 'frontend/dist/index.html')) {
    Push-Location frontend
    npm.cmd ci
    npm.cmd run build
    if ($LASTEXITCODE -ne 0) { throw 'Frontend build failed' }
    Pop-Location
}
& '.venv/Scripts/python.exe' -m scripts.setup_demo
Write-Host 'Your generated login is in .demo-credentials.json. In another terminal run the simulator command from README.'
& '.venv/Scripts/python.exe' -m uvicorn backend.app:app --host 127.0.0.1 --port 8000
