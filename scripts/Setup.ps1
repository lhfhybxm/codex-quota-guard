[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$venvPath = Join-Path $projectRoot '.venv-win'
$venvPython = Join-Path $venvPath 'Scripts\python.exe'

if (-not (Test-Path -LiteralPath $venvPython -PathType Leaf)) {
    $pythonLauncher = Get-Command 'py.exe' -ErrorAction SilentlyContinue
    if ($null -eq $pythonLauncher) {
        throw 'Python Launcher for Windows was not found. Install CPython 3.11 from python.org.'
    }
    & $pythonLauncher.Source -3.11 -m venv $venvPath
    if ($LASTEXITCODE -ne 0) {
        throw 'Unable to create .venv-win with CPython 3.11.'
    }
}

& $venvPython -m pip install -e "$projectRoot[dev]"
if ($LASTEXITCODE -ne 0) { throw "Dependency setup failed with exit code $LASTEXITCODE" }
Write-Host 'Setup complete. Start with scripts\Start-CodexQuotaGuard.ps1'
