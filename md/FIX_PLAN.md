# AI Video Editor - PRD Uyumluluk Duzeltme Plani

**Versiyon:** 1.0  
**Tarih:** Mayis 2026  
**Durum:** Uygulama Plani  
**Bagli belge:** PRD.md, TRD.md

---

## 1. Mevcut Durum Ozeti

Bu belge, `PRD.md` hedefleri ile mevcut repo arasindaki farklari uygulanabilir duzeltme adimlarina cevirir. Mevcut proje temel bir Electron arayuzu, FastAPI agent, Claude tool dongusu, FFmpeg render yardimcilari, muzik analizi ve klip skorlama modullerine sahiptir. Ancak PRD'deki tam urun akisi henuz tamamlanmis degildir.

### 1.1 PRD Ozellik Durumu

| PRD Alani | Durum | Not |
|----------|-------|-----|
| Electron masaustu uygulama | Kismi | Pencere, drag-drop, chat ve oynatici var; tema, proje yonetimi ve QA raporu eksik. |
| Python FastAPI local agent | Kismi | WebSocket ve temel GET endpointleri var; render/profil/proje POST endpointleri eksik. |
| Claude karar motoru | Kismi | Sadece analiz, skor, timeline ve FFmpeg tool'lari bagli. |
| Muzik analizi | Karsilaniyor | BPM, beat, onset ve basit drop analizi mevcut. |
| Klip skorlama | Kismi | Parlaklik, keskinlik ve hareket skoru var; sahne segmentasyonu yok. |
| Fotoğraf analizi | Eksik | Fotoğraflar UI'da gorunuyor, backend tarafinda islenmiyor. |
| Auto-Draft beat-sync kurgu | Kismi | Beat'e gore timeline uretiliyor; gecis secimi, sahne secimi ve offset optimizasyonu yok. |
| Referans profil sistemi | Eksik | Model ve liste endpointi var; analiz, kayit ve uygulama yok. |
| DaVinci Resolve color grading | Kismi | Tool var; ana Claude/render akisina bagli degil. |
| After Effects motion graphics | Kismi | Tool var; ana Claude/render akisina bagli degil. |
| QA modulu | Kismi | Kod var; demo render sonrasi otomatik calismiyor ve siyah kare kontrolu hatali. |
| Final render | Kismi | H.265 komutu var; UI komutu deterministik degil, muzikli finalde 4K scale garanti degil. |
| Windows paketleme | Kismi | Scriptler var; installer ve paketlenmis agent dogrulamasi yapilmali. |

---

## 2. Kritik Duzeltmeler

Bu bolumdeki maddeler once duzeltilmelidir. Bu hatalar giderilmeden PRD'deki demo -> QA -> final akisi guvenilir sayilmaz.

### 2.1 [Once Duzeltilmeli] QA Akisini Demo Render Sonrasina Bagla

**Sorun:** `agent/qa` altinda 3 katmanli QA kodu var, ancak `agent/claude_client.py` icindeki tool dongusune veya `render_timeline` sonrasina bagli degil.

**Yapilacaklar:**

- `QAOrchestrator` agent akisi icinde import edilmeli.
- Demo render basarili olduktan sonra QA otomatik calistirilmali.
- `result` mesajina `qa_report`, `qa_score`, `qa_grade`, `qa_pass` alanlari eklenmeli.
- Electron tarafinda QA sonucu chat mesajinda ve/veya ayri rapor panelinde gosterilmeli.

**Beklenen sonuc:** Demo render tamamlandiginda kullanici sadece video dosyasi degil, QA skoru ve oneriler listesini de gorur.

**Dogrulama:**

- Demo komutu calistirildiginda agent logunda Layer 1, Layer 2 ve Layer 3 adimlari gorunmeli.
- WebSocket sonuc mesajinda QA alanlari bulunmali.
- Claude API yoksa veya Vision hatasi olursa sistem kullaniciya acik hata/uyari vermeli, uygulama akisi kilitlenmemeli.

### 2.2 [Once Duzeltilmeli] Siyah Kare QA Kontrolunu Duzelt

**Sorun:** Mevcut kod `ffprobe -vf blackdetect` kullaniyor. Bu komut hatali calisiyor ve returncode kontrol edilmedigi icin siyah video bile temiz gorulebiliyor.

**Yapilacaklar:**

- Siyah kare kontrolu `ffmpeg -vf blackdetect -f null -` formuna alinmali.
- `subprocess.run` returncode kontrol edilmeli.
- Komut basarisizsa skor 100 verilmemeli; hata rapora dahil edilmeli.
- Siyah video, kisa temiz video ve araya siyah frame eklenmis video icin test fixture uretilmeli.

**Beklenen sonuc:** Siyah kare iceren videolar `black_events > 0` olarak raporlanir ve QA skoru duser.

**Dogrulama:**

- Tamamen siyah 1 saniyelik test videosu `black_events >= 1` dondurmeli.
- Temiz test videosu `black_events = 0` dondurmeli.

### 2.3 [Once Duzeltilmeli] Final Render Komutunu Deterministik Hale Getir

**Sorun:** UI "Final 4K render al" metnini chat olarak gonderiyor. Claude'un `quality: "final"` secmesi garanti degil. Muzikli final render yolunda 4K scale uygulanmiyor.

**Yapilacaklar:**

- Electron final butonu chat niyetine birakilmamali; agent'a acik `render_type: "final"` veya `quality: "final"` alani gonderilmeli.
- `ClaudeClient` final komutunu dogrudan `render_timeline(..., quality="final")` veya ayri endpoint ile calistirmali.
- Muzikli final render komutuna `-vf scale=3840:2160` eklenmeli.
- Final render codec, container ve bitrate/CRF ayarlari tek yerde sabitlenmeli.

**Beklenen sonuc:** Final butonuna basildiginda her zaman 4K H.265 MP4 uretilir.

**Dogrulama:**

- FFprobe ile cikti cozunurlugu `3840x2160` olmali.
- Video codec `hevc` olmali.
- Muzikli ve muziksiz final render ayri ayri test edilmeli.

---

## 3. PRD Ozelliklerine Gore Eksiklerin Tamamlanmasi

### 3.1 Otomatik Analiz Motoru

**Mevcut:** Muzik analizi ve temel klip skorlama var.

**Eksikler ve duzeltmeler:**

- Sahne segmentasyonu eklenmeli: OpenCV histogram farki veya PySceneDetect benzeri yontemle kesim noktalari bulunmali.
- Klip skoru sahne bazina indirilmeli; tek klip icinden en iyi segmentler secilebilmeli.
- Fotoğraf kalite siralamasi eklenmeli: keskinlik, exposure, yuz/urun odagi ve boyut kriterleriyle skor uretilmeli.

**Dogrulama:** Ayni video icindeki dusuk kaliteli ve iyi kaliteli segmentler farkli skor almali.

### 3.2 Auto-Draft Kurgu

**Mevcut:** Beat zamanlarina gore basit timeline uretiliyor.

**Eksikler ve duzeltmeler:**

- Timeline sadece klip siralamamali, klip icinden uygun `clip_offset` secmeli.
- Tarz sablonlari beat araligi disinda gecis, tempo ve renk niyetini de tasimali.
- Gecis secimi eklenmeli: `hard_cut`, `dissolve`, `whip_pan` gibi alanlar timeline segmentlerine yazilmali.
- Klip tekrarini azaltan havuz mantigi eklenmeli.

**Dogrulama:** Fast cut daha kisa segmentler, corporate daha dengeli segmentler, warm/dark farkli gecis ve LUT tercihleri uretmeli.

### 3.3 Referans Profil Sistemi

**Mevcut:** `BrandProfile` modeli ve `/profiles` liste endpointi var.

**Eksikler ve duzeltmeler:**

- `reference_analyzer.py` eklenmeli.
- Referans video linki `yt-dlp` ile indirilmeli veya lokal referans dosyasi kabul edilmeli.
- Referanstan ortalama kesim hizi, renk tonu, gecis tipi ve tempo cikarilmali.
- `/profiles/analyze` endpointi profil JSON'u uretmeli.
- Profil yeni projeye uygulaninca style, LUT, cut duration ve transition tercihlerini etkilemeli.

**Dogrulama:** Kaydedilen profil `profiles/*.json` olarak gorunmeli ve yeni proje sihirbazinda secilebilmeli.

### 3.4 Renk Grading

**Mevcut:** LUT dosyalari ve DaVinci tool'u var.

**Eksikler ve duzeltmeler:**

- `DaVinciTool` Claude tool listesine eklenmeli veya render pipeline icinde opsiyonel adim olmali.
- Style -> LUT eslemesi timeline/render config icinde tasinmali.
- Color match icin sahne bazli exposure/white balance analizi eklenmeli.
- Kullanici chat ile "daha sicak", "daha kontrastli" gibi override verebilmeli.

**Dogrulama:** Style secimi degistiginde kullanilan LUT veya renk ayari degismeli.

### 3.5 Motion Graphics

**Mevcut:** After Effects tool'u logo reveal, text overlay ve flash transition uretebiliyor.

**Eksikler ve duzeltmeler:**

- AE tool Claude tool listesine baglanmali.
- Logo dosyasi UI'dan yuklenebilmeli ve proje state'ine girmeli.
- Logo reveal ciktilari ana timeline'a eklenmeli veya render oncesi overlay olarak birlestirilmeli.
- Text overlay icin UI/chat komutlarindan title/subtitle parametreleri alinmali.

**Dogrulama:** Logo yuklenen bir projede demo veya final ciktiya logo reveal/overlay eklenebilmeli.

### 3.6 Electron UI

**Mevcut:** Temel paneller, drag-drop, oynatici, timeline ve chat var.

**Eksikler ve duzeltmeler:**

- QA raporu icin skor, not, sorunlar ve onerileri gosteren panel eklenmeli.
- Proje kaydetme/acma UI'i eklenmeli.
- Marka profili secimi ve referans link input'u sihirbaza eklenmeli.
- Dark/light tema toggle'i eklenmeli.
- Demo ve final komutlari chat metnine bagli olmaktan cikarilip yapisal komut olarak gonderilmeli.

**Dogrulama:** Kullanici sihirbazdan profil secip demo alabilmeli, QA raporunu gorebilmeli ve projeyi tekrar acabilmeli.

---

## 4. Onceliklendirilmis Uygulama Fazlari

### Faz 1 - QA Akisi ve Kritik QA Hatalari

**Dosyalar:** `agent/claude_client.py`, `agent/qa/layer1_metrics.py`, `agent/qa/orchestrator.py`, `electron/renderer/app.js`

**Adimlar:**

- `QAOrchestrator` demo render sonrasina baglanir.
- Siyah kare komutu `ffmpeg blackdetect` ile duzeltilir.
- QA sonucu WebSocket result payload'una eklenir.
- UI chat veya rapor paneli QA sonucunu gosterir.

**Kabul kriteri:** Demo render sonrasi QA skoru ve notu kullaniciya gorunur.

### Faz 2 - Deterministik Demo/Final Render

**Dosyalar:** `agent/claude_client.py`, `agent/tools/ffmpeg_tool.py`, `electron/renderer/app.js`

**Adimlar:**

- Demo/final komutlari yapisal alanlarla agent'a gonderilir.
- Final render her durumda 4K H.265 olacak sekilde sabitlenir.
- FFmpeg komutlari shell string yerine arguman listesiyle calistirilir.
- Output metadata WebSocket sonucuna eklenir.

**Kabul kriteri:** Final butonu her zaman 4K HEVC cikti uretir.

### Faz 3 - Eksik REST Endpointleri

**Dosyalar:** `agent/main.py`, `agent/models/project.py`, `agent/models/profile.py`

**Adimlar:**

- `POST /projects` proje kaydeder.
- `GET /projects/{id}` proje okur.
- `POST /render/demo` demo render baslatir.
- `POST /render/final` final render baslatir.
- `POST /profiles/analyze` referans analizinden profil uretir.
- `GET /render/status/{id}` uzun render durumunu dondurur.

**Kabul kriteri:** TRD'de listelenen endpointler 404 donmez.

### Faz 4 - Fotoğraf ve Sahne Analizi

**Dosyalar:** `agent/tools/clip_scorer.py`, yeni `agent/tools/photo_scorer.py`, yeni `agent/tools/scene_segmenter.py`, `agent/tools/auto_editor.py`

**Adimlar:**

- Fotoğraflar kalite skoruna dahil edilir.
- Video ici sahneler segmentlere ayrilir.
- Timeline klip yerine segment secimi yapar.
- Fotoğraflar belirli sureli still segment olarak timeline'a eklenebilir.

**Kabul kriteri:** Sadece fotoğraf yuklenen projede demo akisi anlamli hata veya slideshow cikti uretir.

### Faz 5 - Referans Profil Sistemi

**Dosyalar:** yeni `agent/tools/reference_analyzer.py`, `agent/main.py`, `electron/renderer/wizard.js`

**Adimlar:**

- Referans link input'u eklenir.
- Kayitli marka profili secimi eklenir.
- Referans analizinden profil JSON'u olusturulur.
- Profil auto-draft, LUT ve gecis kararlarini etkiler.

**Kabul kriteri:** Kaydedilen profil yeni projede secilip timeline davranisini degistirir.

### Faz 6 - DaVinci ve AE Tool Entegrasyonu

**Dosyalar:** `agent/claude_client.py`, `agent/tools/davinci_tool.py`, `agent/tools/aftereffects_tool.py`

**Adimlar:**

- `apply_lut`, `apply_color_preset`, `logo_reveal`, `add_text_overlay`, `flash_transition` tool listesine eklenir.
- Tool hatalari kullaniciya anlasilir mesajla doner.
- DaVinci/AE yoksa FFmpeg fallback veya "ozellik kullanilamadi" raporu verilir.

**Kabul kriteri:** Claude, kullanici komutuyla LUT veya logo reveal tool'unu calistirabilir.

### Faz 7 - UI Tamamlama

**Dosyalar:** `electron/renderer/index.html`, `electron/renderer/app.js`, `electron/renderer/wizard.js`, `electron/renderer/styles.css`

**Adimlar:**

- QA raporu paneli eklenir.
- Proje kaydet/ac kontrolleri eklenir.
- Profil secimi ve referans linki sihirbaza eklenir.
- Tema toggle'i eklenir.
- Hata durumlari icin kullanici dostu mesajlar eklenir.

**Kabul kriteri:** PRD ana akisi UI uzerinden chat'e mecbur kalmadan tamamlanabilir.

### Faz 8 - Paketleme ve Uctan Uca Test

**Dosyalar:** `package.json`, `agent.spec`, `.env.example`, dokumantasyon dosyalari

**Adimlar:**

- `npm run build:agent` dogrulanir.
- `npm run build` dogrulanir.
- Paketlenmis uygulamada agent.exe basliyor mu kontrol edilir.
- Ilk acilis, demo render, QA raporu ve final render smoke test edilir.
- Kullaniciya FFmpeg/DaVinci/AE eksikleri icin net kurulum uyari sistemi eklenir.

**Kabul kriteri:** Windows installer kurulup 5 dakika icinde demo akisi baslatilabilir.

---

## 5. Test ve Kabul Kriterleri

### 5.1 Agent Testleri

- `python -m compileall agent` hatasiz calismali.
- `from agent.claude_client import ClaudeClient` import hatasiz olmali.
- `/health`, `/projects`, `/profiles`, `/luts`, `/render/demo`, `/render/final`, `/profiles/analyze` endpointleri beklenen status code dondurmeli.
- API key yoksa agent kontrollu hata mesaji vermeli.

### 5.2 FFmpeg Render Testleri

- Demo render 960x540 H.264 cikti uretmeli.
- Final render 3840x2160 H.265 cikti uretmeli.
- Muzikli ve muziksiz render ayrica test edilmeli.
- Ozel karakter ve bosluk iceren dosya yollarinda render kirilmamali.

### 5.3 QA Testleri

- Siyah video siyah kare olarak yakalanmali.
- Temiz video siyah kare uretmemeli.
- Beat-sync toleransi +/-100ms icinde hesaplanmali.
- Ses-video start offset farki rapora girmeli.
- QA hatasi render sonucunu tamamen kaybettirmemeli; kullanici cikti ve hata raporunu gormeli.

### 5.4 Electron Manuel Testleri

- Drag-drop ile video, fotoğraf, muzik ve logo eklenebilmeli.
- Sihirbazda proje tipi, tarz, muzik ve referans/profil secimi calismali.
- Demo butonu demo render baslatmali.
- Final butonu final render baslatmali.
- Oynatici demo/final ciktisini oynatmali.
- QA raporu gorunmeli.
- Agent crash durumunda UI kullaniciya durum bildirmeli.

### 5.5 Paketleme Testleri

- `npm run build:agent` agent.exe uretmeli.
- `npm run build` installer uretmeli.
- Kurulu uygulama `process.resourcesPath/agent.exe` dosyasini bulmali.
- Temiz Windows ortaminda ilk acilis smoke test edilmeli.

---

## 6. Riskler ve Teknik Notlar

- Claude tool secimine kritik urun davranislari birakilmamali. Demo, final ve QA gibi ana akislar deterministik backend komutlariyla yonetilmeli.
- FFmpeg komutlari shell string olarak kurulmamalidir. Arguman listesi kullanmak hem dosya yolu sorunlarini hem de komut enjeksiyonu riskini azaltir.
- DaVinci Resolve ve After Effects entegrasyonlari opsiyonel/harici arac bagimlidir. Bu araclar yoksa uygulama demo/final render akisini FFmpeg ile surdurebilmelidir.
- Vision QA medya karelerini API'ye gonderebilir. Gizlilik dokumantasyonunda bu acikca belirtilmelidir.
- Uzun render ve QA islemleri WebSocket'i bloklamamali; render status endpointi veya job sistemiyle takip edilmelidir.
- `profiles/`, `projects/` ve `temp/` klasorleri paketlenmis uygulamada yazilabilir dizin olarak ele alinmalidir. `resourcesPath` altina yazmak yerine kullanici data dizini tercih edilmelidir.
- TRD ve PRD, uygulama tamamlandikca guncellenmelidir; aksi halde dokumantasyon koddan hizla kopar.

---

## 7. Basari Tanimi

Bu duzeltme planinin tamamlanmis sayilmasi icin asagidaki uc ana akisin sorunsuz calismasi gerekir:

1. Kullanici medya ve muzik yukler, sihirbazdan tarz secer, demo render alir ve QA raporunu gorur.
2. Kullanici demo uzerinden final render ister ve sistem 4K H.265 cikti uretir.
3. Kullanici referans/profil, LUT ve motion graphics ozelliklerini kontrollu sekilde kullanabilir veya arac eksiginde net fallback mesaji alir.

