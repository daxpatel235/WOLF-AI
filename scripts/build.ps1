<#
.SYNOPSIS
    Builds Wolf AI for Windows: app folder, portable .exe, .zip and .msi installer.

.DESCRIPTION
    Outputs (in dist\):
      WolfAI\                         app folder (used by the installer)
      WolfAI-<ver>-portable.exe       single-file exe, no install needed
      WolfAI-<ver>-win64.zip          the app folder zipped
      WolfAI-<ver>-x64.msi            installer (needs the WiX v5 tool: dotnet tool install --global wix --version 5.0.2)

    Requirements: Python 3.12 with requirements.txt and requirements-dev.txt installed.

.EXAMPLE
    .\scripts\build.ps1
    .\scripts\build.ps1 -SkipMsi
#>
param(
    [string]$Version = "",
    [switch]$SkipMsi
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

function Invoke-Checked {
    param([string]$Exe, [string[]]$Arguments)
    & $Exe @Arguments
    if ($LASTEXITCODE -ne 0) { throw "$Exe failed with exit code $LASTEXITCODE" }
}

if (-not $Version) {
    $Version = (python -c "from backend.version import __version__; print(__version__)").Trim()
}
if ($Version -notmatch '^\d+\.\d+\.\d+$') { throw "Version must look like 2.0.0 (got '$Version')" }
$parts = $Version.Split('.')
Write-Host "Building Wolf AI $Version" -ForegroundColor Cyan

# --- Windows version resource (shown in the exe's Properties > Details) ---
New-Item -ItemType Directory -Force -Path build | Out-Null
$tuple = "$($parts[0]), $($parts[1]), $($parts[2]), 0"
$versionInfo = @"
VSVersionInfo(
  ffi=FixedFileInfo(filevers=($tuple), prodvers=($tuple), mask=0x3f, flags=0x0, OS=0x40004,
                    fileType=0x1, subtype=0x0, date=(0, 0)),
  kids=[
    StringFileInfo([StringTable('040904B0', [
      StringStruct('CompanyName', 'Dax Patel'),
      StringStruct('FileDescription', 'Wolf AI Code Debugger'),
      StringStruct('FileVersion', '$Version'),
      StringStruct('InternalName', 'WolfAI'),
      StringStruct('LegalCopyright', 'Copyright (c) Dax Patel'),
      StringStruct('OriginalFilename', 'WolfAI.exe'),
      StringStruct('ProductName', 'Wolf AI Code Debugger'),
      StringStruct('ProductVersion', '$Version')])]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
"@
$versionFile = Join-Path $root "build\version_info.txt"
# No BOM: PyInstaller evaluates this file as Python.
[System.IO.File]::WriteAllText($versionFile, $versionInfo)

# --- PyInstaller ---
# Only Web\ is bundled. wolf_key.json is never bundled: the key lives in the user's settings.
$common = @(
    "-m", "PyInstaller", "--noconfirm", "--clean", "--windowed",
    "--add-data", "Web;Web",
    "--version-file", $versionFile,
    "--exclude-module", "tkinter"
)

Remove-Item -Recurse -Force dist -ErrorAction SilentlyContinue

Write-Host "`n[1/4] App folder (dist\WolfAI)" -ForegroundColor Cyan
Invoke-Checked python ($common + @("--name", "WolfAI", "main.py"))

Write-Host "`n[2/4] Portable single-file exe" -ForegroundColor Cyan
Invoke-Checked python ($common + @("--onefile", "--name", "WolfAI-$Version-portable", "main.py"))

# Sanity checks: UI bundled (a missing Web folder means a blank window), no key bundled.
$appDir = Join-Path $root "dist\WolfAI"
if (-not (Test-Path (Join-Path $appDir "WolfAI.exe"))) { throw "dist\WolfAI\WolfAI.exe was not created" }
$index = Get-ChildItem -Path $appDir -Recurse -Filter index.html | Where-Object { $_.Directory.Name -eq "Web" }
if (-not $index) { throw "Web\index.html is missing from the build" }
if (Get-ChildItem -Path $appDir -Recurse -Filter wolf_key.json) { throw "wolf_key.json must not be bundled" }

Write-Host "`n[3/4] Zip" -ForegroundColor Cyan
Compress-Archive -Path "$appDir\*" -DestinationPath "dist\WolfAI-$Version-win64.zip" -Force

if ($SkipMsi) {
    Write-Host "`n[4/4] MSI skipped (-SkipMsi)" -ForegroundColor Yellow
} else {
    Write-Host "`n[4/4] MSI installer" -ForegroundColor Cyan
    if (-not (Get-Command wix -ErrorAction SilentlyContinue)) {
        throw "WiX not found. Install it with: dotnet tool install --global wix --version 5.0.2 (or run with -SkipMsi)"
    }
    Invoke-Checked wix @(
        "build", "packaging\WolfAI.wxs",
        "-arch", "x64",
        "-d", "Version=$Version",
        "-bindpath", "app=$appDir",
        "-o", "dist\WolfAI-$Version-x64.msi"
    )
}

Write-Host "`nDone:" -ForegroundColor Green
Get-ChildItem dist -File | ForEach-Object { "  {0,-40} {1,8:N1} MB" -f $_.Name, ($_.Length / 1MB) }
