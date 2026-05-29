# Claude Code — Gerekli Skills ve Kurulum Rehberi

Bu dosya Claude Code'un bu projeyi profesyonel kalitede inşa edebilmesi için
hangi skills'lerin yüklenmesi gerektiğini açıklar.

---

## Neden Skills Gerekli?

Claude Code, belirli dosya tipleri veya araçlarla çalışırken
"skills" denilen yönergeler paketine başvurur.
Bu skills olmadan Claude genel bilgisiyle hareket eder —
ortam spesifik kısıtlamaları, kütüphane sürüm farklılıklarını
veya Windows-spesifik davranışları bilemez ve hata yapar.

---

## Zorunlu Skills

### 1. Python Skill
**Ne için:** agent/, tools/, qa/ klasörlerindeki tüm Python kodları

Kapsam:
- asyncio ve async/await pattern'leri
- FastAPI + WebSocket sunucu kurulumu
- subprocess yönetimi (FFmpeg çağrıları)
- Pydantic model tanımları
- pip ve venv yönetimi
- Windows PATH sorunları

Kurulum: Claude Code settings → Skills → "Python Backend" ekle

---

### 2. Electron / Node.js Skill
**Ne için:** electron/ klasörü — main.js, preload.js, renderer

Kapsam:
- Electron main process / renderer process ayrımı
- contextIsolation ve IPC güvenliği
- WebSocket client yönetimi
- electron-builder ile Windows .exe paketleme
- npm scripts ve bağımlılık yönetimi

Kurulum: Claude Code settings → Skills → "Electron Desktop" ekle

---

### 3. FFmpeg Skill
**Ne için:** ffmpeg_tool.py ve tüm video işleme komutları

Kapsam:
- ffmpeg ve ffprobe komut sözdizimi
- codec seçimi (H.264, H.265, AAC)
- filter_complex kullanımı
- concat demuxer formatı
- blackdetect, loudnorm filtreleri
- Windows'ta yol ve tırnak işareti sorunları

Kurulum: Claude Code settings → Skills → "FFmpeg Video Processing" ekle

---

### 4. Frontend / CSS Skill
**Ne için:** electron/renderer/ — HTML, CSS, JavaScript

Kapsam:
- CSS Grid 3-sütun layout
- CSS custom properties (dark/light tema)
- WebSocket client tarafı yönetimi
- Drag-and-drop dosya yükleme
- Canvas ve video player

Kurulum: Claude Code settings → Skills → "Frontend Web" ekle

---

## Opsiyonel Skills (Tavsiye Edilir)

### 5. Anthropic API Skill
**Ne için:** claude_client.py — tool_use döngüsü

Kapsam:
- `tool_use` / `tool_result` mesaj formatı
- Streaming response yönetimi
- Rate limit ve retry stratejisi
- Vision API (base64 image gönderimi)
- Model seçimi (Sonnet vs Haiku)

Kurulum: Claude Code settings → Skills → "Anthropic Claude API" ekle

---

### 6. Windows Systems Skill
**Ne için:** PATH yönetimi, .exe paketleme, registry

Kapsam:
- Windows ortam değişkenleri
- PyInstaller ile .exe oluşturma
- NSIS installer yapılandırması
- Windows Defender / antivirus sorunları
- Yönetici hakları gerektiren işlemler

Kurulum: Claude Code settings → Skills → "Windows Development" ekle

---

## Skills Olmadan Karşılaşılacak Sorunlar

| Alan | Olası Hata | Skills Olsaydı |
|------|------------|----------------|
| FFmpeg | Windows'ta yol boşlukları hataya neden olur | Otomatik tırnak işareti ekler |
| Electron IPC | contextIsolation ihlali | Güvenli preload pattern kullanır |
| asyncio | Python 3.10+ syntax farklılıkları | Doğru syntax seçer |
| PyInstaller | librosa hidden import eksik | Tüm hidden import'ları bilir |
| Anthropic API | tool_use döngüsünde sonsuz loop | Doğru stop_reason kontrolü yapar |

---

## Skills Kurulum Adımları (Claude Code)

```
1. Claude Code'u aç (terminal: claude)
2. /config komutunu çalıştır
3. "Skills" sekmesine git
4. Yukarıdaki her skill için "Add Skill" tıkla
5. Skill adını yaz ve onayla
6. Projeye başlamadan önce /skills list ile kontrol et
```

---

## Proje Başlangıcında Claude'a Verilecek Bağlam

Claude Code ile çalışmaya başlarken şu komutu kullan:

```
Bu projeyi MASTER.md dosyasına göre inşa ediyoruz.
Şu an PHASE_X_XXX.md dosyasındayız.
Lütfen o dosyayı oku ve belirtilen adımları sırayla uygula.
Her adım sonunda doğrulama komutlarını çalıştır ve çıktıyı benimle paylaş.
Bir adımı geçmeden önce tüm kontroller geçilmeli.
```

---

## Kaliteli Bir Proje İçin Genel Claude Code Kullanım Kuralları

1. **Her faz için ayrı session aç.** Bağlam kirlenmesi önlenir.

2. **Her tool çağrısından sonra sonucu oku.** "Başarılı olmuştur" deme.

3. **Hata aldığında tam stack trace'i paylaş.** Kısaltma.

4. **Dosya yazmadan önce mevcut içeriği oku.** Overwrite hatalarını önler.

5. **Her adımda git commit at.** `git commit -m "PHASE_X: açıklama"`

6. **`.env` dosyasını asla Claude'a gösterme.** API key sızdırma riski.

7. **Test dosyaları yaz, silme.** Bir sonraki session'da işe yarar.

8. **Port çakışmasını her session başında kontrol et.**
   `netstat -ano | findstr :8765`
