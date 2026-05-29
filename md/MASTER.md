# AI Video Editor — Master Build Controller

Bu dosya projenin tek hakikat kaynağıdır.
Her adımı sırayla uygula. Bir adımı tamamlamadan bir sonrakine geçme.
Her adım sonunda belirtilen kontrolleri yap. Kontrol geçilmeden ilerleme.

---

## Genel Kurallar

- Her adım kendi MD dosyasına sahiptir. O dosyayı oku, sonra uygula.
- Bir adım başlamadan önce ön koşulları kontrol et.
- Bir adım bittikten sonra doğrulama komutlarını çalıştır, çıktıyı oku.
- Hata varsa o adımda kal, düzelt, tekrar doğrula.
- Hiçbir zaman "zaten çalışıyordur" varsayımıyla ilerleme.
- Kod yaz → test et → logları oku → sonra devam et.

---

## Adım Sırası

| # | Dosya | İçerik | Tahmini Süre |
|---|-------|---------|--------------|
| 1 | `PHASE_1_ENV.md` | Ortam kurulumu ve doğrulaması | 30–60 dk |
| 2 | `PHASE_2_AGENT.md` | Python FastAPI agent + WebSocket | 2–3 saat |
| 3 | `PHASE_3_TOOLS.md` | FFmpeg, müzik analizi, klip skoru | 2–3 saat |
| 4 | `PHASE_4_CLAUDE.md` | Claude API entegrasyonu + tool döngüsü | 2–3 saat |
| 5 | `PHASE_5_ELECTRON.md` | Electron masaüstü uygulaması | 3–4 saat |
| 6 | `PHASE_6_UI.md` | Arayüz — wizard, preview, chat | 3–4 saat |
| 7 | `PHASE_7_DAVINCI.md` | DaVinci Resolve entegrasyonu | 2–3 saat |
| 8 | `PHASE_8_AE.md` | After Effects ExtendScript | 2–3 saat |
| 9 | `PHASE_9_QA.md` | QA modülü — 3 katman | 3–4 saat |
| 10 | `PHASE_10_PACKAGE.md` | Windows .exe paketleme | 1–2 saat |

---

## Adım 1 Öncesi — Sistem Kontrolü

Projeye başlamadan önce şunu çalıştır:

```bash
node --version        # >= 18.x olmalı
python --version      # >= 3.10 olmalı
ffmpeg -version       # kurulu olmalı
git --version         # kurulu olmalı
```

Herhangi biri eksikse PHASE_1_ENV.md içinde kurulum adımları var.

---

## Kritik Riskler ve Genel Uyarılar

### Windows PATH Sorunu
FFmpeg, Python ve Node'un sistem PATH'inde olduğunu her adımda varsay, ama doğrula.
Sadece terminal çıktısını okuyarak doğrula — "kurulmuştu zaten" deme.

### Port Çakışması
Agent 8765 (WebSocket) ve 8766 (HTTP) portlarını kullanır.
Her agent başlatmadan önce portların boş olduğunu kontrol et:
```bash
netstat -ano | findstr :8765
netstat -ano | findstr :8766
```

### Anthropic API Key
`.env` dosyası olmadan hiçbir Claude entegrasyonu çalışmaz.
PHASE_4 başlamadan `.env` dosyasının varlığını doğrula.

### DaVinci Resolve Bağımlılığı
PHASE_7 başlamadan Resolve'un açık ve bir proje yüklü olduğunu doğrula.
Resolve kapalıyken script çalıştırma — sessizce hata verir, anlamak zor olur.

### Electron + Python Entegrasyonu
Electron, Python agent'ı subprocess olarak başlatır.
Agent hazır olmadan Electron penceresi açılırsa WebSocket bağlantısı kurulamaz.
PHASE_5'te 1500ms bekleme süresi buna göredir — gerekirse artır.

---

## Her Adım İçin Kontrol Protokolü

Bir adım tamamlandığında şu soruları sor:

1. Bu adımın doğrulama komutları başarıyla geçti mi?
2. Bir sonraki adımın ön koşullarını bu adım karşılıyor mu?
3. Log çıktılarında `ERROR`, `CRITICAL`, `Exception` var mı?
4. Oluşturulan dosyalar beklenen dizinde mi?

Hepsine EVET diyebiliyorsan sonraki adıma geç.

---

## Proje Klasör Yapısı (Hedef)

```
ai-video-editor/
├── electron/
│   ├── main.js
│   ├── preload.js
│   └── renderer/
│       ├── index.html
│       ├── app.js
│       └── styles.css
├── agent/
│   ├── main.py
│   ├── claude_client.py
│   ├── tools/
│   │   ├── ffmpeg_tool.py
│   │   ├── music_analyzer.py
│   │   ├── clip_scorer.py
│   │   ├── davinci_tool.py
│   │   ├── aftereffects_tool.py
│   │   └── reference_analyzer.py
│   ├── qa/
│   │   ├── orchestrator.py
│   │   ├── layer1_metrics.py
│   │   ├── layer2_claude.py
│   │   └── layer3_vision.py
│   └── models/
│       ├── project.py
│       └── profile.py
├── profiles/
├── projects/
├── luts/
├── temp/
├── .env
├── requirements.txt
└── package.json
```

---

## Durum Takibi

Her adımı tamamladıktan sonra bu tabloyu güncelle:

| Adım | Durum | Tamamlanma Tarihi | Notlar |
|------|-------|-------------------|--------|
| 1 — Ortam | Bekliyor | — | — |
| 2 — Agent | Bekliyor | — | — |
| 3 — Tools | Bekliyor | — | — |
| 4 — Claude | Bekliyor | — | — |
| 5 — Electron | Bekliyor | — | — |
| 6 — UI | Bekliyor | — | — |
| 7 — DaVinci | Bekliyor | — | — |
| 8 — AE | Bekliyor | — | — |
| 9 — QA | Bekliyor | — | — |
| 10 — Package | Bekliyor | — | — |
