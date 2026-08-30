# Gera o instalador (TradutorDeLegendasSetup.exe) a partir de dist\Tradutor de Legendas\.
# Uso:  powershell -ExecutionPolicy Bypass -File installer\build_installer.ps1
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$dist = Join-Path $root "dist\Tradutor de Legendas\Tradutor de Legendas.exe"
if (-not (Test-Path $dist)) {
    Write-Host "dist\ nao encontrada. Gerando o executavel primeiro..." -ForegroundColor Yellow
    & "$root\build_exe.bat"
    if (-not (Test-Path $dist)) { throw "build_exe.bat nao produziu o executavel." }
}

# localiza o compilador do Inno Setup (ISCC.exe)
function Find-ISCC {
    $cmd = Get-Command iscc.exe -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    foreach ($p in @(
        "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
        "${env:ProgramFiles}\Inno Setup 6\ISCC.exe",
        "${env:LOCALAPPDATA}\Programs\Inno Setup 6\ISCC.exe")) {
        if (Test-Path $p) { return $p }
    }
    return $null
}

$iscc = Find-ISCC
if (-not $iscc) {
    Write-Host "Inno Setup nao encontrado. Instalando..." -ForegroundColor Yellow
    $ok = $false
    try { winget install --id JRSoftware.InnoSetup -e --accept-source-agreements --accept-package-agreements; $ok = $true } catch {}
    if (-not $ok) { try { choco install innosetup -y; $ok = $true } catch {} }
    $iscc = Find-ISCC
    if (-not $iscc) { throw "Instale o Inno Setup 6 manualmente: https://jrsoftware.org/isdl.php" }
}

Write-Host "Compilando com $iscc ..." -ForegroundColor Cyan
& $iscc "$PSScriptRoot\tradutor-legendas.iss"
if ($LASTEXITCODE -ne 0) { throw "ISCC falhou (exit $LASTEXITCODE)." }

$out = Join-Path $PSScriptRoot "Output\TradutorDeLegendasSetup.exe"
Write-Host "`nPronto: $out" -ForegroundColor Green
