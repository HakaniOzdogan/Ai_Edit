# AI Video Editor

Yapay zeka destekli profesyonel video prodüksiyon asistanı. Ham medyadan (video, fotoğraf, müzik) müziğe senkron, renk düzeltmeli, motion grafik içeren videolar üretir.

---

## Özellikler

- **Beat-sync otomatik kurgu** — Müziğin ritmine göre klip kesimi
- **Semantik klip analizi** — Claude Vision ile içerik anlama, ürün görünürlüğü, duygu tespiti
- **Kalite odaklı seçim** — Shot type (action/medium/static) çeşitliliği, renk sürekliliği
- **DaVinci Resolve entegrasyonu** — Profesyonel renk grading ve LUT uygulama
- **After Effects / Remotion** — Logo reveal, alt başlık animasyonları
- **Premiere Pro** — Final 4K H.265 export
- **YouTube / Spotify müzik** — Link yapıştırarak müzik indirme
- **Fotoğraf desteği** — Ken Burns efektiyle fotoğrafları videoya dönüştürme
- **3 Katmanlı QA** — Metrik + Claude denetimi + Vision analizi, A–F not
- **İteratif chat** — Render sonrası düzeltme komutları
- **Proje yönetimi** — OneDrive'a kaydet/aç

---

## Gereksinimler

### Zorunlu

| Araç | Versiyon | Notlar |
|------|----------|--------|
| Windows | 10/11 x64 | — |
| Node.js | ≥ 18 | [nodejs.org](https://nodejs.org) |
| Python | ≥ 3.10 | "Add to PATH" seçili olmalı |
| FFmpeg | ≥ 6.0 | [ffmpeg.org](https://ffmpeg.org) — PATH'e ekle |
| Anthropic API Key | — | [console.anthropic.com](https://console.anthropic.com) |

### Opsiyonel (daha iyi kalite için)

| Araç | Ne için |
|------|---------|
| DaVinci Resolve 20 | Profesyonel renk grading |
| After Effects 2026 | Gelişmiş logo/metin animasyonları |
| Premiere Pro 2026 | Final export presetleri |

---

## Kurulum

### 1. Repoyu klonla

```bash
git clone <repo-url>
cd Ai_Edit
```

### 2. Python sanal ortamı

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Node bağımlılıkları

```powershell
npm install
```

### 4. `.env` dosyasını oluştur

`.env.example` dosyasını kopyala ve API key'ini gir:

```powershell
Copy-Item .env.example .env
notepad .env
```

```env
ANTHROPIC_API_KEY=sk-ant-...

# Proje dosyaları (OneDrive önerilir)
PROJECTS_DIR=C:\Users\Kullanici\OneDrive\Videos\Ai_Edit\projects
PROFILES_DIR=C:\Users\Kullanici\OneDrive\Videos\Ai_Edit\profiles
OUTPUT_DIR=C:\Users\Kullanici\OneDrive\Videos\Ai_Edit\output

# Geçici dosyalar (YEREL disk — OneDrive'a koyma)
TEMP_DIR=.\temp
LUTS_DIR=.\luts
```

---

## Kullanım

### Uygulamayı başlat

```powershell
.\start.ps1
```

> İlk çalıştırmada ~5–7 saniye, sonraki açılışlarda ~2–3 saniye.

### Durdur

```powershell
.\stop.ps1
```

---

## İlk Proje

1. **Ana ekran** açılır — Agent bağlandıktan sonra `Hazırız — Başlayalım!` yazar
2. **Yeni Proje** butonuna tıkla
3. **Sihirbazda** proje tipini, tarzı ve müziği seç
4. Video/fotoğrafları **sürükle-bırak** ile ekle
5. Asistan sana ne yapacağını sorar — **onayla**
6. **Demo render** oluşur, QA raporu gösterilir
7. Chat ile düzeltmeler yap
8. **4K Final** render al

### Müzik Ekleme

- Dosya: MP3/WAV sürükle-bırak
- Link: YouTube veya Spotify linki yapıştır → ⬇ butonu

---

## Tarz Seçenekleri

| Tarz | Beat/Sahne | Geçiş | Renk |
|------|-----------|-------|------|
| `dark` | 4 beat | Hard cut | Cool, dramatik |
| `warm` | 3 beat | Dissolve | Sıcak, soft |
| `corp` | 2 beat | Fade | Nötr, temiz |
| `fast` | 1 beat | Wipe | High contrast, enerji |

---

## DaVinci Resolve Kurulumu (Opsiyonel)

Her oturum başında Resolve açıkken bir kez çalıştır:

```
Workspace → Console → Py3 → Yapıştır:
exec(open(r"D:\\...\\agent\\tools\\resolve_bridge.py").read())
```

"Bridge hazir" yazısını gördükten sonra renk grading otomatik çalışır.

> Uygulama açılırken Resolve kapalıysa otomatik açıp bridge'i kurar.

---

## Klasör Yapısı

```
Ai_Edit/
├── agent/              # Python FastAPI backend
│   ├── main.py         # WebSocket sunucu + REST API
│   ├── claude_client.py # Claude tool döngüsü
│   ├── tools/          # FFmpeg, müzik analizi, klip skoru...
│   └── qa/             # 3 katmanlı kalite kontrol
├── electron/           # Masaüstü uygulama (Electron 28)
│   ├── main.js
│   ├── preload.js
│   └── renderer/       # HTML + CSS + JS
├── remotion/           # React motion graphics
│   └── src/            # LogoReveal, TextOverlay, Transition
├── luts/               # Renk LUT dosyaları (.cube)
├── start.ps1           # Uygulamayı başlat
├── stop.ps1            # Uygulamayı durdur
└── .env                # API key ve klasör yolları
```

---

## API & Portlar

| Servis | Port | Protokol |
|--------|------|----------|
| Agent HTTP | 8765 | REST |
| Agent WebSocket | 8765 | `ws://localhost:8765/ws` |

---

## Maliyet

`claude-sonnet-4-6` fiyatlarına göre:

| Proje | Tahmini Maliyet |
|-------|----------------|
| 10 klip, 30sn demo | ~$0.35 |
| 30 klip, 60sn demo | ~$0.50 |
| 100 klip, 90sn demo | ~$0.65 |

5$ bakiye ile yaklaşık **10–15 tam proje** yapılabilir.

---

## Geliştirme

```powershell
# Agent'ı direkt başlat (debug modu)
venv\Scripts\python.exe agent\main.py

# Electron'u başlat (DevTools açık)
$env:ELECTRON_RUN_AS_NODE=""
node_modules\electron\dist\electron.exe .
```

### Yeni LUT Ekle

`.cube` dosyasını `luts/` klasörüne koy. Otomatik olarak renk grading seçeneklerine eklenir.

---

## Sorun Giderme

**Agent başlamıyor:**
```powershell
.\stop.ps1  # önce temizle
.\start.ps1
```

**Port meşgul:**
```powershell
netstat -ano | findstr :8765
taskkill /PID <PID> /F
```

**DaVinci bağlanamıyor:**
- Resolve açık mı kontrol et
- `Workspace → Console → Py3` → bridge scriptini çalıştır

**Electron gri ekran:**
```powershell
# ELECTRON_RUN_AS_NODE temizle
$env:ELECTRON_RUN_AS_NODE=""
.\start.ps1
```

---

## Lisans

Kişisel kullanım için geliştirilmiştir.
