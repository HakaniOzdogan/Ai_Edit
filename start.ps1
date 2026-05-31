# AI Video Editor - Baslat
# Kullanim: .\start.ps1

$ProjectDir = $PSScriptRoot
Set-Location $ProjectDir

$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" +
            [System.Environment]::GetEnvironmentVariable("Path","User")
$env:ELECTRON_RUN_AS_NODE = ""

Write-Host ""
Write-Host "=== AI Video Editor ===" -ForegroundColor Cyan

# Dosya kontrolleri
foreach ($f in @(".env","venv\Scripts\python.exe","node_modules\electron\dist\electron.exe")) {
    if (-not (Test-Path (Join-Path $ProjectDir $f))) {
        Write-Host "[EKSIK] $f" -ForegroundColor Red
        pause; exit 1
    }
}

# Agent zaten calisiyor mu?
$agentRunning = $false
try {
    $h = Invoke-RestMethod "http://localhost:8765/health" -TimeoutSec 2
    if ($h.status -eq "ok") { $agentRunning = $true }
} catch {}

if ($agentRunning) {
    Write-Host "[OK] Agent zaten calisiyor, direkt aciliyor..." -ForegroundColor Green
} else {
    # Eski surecler ve port temizle
    Stop-Process -Name "python","electron" -Force -ErrorAction SilentlyContinue
    Start-Sleep -Milliseconds 600
    $portLine = netstat -ano 2>&1 | Select-String ":8765\s" | Select-Object -First 1
    if ($portLine) {
        $portPid = ($portLine.ToString().Trim() -split "\s+")[-1]
        if ($portPid -match "^\d+$") { taskkill /PID $portPid /F 2>$null; Start-Sleep -Milliseconds 400 }
    }

    Write-Host "[...] Agent baslatiliyor..." -ForegroundColor DarkGray

    Start-Process -FilePath "venv\Scripts\python.exe" -ArgumentList "agent\main.py" `
        -WorkingDirectory $ProjectDir -WindowStyle Hidden

    $ready = $false
    for ($i = 1; $i -le 60; $i++) {
        Start-Sleep -Milliseconds 500
        try {
            $h = Invoke-RestMethod "http://localhost:8765/health" -TimeoutSec 1
            if ($h.status -eq "ok") { $ready = $true; break }
        } catch {}
        if ($i % 6 -eq 0) {
            $sn = $i / 2
            Write-Host "    $sn saniye..." -ForegroundColor DarkGray
        }
    }

    if ($ready) {
        Write-Host "[OK] Agent hazir!" -ForegroundColor Green
    } else {
        Write-Host "[UYARI] Agent 30 saniyede baslamadi, devam ediliyor..." -ForegroundColor Yellow
    }
}

# API key kontrol
$envContent = Get-Content (Join-Path $ProjectDir ".env") -ErrorAction SilentlyContinue -Raw
if ($envContent -notmatch "ANTHROPIC_API_KEY=sk-ant") {
    Write-Host "[UYARI] API key eksik - Claude ozellikleri calismaycak" -ForegroundColor Yellow
}

Write-Host "[OK] Uygulama aciliyor..." -ForegroundColor Green
Write-Host ""

$ElectronExe = Join-Path $ProjectDir "node_modules\electron\dist\electron.exe"
& $ElectronExe "."
