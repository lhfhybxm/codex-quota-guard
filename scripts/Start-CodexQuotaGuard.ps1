[CmdletBinding()]
param(
    [switch]$NoTray
)

$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$venvPython = Join-Path $projectRoot '.venv-win\Scripts\pythonw.exe'
$consolePython = Join-Path $projectRoot '.venv-win\Scripts\python.exe'

if (-not (Test-Path -LiteralPath $venvPython -PathType Leaf)) {
    throw 'Local environment not found. Run scripts\Setup.ps1 first.'
}

$arguments = @('-m', 'codex_quota_guard', '--start-hidden')
if ($NoTray) {
    $arguments = @('-m', 'codex_quota_guard', '--no-tray')
    & $consolePython @arguments
    exit $LASTEXITCODE
}

Start-Process -FilePath $venvPython -ArgumentList $arguments -WorkingDirectory $projectRoot -WindowStyle Hidden
