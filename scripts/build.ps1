<#
.SYNOPSIS
    Builds Wolf AI for Windows x64: the app folder, a setup.exe and an .msi installer.

.DESCRIPTION
    Outputs (in dist\):
      WolfAI\                      app folder (what both installers install)
      WolfAI-<ver>-x64-setup.exe   installer for people (Inno Setup; per-user, no admin needed)
      WolfAI-<ver>-x64.msi         installer for managed deployments (WiX; per-machine)

    Needs Python 3.12 with requirements.txt + requirements-dev.txt, plus:
      Inno Setup 6.3+   choco install innosetup
      WiX v5            dotnet tool install --global wix --version 5.0.2
    Check the result with scripts\check_windows.ps1.

.EXAMPLE
    .\scripts\build.ps1
    .\scripts\build.ps1 -SkipInstallers
#>
param(
    [string]$Version = "",
    [switch]$SkipInstallers
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
Write-Host "Building Wolf AI $Version for Windows x64" -ForegroundColor Cyan

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

Remove-Item -Recurse -Force dist -ErrorAction SilentlyContinue

# --- App folder (PyInstaller). Only Web\ is bundled; wolf_key.json never is. ---
Write-Host "`n[1/3] App folder (dist\WolfAI)" -ForegroundColor Cyan
Invoke-Checked python @(
    "-m", "PyInstaller", "--noconfirm", "--clean", "--windowed",
    "--name", "WolfAI",
    "--icon", "packaging\icons\wolfai.ico",
    "--add-data", "Web;Web",
    "--version-file", $versionFile,
    "--exclude-module", "tkinter",
    "main.py"
)
$appDir = Join-Path $root "dist\WolfAI"
if (-not (Test-Path (Join-Path $appDir "WolfAI.exe"))) { throw "dist\WolfAI\WolfAI.exe was not created" }

if ($SkipInstallers) {
    Write-Host "`nInstallers skipped (-SkipInstallers)" -ForegroundColor Yellow
    exit 0
}

# --- setup.exe (Inno Setup) ---
Write-Host "`n[2/3] x64-setup.exe (Inno Setup)" -ForegroundColor Cyan
$iscc = (Get-Command iscc -ErrorAction SilentlyContinue).Source
if (-not $iscc) {
    $iscc = @("${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe", "$env:ProgramFiles\Inno Setup 6\ISCC.exe") |
        Where-Object { Test-Path $_ } | Select-Object -First 1
}
if (-not $iscc) { throw "Inno Setup not found. Install it with: choco install innosetup" }
Invoke-Checked $iscc @("/Qp", "/DAppVersion=$Version", "packaging\WolfAI.iss")

# --- .msi (WiX) ---
Write-Host "`n[3/3] x64.msi (WiX)" -ForegroundColor Cyan
if (-not (Get-Command wix -ErrorAction SilentlyContinue)) {
    throw "WiX not found. Install it with: dotnet tool install --global wix --version 5.0.2"
}
Invoke-Checked wix @(
    "build", "packaging\WolfAI.wxs",
    "-arch", "x64",
    "-d", "Version=$Version",
    "-bindpath", "app=$appDir",
    "-bindpath", "icons=$root\packaging\icons",
    "-o", "dist\WolfAI-$Version-x64.msi"
)
Remove-Item -Force "dist\*.wixpdb" -ErrorAction SilentlyContinue

Write-Host "`nDone:" -ForegroundColor Green
Get-ChildItem dist -File | ForEach-Object { "  {0,-40} {1,8:N1} MB" -f $_.Name, ($_.Length / 1MB) }
