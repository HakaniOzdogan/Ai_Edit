# AI Video Editor — Technical Requirements Document (TRD)

**Versiyon:** 1.0  
**Tarih:** Mayıs 2026  
**Durum:** Aktif  
**Bağlı belge:** PRD.md, MASTER.md, QA_MODULE.md

---

## 1. Genel Teknik Yapı

AI Video Editor dört katmanlı bir mimari üzerine inşa edilmiştir. Electron.js tabanlı masaüstü arayüzü, WebSocket üzerinden bir Python FastAPI agent ile iletişim kurar. Agent, Anthropic Claude API'yi karar motoru olarak kullanır ve FFmpeg, DaVinci Resolve, After Effects gibi lokal araçları subprocess veya script API'leri aracılığıyla kontrol eder.

### 1.1 Klasör Yapısı

```
ai-video-editor/
├── electron/
│   ├── main.js                  # Ana process — pencere, agent başlatma
│   ├── preload.js               # Güvenli IPC köprüsü
│   └── renderer/
│       ├── index.html
│       ├── app.js               # WebSocket yönetimi, UI logic
│       ├── wizard.js            # Proje kurulum sihirbazı
│       └── styles.css
├── agent/
│   ├── main.py                  # FastAPI + WebSocket sunucusu
│   ├── claude_client.py         # Anthropic API, tool döngüsü
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── ffmpeg_tool.py       # Video işleme
│   │   ├── music_analyzer.py    # librosa — BPM, beat
│   │   ├── clip_scorer.py       # opencv — klip kalitesi
│   │   ├── auto_editor.py       # Beat-sync kurgu algoritması
│   │   ├── davinci_tool.py      # DaVinci Resolve Fusion Script
│   │   ├── aftereffects_tool.py # AE ExtendScript
│   │   └── reference_analyzer.py# Referans video analizi
│   ├── qa/
│   │   ├── __init__.py
│   │   ├── orchestrator.py      # 3 katmanı birleştiren koordinatör
│   │   ├── layer1_metrics.py    # Metrik kontrol
│   │   ├── layer2_claude.py     # Claude denetimi
│   │   └── layer3_vision.py     # Vision frame analizi
│   └── models/
│       ├── project.py           # Pydantic proje modeli
│       └── profile.py           # Pydantic marka profili modeli
├── profiles/                    # Marka profilleri (.json)
├── projects/                    # Kullanıcı projeleri (.json)
├── luts/                        # LUT dosyaları (.cube)
├── temp/                        # Geçici render dosyaları
├── .env                         # API anahtarları (Git'e eklenmez)
├── requirements.txt
└── package.json
```

### 1.2 İletişim Protokolü

Electron renderer ↔ Python agent arasında iki kanal:

| Kanal | URL | Kullanım |
|-------|-----|----------|
| WebSocket | ws://localhost:8765/ws | Gerçek zamanlı komut ve progress |
| HTTP REST | http://localhost:8765 | Proje kaydetme, profil yönetimi |

### 1.3 Ortam Gereksinimleri

| Bileşen | Versiyon | Kurulum |
|---------|----------|---------|
| Node.js | ≥ 18.x | nodejs.org |
| Python | ≥ 3.10 | python.org — PATH'e ekle |
| FFmpeg | ≥ 6.0 | ffmpeg.org — bin klasörünü PATH'e ekle |
| DaVinci Resolve | ≥ 18.x (ücretsiz) | blackmagicdesign.com |
| After Effects | ≥ 2024 | Adobe CC (opsiyonel) |

---

## 2. Faz 1 — Temel Altyapı

### 2.1 Python Bağımlılıkları (requirements.txt)

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

### 2.2 FastAPI Agent Ana Sunucu

`agent/main.py` — WebSocket endpoint, HTTP endpoint'ler, logging:

```python
@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    try:
        while True:
            data = await ws.receive_json()
            await handle_command(ws, data)
    except WebSocketDisconnect:
        pass

@app.get("/health")
async def health():
    return {"status": "ok"}
```

### 2.3 Electron Ana Process

`electron/main.js` — Agent otomatik başlatma, pencere yönetimi:

```javascript
function startAgent() {
    const venvPython = path.join(__dirname, '..', 'venv', 'Scripts', 'python.exe')
    agentProcess = spawn(venvPython, ['agent/main.py'], { cwd: '../' })
}

app.whenReady().then(() => {
    startAgent()
    setTimeout(createWindow, 2000) // Agent hazır olunca aç
})
```

### 2.4 WebSocket Bağlantı Yöneticisi (Renderer)

`electron/renderer/app.js` — Otomatik yeniden bağlanma, mesaj dispatch:

```javascript
class AgentConnection {
    connect() { /* WebSocket bağlan, onclose'da retry */ }
    send(data) { this.ws.send(JSON.stringify(data)) }
    on(type, handler) { this.handlers[type] = handler }
}
```

### 2.5 Preload Güvenlik Köprüsü

`electron/preload.js`:

```javascript
contextBridge.exposeInMainWorld('electronAPI', {
    agentWsUrl:   () => 'ws://localhost:8765/ws',
    agentHttpUrl: () => 'http://localhost:8765',
})
```

---

## 3. Faz 2 — Analiz Motoru

### 3.1 Müzik Analizi (librosa)

`agent/tools/music_analyzer.py` — BPM, beat zamanları, drop noktaları:

```python
class MusicAnalyzer:
    async def analyze(self, file_path: str) -> dict:
        y, sr = librosa.load(file_path, sr=None)
        tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
        beat_times = librosa.frames_to_time(beat_frames, sr=sr).tolist()
        # RMS enerji — drop tespiti
        rms = librosa.feature.rms(y=y)[0]
        threshold = np.percentile(rms, 80)
        return {
            "bpm": round(float(tempo), 1),
            "beat_times": beat_times,
            "drop_times": [...],
            "duration": librosa.get_duration(y=y, sr=sr)
        }
```

### 3.2 Klip Skorlama (opencv)

`agent/tools/clip_scorer.py` — Parlaklık, keskinlik (Laplacian), hareket (Optical Flow):

```python
class ClipScorer:
    def _score_clip(self, path: str) -> dict:
        # Laplacian varyansı = keskinlik
        sharpness = cv2.Laplacian(gray, cv2.CV_64F).var()
        # Optical Flow = hareket yoğunluğu
        flow = cv2.calcOpticalFlowFarneback(prev_gray, gray, ...)
        total = (sharpness * 0.5) + (brightness * 0.3) + (motion * 0.2)
        return {"total_score": round(total, 3)}
```

### 3.3 Beat-Sync Kurgu Algoritması

`agent/tools/auto_editor.py`:

```python
def build_timeline(beat_times, scored_clips, music_duration, style="dark"):
    # Tarz bazlı beat atlama
    beat_skip = {"dark": 4, "fast": 1, "warm": 3, "corp": 2}[style]
    cut_beats = [beat_times[i] for i in range(0, len(beat_times), beat_skip)]

    for i, beat_time in enumerate(cut_beats):
        clip = clip_pool[clip_index % len(clip_pool)]
        timeline.append({
            "clip_path":  clip["path"],
            "start_time": beat_time,
            "duration":   next_beat - beat_time
        })
    return timeline
```

### 3.4 FFmpeg Tool

`agent/tools/ffmpeg_tool.py` — Hazır komut şablonları:

```python
class FFmpegTool:
    def demo_render_cmd(self, input_path):
        return f"-i \"{input_path}\" -vf scale=960:540 -c:v libx264 -crf 28 -preset ultrafast -c:a aac"

    def render_4k_cmd(self, input_path):
        return f"-i \"{input_path}\" -vf scale=3840:2160 -c:v libx265 -crf 18 -preset slow -c:a aac -b:a 320k"

    def get_duration(self, file_path) -> float:
        # ffprobe ile süre
```

---

## 4. Faz 3 — Claude API Entegrasyonu

### 4.1 System Prompt

```
Sen AI Video Editor sisteminin karar motorusun.

ARAÇLARIN:
- analyze_music  : Müzik BPM, beat ve drop tespiti
- score_clips    : Video klip kalite skorlaması
- build_timeline : Beat-sync otomatik kurgu oluşturma
- run_ffmpeg     : Video kesme, birleştirme, render
- apply_lut      : DaVinci üzerinden renk grading

KURGU KURALLARI:
- Her zaman önce müziği analiz et
- Ardından klipleri skorla
- Timeline'ı kurgula
- Demo render al (düşük kalite, hız öncelikli)
- Final render 4K H.265

TARZ TANIMLARI:
- dark_cinematic : 4 beat/sahne, desature, cool ton
- fast_cut       : 1 beat/sahne, high contrast, warm
- corporate      : 2 beat/sahne, clean, neutral
- warm_lifestyle : 3 beat/sahne, warm LUT, soft geçiş
```

### 4.2 Tool Tanımları

```python
TOOLS = [
    {
        "name": "analyze_music",
        "description": "Müzik BPM, beat zamanları, drop noktaları döner.",
        "input_schema": {
            "type": "object",
            "properties": {"file_path": {"type": "string"}},
            "required": ["file_path"]
        }
    },
    {
        "name": "score_clips",
        "description": "Video kliplerini kalite açısından puanlar.",
        "input_schema": {
            "type": "object",
            "properties": {"clip_paths": {"type": "array", "items": {"type": "string"}}},
            "required": ["clip_paths"]
        }
    },
    {
        "name": "build_timeline",
        "description": "Beat analizine göre otomatik kurgu timeline oluşturur.",
        "input_schema": {
            "type": "object",
            "properties": {
                "beat_times":     {"type": "array"},
                "scored_clips":   {"type": "array"},
                "music_duration": {"type": "number"},
                "style":          {"type": "string"}
            },
            "required": ["beat_times", "scored_clips", "music_duration"]
        }
    },
    {
        "name": "run_ffmpeg",
        "description": "FFmpeg ile trim, concat veya render.",
        "input_schema": {
            "type": "object",
            "properties": {
                "operation":   {"type": "string", "enum": ["trim","concat","demo_render","final_render"]},
                "input_path":  {"type": "string"},
                "output_path": {"type": "string"},
                "params":      {"type": "object"}
            },
            "required": ["operation", "output_path"]
        }
    }
]
```

### 4.3 Tool Döngüsü (claude_client.py)

```python
class ClaudeClient:
    async def process(self, data: dict):
        messages = [{"role": "user", "content": self._build_prompt(data)}]

        while True:
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4096,
                system=SYSTEM_PROMPT,
                tools=TOOLS,
                messages=messages
            )

            if response.stop_reason == "end_turn":
                yield {"type": "result", "text": response.content[0].text}
                break

            if response.stop_reason == "tool_use":
                for block in response.content:
                    if block.type == "tool_use":
                        yield {"type": "progress", "tool": block.name, "status": "running"}
                        result = await self._run_tool(block.name, block.input, context)
                        yield {"type": "progress", "tool": block.name, "status": "done"}
                        # tool_result mesajını messages'a ekle
                messages.append({"role": "user", "content": tool_results})
```

---

## 5. Faz 4 — Renk ve Motion Graphics

### 5.1 DaVinci Resolve Entegrasyonu

`agent/tools/davinci_tool.py` — Fusion Script API:

```python
class DaVinciTool:
    def _get_resolve(self):
        import DaVinciResolveScript as dvr
        resolve = dvr.scriptapp("Resolve")
        if not resolve:
            raise RuntimeError("DaVinci Resolve açık değil")
        return resolve

    async def apply_lut(self, lut_path: str) -> dict:
        resolve  = self._get_resolve()
        timeline = resolve.GetProjectManager().GetCurrentProject().GetCurrentTimeline()
        resolve.OpenPage("color")
        for i in range(1, timeline.GetTrackCount("video") + 1):
            for item in timeline.GetItemListInTrack("video", i):
                item.SetLUT(1, lut_path)
        return {"success": True}
```

**Ön koşul:** Resolve açık ve scripting etkin olmalı.
`Preferences → System → General → "External scripting using local network" AÇIK`

### 5.2 After Effects Entegrasyonu

`agent/tools/aftereffects_tool.py` — ExtendScript (.jsx) dosyası üret ve çalıştır:

```python
class AfterEffectsTool:
    AE_PATH = r"C:\Program Files\Adobe\Adobe After Effects 2024\Support Files\AfterFX.exe"

    async def add_logo_reveal(self, logo_path, duration, output_path):
        jsx = f"""
var comp = app.project.items.addComp("logo_reveal", 1920, 1080, 1, {duration}, 25);
var logoLayer = comp.layers.add(app.project.importFile(new ImportOptions(File("{logo_path}"))));
logoLayer.property("Opacity").setValueAtTime(0, 0);
logoLayer.property("Opacity").setValueAtTime(100, 0.8);
"""
        # jsx dosyasını yaz ve AE'yi headless çalıştır
        return await self.run_script(jsx)
```

### 5.3 LUT Kütüphanesi

| LUT Dosyası | Tarz | Kullanım Alanı |
|-------------|------|----------------|
| warm_cinema.cube | Warm / Cinematic | Lifestyle, düğün, ürün |
| cool_corporate.cube | Cool / Clean | Kurumsal, teknoloji |
| dark_dramatic.cube | Dark / Desaturate | Luxury marka, moda |
| fast_vivid.cube | High Contrast | Spor, enerji, genç marka |
| natural_soft.cube | Natural / Soft | Yiyecek, organik, sağlık |

---

## 6. Faz 5 — QA Modülü

### 6.1 Genel Bakış

Demo render tamamlandıktan sonra otomatik devreye girer.
3 katman sırayla çalışır, birleşik rapor üretir.
Kritik hata varsa kullanıcıya gösterilmeden önce otomatik düzeltme döngüsü başlar.

| Katman | Yöntem | Ne Kontrol Eder | Süre |
|--------|--------|-----------------|------|
| 1 — Metrik | Kod (ffmpeg + opencv + librosa) | Beat sync, siyah kare, ses-video, tekrar | < 10 sn |
| 2 — Claude | Claude API (metin) | Timeline mantığı, tarz uyumu, açılış/kapanış | 10–30 sn |
| 3 — Vision | Claude API (görsel) | Kompozisyon, ışık, renk, profesyonellik | 30–90 sn |

### 6.2 Katman 1 — Metrik Kontroller

```python
class MetricQA:
    def run(self, video_path, music_path, timeline):
        return {
            "beat_sync":         self._check_beat_sync(timeline, music_path),   # ±100ms
            "black_frames":      self._check_black_frames(video_path),           # 0 tolerans
            "av_sync":           self._check_av_sync(video_path),               # < 50ms
            "clip_repeat":       self._check_clip_repeat(timeline),             # max %30
            "duration":          self._check_duration(video_path, music_path),  # ±2sn
            "color_consistency": self._check_color(video_path),                 # < %40 fark
            "overall_score":     self._compute_score(results)
        }
```

Ağırlıklar: beat_sync %35, black_frames %20, av_sync %20, duration %15, clip_repeat %5, color %5

### 6.3 Katman 2 — Claude Denetimi

Claude'a timeline özeti ve metrik raporu gönderilir.
JSON formatında yanıt beklenir:

```json
{
  "opening_strength": 8,
  "closing_strength": 6,
  "rhythm_consistency": 7,
  "style_adherence": 9,
  "overall_score": 76,
  "issues": ["Kapanış sahnesi zayıf"],
  "auto_fixes": ["Son sahneyi en yüksek puanlı kliple değiştir"],
  "suggestions": ["Logo reveal 2 saniye daha erken gelebilir"]
}
```

### 6.4 Katman 3 — Vision Frame Analizi

Demo'dan çekilen kareler Claude vision'a gönderilir:

```python
class VisionQA:
    def run(self, video_path, timeline, music_analysis):
        timestamps = [0]                                      # açılış
        timestamps += [seg["start_time"] for seg in timeline[:5]]  # ilk 5 sahne
        timestamps.append(music_analysis.get("drop_times", [0])[0]) # drop anı
        frame_paths = self.extract_frames(video_path, timestamps)
        return self.analyze_frames(frame_paths)  # Claude vision API
```

Puanlanan kriterler: composition, lighting, color_grade, product_focus, motion_blur, professional

### 6.5 Birleşik Skor

```
final_score = (L1 × 0.35) + (L2 × 0.35) + (L3 × 0.30)

A (≥90): Profesyonel Kalite
B (≥75): İyi Kalite
C (≥60): Kabul Edilebilir
D (≥45): Revizyon Gerekli
F (<45) : Yeniden Oluştur
```

### 6.6 Otomatik Düzeltilebilen Sorunlar

| Sorun | Düzeltme | Yöntem |
|-------|----------|--------|
| Boş/siyah kare | Komşu kareden dolgu | FFmpeg overlay |
| Klip tekrarı | Sonraki kliple değiştir | Timeline güncelle + yeniden render |
| Kapanış zayıf | En yüksek puanlı klip | Timeline güncelle |
| Ses-video desync | Audio offset düzelt | FFmpeg -itsoffset |
| Süre uyumsuzluğu | Son sahneyi snap'le | FFmpeg trim |

---

## 7. API Referansı

### 7.1 WebSocket Mesaj Formatları

**Komut Mesajı (Electron → Agent):**
```json
{
  "type": "command",
  "command": "dark cinematic tarz, drop anında logo gelsin",
  "project_id": "prj_abc123",
  "style": "dark",
  "files": {
    "clips":  ["C:/Projects/clip1.mp4", "C:/Projects/clip2.mp4"],
    "photos": ["C:/Projects/img1.jpg"],
    "music":  "C:/Projects/music.mp3",
    "logo":   "C:/Projects/logo.png"
  },
  "profile": null
}
```

**Progress Mesajı (Agent → Electron):**
```json
{
  "type": "progress",
  "tool": "analyze_music",
  "status": "done",
  "message": "Müzik analizi tamamlandı",
  "data": {"bpm": 126.4, "beat_count": 84}
}
```

**Sonuç Mesajı (Agent → Electron):**
```json
{
  "type": "result",
  "output_path": "C:/Projects/demo_v1.mp4",
  "render_type": "demo",
  "duration": 42.3,
  "qa_score": 81.4,
  "qa_grade": "B — İyi Kalite"
}
```

### 7.2 REST Endpoints

| Method | Endpoint | Açıklama |
|--------|----------|----------|
| GET | /health | Agent sağlık kontrolü |
| GET | /projects | Projeleri listele |
| POST | /projects | Yeni proje oluştur |
| GET | /profiles | Marka profillerini listele |
| POST | /profiles/analyze | Referans URL'den profil oluştur |
| GET | /luts | LUT dosyaları |
| POST | /render/demo | Demo render başlat |
| POST | /render/final | Final render başlat |
| GET | /render/status/{id} | Render durumu |

---

## 8. Hata Yönetimi

| Hata Kodu | Durum | Çözüm |
|-----------|-------|-------|
| ERR_FFMPEG_NOT_FOUND | FFmpeg PATH'te yok | Kurulum kılavuzu göster |
| ERR_RESOLVE_OFFLINE | DaVinci Resolve kapalı | Otomatik başlatmayı dene |
| ERR_AE_NOT_INSTALLED | After Effects yok | FFmpeg fallback kullan |
| ERR_CLAUDE_API | API bağlantı hatası | 3 retry, sonra kullanıcıya bildir |
| ERR_RENDER_FAILED | FFmpeg render başarısız | Stderr logunu göster |
| ERR_MUSIC_PARSE | Müzik analizi başarısız | Manuel BPM girişi sun |
| ERR_QA_CRITICAL | Kritik QA hatası | Otomatik düzeltme döngüsü başlat |

---

## 9. Güvenlik ve Gizlilik

- Anthropic API anahtarı `.env` dosyasında tutulur, kaynak koda gömülmez.
- `.env` asla Git'e commit edilmez — `.gitignore`'a eklenir.
- Tüm medya dosyaları lokaldir; dışarıya gönderilmez. Yalnızca komut metni Claude API'ye iletilir.
- Temp klasörü her render tamamlandıktan sonra otomatik temizlenir.
- Electron `contextIsolation: true` — renderer'a doğrudan Node erişimi kapatılır.
- WebSocket yalnızca `localhost:8765` dinler; dış bağlantı kabul etmez.
- Vision API'ye gönderilen frame'ler temp klasöründe saklanır, işlem sonrası silinir.

---

## 10. Paketleme (Windows .exe)

### Python Agent (PyInstaller)

```bash
pyinstaller --onefile --name agent \
  --add-data "luts;luts" \
  --add-data "profiles;profiles" \
  --hidden-import librosa \
  --hidden-import cv2 \
  --hidden-import anthropic \
  agent/main.py
```

### Electron Builder (package.json)

```json
{
  "build": {
    "appId": "com.aivideo.editor",
    "productName": "AI Video Editor",
    "win": { "target": "nsis" },
    "extraResources": [
      { "from": "dist/agent.exe", "to": "agent.exe" },
      { "from": "luts/", "to": "luts/" }
    ]
  }
}
```

Çıktı: `dist/AI Video Editor Setup.exe`

---

*Bu TRD geliştirme sürecinde kod tamamlandıkça güncellenecektir.*  
*Bağlı belgeler: PRD.md — MASTER.md — CLAUDE_CODE_SKILLS.md*
