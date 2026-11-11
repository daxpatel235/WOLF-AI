<#
.SYNOPSIS
    Checks the Windows build: self-tests the app, then installs, self-tests and uninstalls
    both the setup.exe and the .msi. Fails on the first problem.

    Installing the MSI needs an elevated shell (GitHub's Windows runners are elevated).
#>
param([string]$Version = "")

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
if (-not $Version) {
    $Version = (python -c "from backend.version import __version__; print(__version__)").Trim()
}
$setup = Join-Path $root "dist\WolfAI-$Version-x64-setup.exe"
$msi = Join-Path $root "dist\WolfAI-$Version-x64.msi"
$work = Join-Path ([System.IO.Path]::GetTempPath()) "wolfai-check-$([guid]::NewGuid().ToString('N'))"
New-Item -ItemType Directory -Force -Path $work | Out-Null

function Step($text) { Write-Host "`n=== $text" -ForegroundColor Cyan }
function Fail($text) { throw "CHECK FAILED: $text" }

function Invoke-SelfTest([string]$exe, [string]$label) {
    if (-not (Test-Path $exe)) { Fail "$label`: $exe not found" }
    $report = Join-Path $work "selftest-$label.txt"
    # The exe is windowed (no console), so the result comes back through a report file + exit code.
    $p = Start-Process -FilePath $exe -ArgumentList @("--self-test", "`"$report`"") -Wait -PassThru
    if (Test-Path $report) { Get-Content $report | Write-Host }
    if ($p.ExitCode -ne 0) { Fail "$label self-test exited with $($p.ExitCode)" }
    Write-Host "$label self-test passed" -ForegroundColor Green
}

function Get-MsiProperty([string]$path, [string]$name) {
    $installer = New-Object -ComObject WindowsInstaller.Installer
    $db = $installer.GetType().InvokeMember("OpenDatabase", "InvokeMethod", $null, $installer, @($path, 0))
    $view = $db.GetType().InvokeMember("OpenView", "InvokeMethod", $null, $db, @("SELECT Value FROM Property WHERE Property='$name'"))
    $view.GetType().InvokeMember("Execute", "InvokeMethod", $null, $view, $null) | Out-Null
    $record = $view.GetType().InvokeMember("Fetch", "InvokeMethod", $null, $view, $null)
    $value = if ($record) { $record.GetType().InvokeMember("StringData", "GetProperty", $null, $record, 1) } else { $null }
    $view.GetType().InvokeMember("Close", "InvokeMethod", $null, $view, $null) | Out-Null
    [System.Runtime.InteropServices.Marshal]::ReleaseComObject($installer) | Out-Null
    return $value
}

Step "Built app folder"
$exe = Join-Path $root "dist\WolfAI\WolfAI.exe"
$info = (Get-Item $exe).VersionInfo
if ($info.ProductVersion -ne $Version) { Fail "WolfAI.exe ProductVersion is '$($info.ProductVersion)', expected $Version" }
if ($info.CompanyName -ne "Dax Patel") { Fail "WolfAI.exe CompanyName is '$($info.CompanyName)'" }
Invoke-SelfTest $exe "app-folder"

Step "setup.exe: install, self-test, uninstall"
if (-not (Test-Path $setup)) { Fail "$setup not found" }
$dir = Join-Path $work "setup-install"
$p = Start-Process -FilePath $setup -Wait -PassThru -ArgumentList @(
    "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/CURRENTUSER", "/DIR=`"$dir`"", "/LOG=`"$work\setup.log`"")
if ($p.ExitCode -ne 0) { Get-Content "$work\setup.log" -Tail 40; Fail "setup.exe exited with $($p.ExitCode)" }
Invoke-SelfTest (Join-Path $dir "WolfAI.exe") "setup-installed"
$shortcut = Join-Path ([Environment]::GetFolderPath("Programs")) "Wolf AI.lnk"
if (-not (Test-Path $shortcut)) { Fail "Start Menu shortcut not created: $shortcut" }
$p = Start-Process -FilePath (Join-Path $dir "unins000.exe") -ArgumentList @("/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART") -Wait -PassThru
if ($p.ExitCode -ne 0) { Fail "uninstaller exited with $($p.ExitCode)" }
# The uninstaller finishes in a child process; give it a moment.
for ($i = 0; $i -lt 30 -and (Test-Path (Join-Path $dir "WolfAI.exe")); $i++) { Start-Sleep -Seconds 1 }
if (Test-Path (Join-Path $dir "WolfAI.exe")) { Fail "setup.exe uninstall left WolfAI.exe behind" }
Write-Host "setup.exe install/uninstall passed" -ForegroundColor Green

Step "MSI: properties, install, self-test, uninstall"
if (-not (Test-Path $msi)) { Fail "$msi not found" }
$props = @{
    ProductName    = "Wolf AI Code Debugger"
    ProductVersion = $Version
    Manufacturer   = "Dax Patel"
}
foreach ($k in $props.Keys) {
    $v = Get-MsiProperty $msi $k
    if ($v -ne $props[$k]) { Fail "MSI $k is '$v', expected '$($props[$k])'" }
}
$p = Start-Process msiexec.exe -Wait -PassThru -ArgumentList @("/i", "`"$msi`"", "/qn", "/norestart", "/l*v", "`"$work\msi-install.log`"")
if ($p.ExitCode -ne 0) { Get-Content "$work\msi-install.log" -Tail 60; Fail "MSI install exited with $($p.ExitCode)" }
$installed = Join-Path $env:ProgramFiles "Wolf AI\WolfAI.exe"
Invoke-SelfTest $installed "msi-installed"
$p = Start-Process msiexec.exe -Wait -PassThru -ArgumentList @("/x", "`"$msi`"", "/qn", "/norestart", "/l*v", "`"$work\msi-uninstall.log`"")
if ($p.ExitCode -ne 0) { Get-Content "$work\msi-uninstall.log" -Tail 60; Fail "MSI uninstall exited with $($p.ExitCode)" }
if (Test-Path $installed) { Fail "MSI uninstall left WolfAI.exe behind" }
Write-Host "MSI install/uninstall passed" -ForegroundColor Green

Write-Host "`nAll Windows checks passed." -ForegroundColor Green
