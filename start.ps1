# AI Video Editor - Baslat
# Kullanim: .\start.ps1

$ProjectDir = $PSScriptRoot
Set-Location $ProjectDir

# PATH guncelle
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" +
            [System.Environment]::GetEnvironmentVariable("Path","User")

# Electron'un Node moduna girmesini engelle
$env:ELECTRON_RUN_AS_NODE = ""

Write-Host ""
Write-Host "=== AI Video Editor Baslatiliyor ===" -ForegroundColor Cyan

# Port 8765 kontrolu
$portCheck = netstat -ano 2>&1 | Select-String ":8765\s"
if ($portCheck) {
    Write-Host "[UYARI] 8765 portu dolu, temizleniyor..." -ForegroundColor Yellow
    $portPid = ($portCheck | Select-Object -First 1).ToString().Trim().Split()[-1]
    if ($portPid -match "^\d+$") {
        taskkill /PID $portPid /F 2>$null
        Start-Sleep -Seconds 1
    }
}

# Gerekli dosya kontrolleri
$checks = @(".env", "venv\Scripts\python.exe", "node_modules\electron\dist\electron.exe")
$allOk = $true
foreach ($f in $checks) {
    if (-not (Test-Path (Join-Path $ProjectDir $f))) {
        Write-Host "[EKSIK] $f" -ForegroundColor Red
        $allOk = $false
    }
}
if (-not $allOk) {
    Write-Host "Kurulum eksik. Devam edilemiyor." -ForegroundColor Red
    pause
    exit 1
}

# API key kontrol
$envContent = Get-Content (Join-Path $ProjectDir ".env") -ErrorAction SilentlyContinue -Raw
if ($envContent -notmatch "ANTHROPIC_API_KEY=sk-ant") {
    Write-Host "[UYARI] ANTHROPIC_API_KEY .env dosyasinda bulunamadi" -ForegroundColor Yellow
    Write-Host "         Claude ozellikleri calismaycak." -ForegroundColor Yellow
}

Write-Host "[OK] Kontroller tamam, uygulama baslatiliyor..." -ForegroundColor Green
Write-Host ""

$ElectronExe = Join-Path $ProjectDir "node_modules\electron\dist\electron.exe"
& $ElectronExe "."
