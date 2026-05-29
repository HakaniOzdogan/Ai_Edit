# PHASE 10 — Windows .exe Paketleme

Önceki adım: PHASE_9_QA.md (tüm modüller çalışıyor)
Sonraki adım: YOK — proje tamamlandı

---

## Amaç

Projeyi çift tıkla kurulabilen bir Windows .exe installer'ına dönüştür.

---

## 10.1 — Python Agent'ı Paketleme (PyInstaller)

```bash
pip install pyinstaller

pyinstaller --onefile --name agent ^
  --add-data "luts;luts" ^
  --add-data "profiles;profiles" ^
  --hidden-import librosa ^
  --hidden-import cv2 ^
  --hidden-import anthropic ^
  agent/main.py
```

Çıktı: `dist/agent.exe`

---

## 10.2 — Electron Builder Yapılandırması

`package.json` güncelle:

```json
{
  "build": {
    "appId": "com.aivideo.editor",
    "productName": "AI Video Editor",
    "win": {
      "target": "nsis",
      "icon": "assets/icon.ico"
    },
    "nsis": {
      "oneClick": false,
      "allowToChangeInstallationDirectory": true,
      "installerIcon": "assets/icon.ico"
    },
    "extraResources": [
      { "from": "dist/agent.exe", "to": "agent.exe" },
      { "from": "luts/",          "to": "luts/"     },
      { "from": "profiles/",      "to": "profiles/"  }
    ]
  }
}
```

---

## 10.3 — Electron main.js Güncelleme

Paketlenmiş agent yolunu bul:

```javascript
const { app } = require('electron')
const path = require('path')

function getAgentPath() {
  if (app.isPackaged) {
    return path.join(process.resourcesPath, 'agent.exe')
  }
  return null // dev modda Python'u doğrudan kullan
}
```

---

## 10.4 — Build

```bash
npm run build
```

Çıktı: `dist/AI Video Editor Setup.exe`

---

## Doğrulama Kontrolleri

```bash
# 1. PyInstaller build
ls dist/agent.exe

# 2. Electron build
npm run build
ls dist/*.exe

# 3. Kurulum testi — başka bir Windows makinesinde
# Setup.exe çalıştır → kur → aç → agent bağlansın
```

---

## Geçiş Kriteri

- `agent.exe` bağımsız çalışıyor (Python kurulu olmayan makinede)
- Electron installer oluşturuldu
- Kurulu uygulama açılıyor ve agent bağlanıyor
- Temel bir proje oluşturulabiliyor

---

## Sık Karşılaşılan Hatalar

| Hata | Sebep | Çözüm |
|------|-------|-------|
| `librosa` PyInstaller'da çalışmıyor | Hidden import eksik | `--hidden-import soundfile --collect-data librosa` ekle |
| `agent.exe` bulunamıyor | extraResources yolu yanlış | `package.json` yolunu kontrol et |
| Antivirus engelliyor | PyInstaller exe şüpheli görünür | Antivirus whitelist veya code signing |
| Port 8765 kullanımda | Başka uygulama | Installer'a port kontrolü ekle |
