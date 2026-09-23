<#
.SYNOPSIS
  Compila lectorMD para Windows: instalador (.exe) y versión portable (.zip).

.DESCRIPTION
  Requisitos en el PC con Windows 10/11:
    - Python 3.12        winget install Python.Python.3.12
    - Inno Setup 6       winget install JRSoftware.InnoSetup   (solo para el instalador)

  Uso, desde la carpeta del proyecto:
    powershell -ExecutionPolicy Bypass -File packaging\windows\build.ps1

  Resultado en dist\paquetes\:
    lectorMD-<versión>-windows-setup.exe      instalador
    lectorMD-<versión>-windows-portable.zip   portable (descomprimir y ejecutar)

.PARAMETER SinVenv
  Usa el Python activo en vez de crear .venv-win (así lo usa GitHub Actions).
#>
param([switch]$SinVenv)

$ErrorActionPreference = "Stop"
$Raiz = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
Set-Location $Raiz

$Version = (Select-String -Path "lectormd\__init__.py" -Pattern '__version__ = "([^"]+)"').Matches[0].Groups[1].Value
Write-Host "==> lectorMD $Version" -ForegroundColor Cyan

# 1. Entorno de Python ------------------------------------------------------
if ($SinVenv) {
    $Py = "python"
} else {
    if (-not (Test-Path ".venv-win\Scripts\python.exe")) {
        Write-Host "  creando entorno virtual .venv-win"
        if (Get-Command py -ErrorAction SilentlyContinue) { & py -3.12 -m venv .venv-win }
        else { & python -m venv .venv-win }
        if ($LASTEXITCODE) { throw "No se pudo crear el entorno virtual. ¿Está instalado Python 3.12?" }
    }
    $Py = Join-Path $Raiz ".venv-win\Scripts\python.exe"
}
& $Py -m pip install --disable-pip-version-check -q -r requirements-build.txt
if ($LASTEXITCODE) { throw "Falló la instalación de dependencias" }

# 2. Ejecutable -------------------------------------------------------------
& $Py -m PyInstaller packaging\lectormd.spec --noconfirm --clean --distpath dist --workpath build\pyinstaller
if ($LASTEXITCODE) { throw "Falló PyInstaller" }
Copy-Item packaging\TERCEROS.md dist\lectorMD\TERCEROS.txt -Force

$Salida = Join-Path $Raiz "dist\paquetes"
New-Item -ItemType Directory -Force $Salida | Out-Null

# 3. Portable ---------------------------------------------------------------
$Zip = Join-Path $Salida "lectorMD-$Version-windows-portable.zip"
if (Test-Path $Zip) { Remove-Item $Zip }
Compress-Archive -Path "dist\lectorMD" -DestinationPath $Zip -CompressionLevel Optimal
Write-Host "  portable   -> $Zip" -ForegroundColor Green

# 4. Instalador -------------------------------------------------------------
$Iscc = @(
    "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
    "$env:ProgramFiles\Inno Setup 6\ISCC.exe",
    "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe"
) | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $Iscc) {
    $cmd = Get-Command iscc -ErrorAction SilentlyContinue
    if ($cmd) { $Iscc = $cmd.Source }
}

if ($Iscc) {
    & $Iscc "/DAppVersion=$Version" "/O$Salida" /Q packaging\windows\lectormd.iss
    if ($LASTEXITCODE) { throw "Falló Inno Setup" }
    Write-Host "  instalador -> $(Join-Path $Salida "lectorMD-$Version-windows-setup.exe")" -ForegroundColor Green
} else {
    Write-Warning "Inno Setup 6 no está instalado: se generó solo la versión portable."
    Write-Warning "Instálalo con:  winget install JRSoftware.InnoSetup   y vuelve a ejecutar este script."
}
