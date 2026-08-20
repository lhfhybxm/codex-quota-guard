[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$venvPython = Join-Path $projectRoot '.venv-win\Scripts\python.exe'

if (-not (Test-Path -LiteralPath $venvPython -PathType Leaf)) {
    throw 'Local environment not found. Run scripts\Setup.ps1 first.'
}

Push-Location $projectRoot
try {
    $buildTag = Get-Date -Format 'yyyyMMdd-HHmmss'
    $artifactRoot = Join-Path $projectRoot 'artifacts'
    if (-not (Test-Path -LiteralPath $artifactRoot -PathType Container)) {
        New-Item -ItemType Directory -Path $artifactRoot -ErrorAction Stop | Out-Null
    }
    $pytestTemp = Join-Path $artifactRoot "pytest-$buildTag"
    & $venvPython -m pytest --basetemp $pytestTemp
    if ($LASTEXITCODE -ne 0) { throw "Tests failed with exit code $LASTEXITCODE" }
    $distPath = Join-Path $projectRoot "publish\$buildTag"
    $workPath = Join-Path $projectRoot "build\work-$buildTag"
    $specPath = Join-Path $projectRoot "build\spec-$buildTag"
    $sourcePath = Join-Path $projectRoot 'src'
    $schemaPath = Join-Path $projectRoot 'src\codex_quota_guard\storage\schema.sql'
    $qmlPath = Join-Path $projectRoot 'src\codex_quota_guard\ui\qml'
    $hookPath = Join-Path $projectRoot 'packaging\hooks'
    $launcherPath = Join-Path $projectRoot 'packaging\launcher.py'
    $iconPath = Join-Path $artifactRoot "icon-$buildTag\CodexQuotaGuard.ico"
    & $venvPython (Join-Path $projectRoot 'scripts\generate_icon.py') $iconPath
    if ($LASTEXITCODE -ne 0) { throw "Icon generation failed with exit code $LASTEXITCODE" }
    $pyInstallerArguments = @(
        '--windowed',
        '--name', 'CodexQuotaGuard',
        '--icon', $iconPath,
        '--paths', $sourcePath,
        '--additional-hooks-dir', $hookPath,
        '--distpath', $distPath,
        '--workpath', $workPath,
        '--specpath', $specPath,
        '--hidden-import', 'PySide6.QtQml',
        '--hidden-import', 'PySide6.QtQuick',
        '--hidden-import', 'PySide6.QtQuickControls2',
        '--add-data', "$schemaPath;codex_quota_guard\storage",
        '--add-data', "$qmlPath;codex_quota_guard\ui\qml"
    )
    $pyInstallerArguments += $launcherPath
    & $venvPython -m PyInstaller @pyInstallerArguments
    if ($LASTEXITCODE -ne 0) { throw "Build failed with exit code $LASTEXITCODE" }
}
finally {
    Pop-Location
}

Write-Host "Build complete: $distPath\CodexQuotaGuard\CodexQuotaGuard.exe"
