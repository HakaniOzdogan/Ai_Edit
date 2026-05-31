# AI Video Editor — Durdur
# Kullanim: .\stop.ps1

Write-Host ""
Write-Host "=== AI Video Editor Durduruluyor ===" -ForegroundColor Cyan

# Electron'u durdur
$electronProcs = Get-Process -Name "electron" -ErrorAction SilentlyContinue
if ($electronProcs) {
    $electronProcs | Stop-Process -Force
    Write-Host "[OK] Electron durduruldu" -ForegroundColor Green
} else {
    Write-Host "[ ] Electron zaten kapali" -ForegroundColor Gray
}

# Python agent'i durdur
$pythonProcs = Get-Process -Name "python" -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -like "*agent*" -or $_.CommandLine -like "*main.py*" }
if (-not $pythonProcs) {
    # CommandLine erişimi yoksa tüm python'ları dene
    $pythonProcs = Get-Process -Name "python" -ErrorAction SilentlyContinue
}
if ($pythonProcs) {
    $pythonProcs | Stop-Process -Force -ErrorAction SilentlyContinue
    Write-Host "[OK] Python agent durduruldu" -ForegroundColor Green
} else {
    Write-Host "[ ] Python agent zaten kapali" -ForegroundColor Gray
}

# Port 8765'i temizle
$portCheck = netstat -ano 2>&1 | Select-String ":8765\s"
if ($portCheck) {
    $portPid = ($portCheck | Select-Object -First 1).ToString().Trim().Split()[-1]
    if ($portPid -match '^\d+$') {
        taskkill /PID $portPid /F 2>$null
        Write-Host "[OK] Port 8765 temizlendi" -ForegroundColor Green
    }
} else {
    Write-Host "[ ] Port 8765 zaten bos" -ForegroundColor Gray
}

Write-Host ""
Write-Host "Uygulama durduruldu." -ForegroundColor Cyan
