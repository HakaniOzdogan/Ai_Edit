# PHASE 1 — Ortam Kurulumu ve Doğrulaması

Önceki adım: Yok (başlangıç)
Sonraki adım: PHASE_2_AGENT.md

---

## Amaç

Projenin çalışması için gereken tüm araçları kur, doğrula ve proje iskeletini oluştur.
Bu adım tamamlanmadan hiçbir kod yazılmaz.

---

## 1.1 — Gerekli Araçlar

### Node.js (>= 18.x)
```bash
# İndir: https://nodejs.org (LTS sürüm)
node --version
npm --version
```

### Python (>= 3.10)
```bash
# İndir: https://python.org
# KRITIK: Kurulum sırasında "Add Python to PATH" kutusunu işaretle
python --version
pip --version
```

### FFmpeg
```bash
# İndir: https://ffmpeg.org/download.html (Windows builds — gyan.dev önerilir)
# zip'i aç, bin klasörünü sistem PATH'ine ekle
ffmpeg -version
ffprobe -version
```

### Git
```bash
git --version
```

---

## 1.2 — Proje Klasörünü Oluştur

```bash
mkdir ai-video-editor
cd ai-video-editor
git init

mkdir electron
mkdir electron\renderer
mkdir agent
mkdir agent\tools
mkdir agent\qa
mkdir agent\models
mkdir profiles
mkdir projects
mkdir luts
mkdir temp
```

---

## 1.3 — Python Sanal Ortamı

```bash
cd ai-video-editor
python -m venv venv
venv\Scripts\activate

# Aktivasyon sonrası prompt (venv) ile başlamalı
```

---

## 1.4 — Python Bağımlılıkları

`requirements.txt` dosyası oluştur:

```
fastapi==0.115.0
uvicorn==0.30.0
websockets==12.0
anthropic==0.34.0
librosa==0.10.2
opencv-python==4.10.0.84
moviepy==1.0.3
Pillow==10.4.0
yt-dlp==2024.9.27
pydantic==2.8.0
python-dotenv==1.0.1
numpy==1.26.4
```

```bash
pip install -r requirements.txt
```

### Olası Sorunlar

**librosa kurulumunda hata:** `pip install soundfile` önce çalıştır.

**opencv hata:** `pip install opencv-python-headless` alternatif dene.

**moviepy hata:** ImageMagick kurulu değilse bazı özellikler çalışmaz ama temel işlevler çalışır, ilerle.

---

## 1.5 — Node Bağımlılıkları

`package.json` oluştur:

```json
{
  "name": "ai-video-editor",
  "version": "1.0.0",
  "main": "electron/main.js",
  "scripts": {
    "start": "electron .",
    "build": "electron-builder --win"
  },
  "devDependencies": {
    "electron": "^31.0.0",
    "electron-builder": "^24.0.0"
  }
}
```

```bash
npm install
```

---

## 1.6 — .env Dosyası

Proje kökünde `.env` oluştur:

```
ANTHROPIC_API_KEY=sk-ant-buraya-anahtarini-yaz
AGENT_WS_PORT=8765
AGENT_HTTP_PORT=8766
TEMP_DIR=./temp
PROJECTS_DIR=./projects
PROFILES_DIR=./profiles
LUTS_DIR=./luts
```

**KRITIK:** `.env` dosyasını asla Git'e commit etme.

`.gitignore` oluştur:
```
.env
venv/
node_modules/
temp/
__pycache__/
*.pyc
dist/
```

---

## 1.7 — LUT Dosyaları

`luts/` klasörüne başlangıç LUT dosyalarını ekle.
Ücretsiz LUT kaynakları:
- https://luts.iwltbap.com (ücretsiz paketi indir)
- https://groundcontrol.film/free-luts

En az şu isimlerde `.cube` dosyaları olmalı:
```
luts/warm_cinema.cube
luts/cool_corporate.cube
luts/dark_dramatic.cube
luts/fast_vivid.cube
luts/natural_soft.cube
```

Bulamazsan boş dosya oluştur, PHASE_7'de gerçekleriyle değiştirilir:
```bash
type nul > luts\warm_cinema.cube
type nul > luts\cool_corporate.cube
type nul > luts\dark_dramatic.cube
```

---

## Doğrulama Kontrolleri

Bu adım tamamlandı sayılmadan önce HER BİRİNİ çalıştır:

```bash
# 1. Python araçları
python -c "import fastapi; print('fastapi ok')"
python -c "import anthropic; print('anthropic ok')"
python -c "import librosa; print('librosa ok')"
python -c "import cv2; print('opencv ok')"

# 2. Node
node -e "console.log('node ok')"
ls node_modules/electron

# 3. FFmpeg
ffmpeg -version | head -1
ffprobe -version | head -1

# 4. Klasör yapısı
ls agent/tools
ls agent/qa
ls luts

# 5. .env
python -c "from dotenv import load_dotenv; import os; load_dotenv(); print('API KEY:', os.getenv('ANTHROPIC_API_KEY')[:10] + '...')"
```

---

## Geçiş Kriteri

Tüm doğrulama komutları hatasız çalıştıysa PHASE_2_AGENT.md'ye geç.
Herhangi bir hata varsa bu adımda kal ve düzelt.

---

## Sık Karşılaşılan Hatalar

| Hata | Sebep | Çözüm |
|------|-------|-------|
| `python` bulunamadı | PATH'e eklenmemiş | Sistem ortam değişkenlerinden PATH'e Python ekle |
| `ffmpeg` bulunamadı | PATH'e eklenmemiş | FFmpeg bin klasörünü PATH'e ekle, terminali yeniden başlat |
| `pip install` SSL hatası | Şirket proxy | `pip install --trusted-host pypi.org ...` ekle |
| `librosa` ses kütüphanesi hatası | soundfile eksik | `pip install soundfile cffi` çalıştır |
| `npm install` EACCES | İzin sorunu | Terminali yönetici olarak çalıştır |
