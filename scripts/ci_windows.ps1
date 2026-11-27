<#
Сборка Windows x64 для GitHub Actions (windows-latest) и для локального запуска.

  powershell -ExecutionPolicy Bypass -File scripts/ci_windows.ps1

Результат в release\:
  RestoreAppStore-win-x64.exe
  RestoreAppStore-win-x64.exe.sha256
  RestoreAppStore-win-x64.zip          (onedir: RestoreAppStore\RestoreAppStore.exe)
  RestoreAppStore-win-x64.zip.sha256

Внешние файлы скачиваются с GitHub и сверяются по SHA-256 (ICU и ipatool-cpp 1.3.4).
#>
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

$IcuTag = "72.1-custom+4"
$IcuUrl = "https://github.com/FaithLife-Community/icu/releases/download/$IcuTag/icu-win.tar.gz"
$IcuSha = "2813ea1205fcf9d9a7930339dae181dc3e299b2391f2f4879c5e542be43f3a7f"

$IpatoolZipUrl = "https://github.com/Sorvigolova/ipatool/releases/download/1.3.4/windows_amd64_ipatool-cpp-1.3.4.zip"
$IpatoolZipSha = "f825512372346f2a29bd3be6ee9a2234a4de9781cdfbb597299d6a06ff36eb43"
$IpatoolExeSha = "3ab8167cbe3a36f3e12bf20ba4e7b9bd06a7b3165566973de3758786894edb0f"

function Assert-Hash([string]$Path, [string]$Expected) {
    $h = (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($h -ne $Expected.ToLowerInvariant()) {
        throw "SHA-256 mismatch: $Path`n  expected $Expected`n  got      $h"
    }
}

function Get-Checked([string]$Url, [string]$Out, [string]$Sha) {
    New-Item -ItemType Directory -Force (Split-Path -Parent $Out) | Out-Null
    if (-not (Test-Path -LiteralPath $Out) -or ((Get-FileHash -LiteralPath $Out -Algorithm SHA256).Hash -ne $Sha)) {
        Write-Host "Downloading $Url"
        $ProgressPreference = "SilentlyContinue"
        Invoke-WebRequest -Uri $Url -OutFile $Out
    }
    Assert-Hash $Out $Sha
}

function Invoke-Native {
    & $args[0] @($args | Select-Object -Skip 1)
    if ($LASTEXITCODE) { throw "Command failed ($LASTEXITCODE): $($args -join ' ')" }
}

$pyHost = (Get-Command python).Source
Write-Host "Host Python: $pyHost"
$bits = & $pyHost -c "import struct; print(struct.calcsize('P')*8)"
if ($bits.Trim() -ne "64") { throw "Python is not 64-bit: $bits" }

$venvPy = "build\venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $venvPy)) {
    Write-Host "Creating build\venv"
    Invoke-Native $pyHost -m venv build\venv
}
Invoke-Native $venvPy -m pip install --disable-pip-version-check -q -r requirements-build.txt

New-Item -ItemType Directory -Force build\dl, build\res, release | Out-Null

# --- ICU 72.1 (PySide6 on Windows needs icuuc.dll next to Qt) ---
Get-Checked $IcuUrl build\dl\icu-win.tar.gz $IcuSha
Remove-Item -Recurse -Force build\dl\icu -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force build\dl\icu | Out-Null
Invoke-Native tar -xzf build\dl\icu-win.tar.gz -C build\dl\icu
$icuSrc = Get-ChildItem build\dl\icu -Recurse -Filter "icuuc.dll" | Select-Object -First 1
if (-not $icuSrc) { throw "icuuc.dll not found in ICU archive" }
$icuDir = "build\res\icu"
New-Item -ItemType Directory -Force $icuDir | Out-Null
foreach ($name in @("icu.dll", "icuuc.dll", "icuin.dll")) {
    $src = Join-Path $icuSrc.DirectoryName $name
    if (-not (Test-Path -LiteralPath $src)) { throw "Missing $src in ICU archive" }
    Copy-Item -LiteralPath $src -Destination (Join-Path $icuDir $name) -Force
}

# --- ipatool-cpp 1.3.4 ---
Get-Checked $IpatoolZipUrl build\dl\ipatool-cpp.zip $IpatoolZipSha
Remove-Item -Recurse -Force build\dl\ipatool-cpp -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force build\dl\ipatool-cpp | Out-Null
Invoke-Native tar -xf build\dl\ipatool-cpp.zip -C build\dl\ipatool-cpp
$ipatool = Get-ChildItem build\dl\ipatool-cpp -Recurse -Filter "ipatool-cpp*.exe" | Select-Object -First 1
if (-not $ipatool) { throw "ipatool-cpp exe not found in archive" }
Assert-Hash $ipatool.FullName $IpatoolExeSha
Copy-Item -LiteralPath $ipatool.FullName -Destination build\res\ipatool-cpp.exe -Force
Copy-Item -Force licenses\IPATOOL_CPP_LICENSE.txt, licenses\IPA_DOWNLOADER_LICENSE.txt build\res\

Write-Host "Tests"
Invoke-Native $venvPy -m unittest discover -s tests -q

if (-not (Test-Path -LiteralPath assets\icon.ico)) {
    Invoke-Native $venvPy installer\make_art.py
}

$version = (& $venvPy tools\write_version_info.py build\version_info.txt).Trim()
if ($LASTEXITCODE) { throw "Failed to write version info" }
Write-Host "Version $version"

foreach ($onedir in @("0", "1")) {
    $env:RESTORE_ONEDIR = $onedir
    $label = if ($onedir -eq "1") { "onedir" } else { "onefile" }
    Write-Host "PyInstaller $version ($label)"
    Invoke-Native build\venv\Scripts\pyinstaller.exe RestoreAppStore.spec --noconfirm --log-level WARN --workpath "build\work$onedir" --distpath dist
}
Remove-Item Env:RESTORE_ONEDIR

foreach ($exe in @("dist\RestoreAppStore.exe", "dist\RestoreAppStore\RestoreAppStore.exe")) {
    if (-not (Test-Path -LiteralPath $exe)) { throw "Missing $exe" }
    $report = Join-Path (Get-Location) "build\check-ui-$($exe.Replace('\','-')).txt"
    $p = Start-Process -FilePath $exe -ArgumentList @("--check-ui", $report) -Wait -PassThru -WindowStyle Hidden
    if ($p.ExitCode -ne 0) {
        $text = if (Test-Path -LiteralPath $report) { Get-Content -LiteralPath $report -Raw } else { "" }
        throw "UI check failed for $exe (exit $($p.ExitCode)):`n$text"
    }
    Write-Host "UI check OK: $exe"
}

Copy-Item -Force dist\RestoreAppStore.exe release\RestoreAppStore-win-x64.exe

$zipPath = (Resolve-Path .).Path + "\release\RestoreAppStore-win-x64.zip"
if (Test-Path -LiteralPath $zipPath) { Remove-Item -LiteralPath $zipPath }
# Zip so the first path is RestoreAppStore/RestoreAppStore.exe (same layout as published releases).
Push-Location dist
try {
    Invoke-Native tar -a -cf $zipPath RestoreAppStore
} finally {
    Pop-Location
}

$venvPyArgs = @("-c", @"
import hashlib, pathlib
root = pathlib.Path('release')
for name in ('RestoreAppStore-win-x64.exe', 'RestoreAppStore-win-x64.zip'):
    path = root / name
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    (root / (name + '.sha256')).write_text(f'{digest}  {name}\n', encoding='ascii')
    print(f'{digest}  {name}')
"@)
Invoke-Native $venvPy @venvPyArgs
Write-Host "Done. Files in release\"
