# AI Video Editor — Product Requirements Document (PRD)

**Versiyon:** 1.0  
**Tarih:** Mayıs 2026  
**Durum:** Aktif

---

## 1. Proje Özeti

AI Video Editor, marka ve reklam içerikleri üreten profesyoneller için tasarlanmış, yapay zeka destekli, tam entegre bir masaüstü video prodüksiyon asistanıdır.

Kullanıcı ham medyasını (video klip ve fotoğraf) ve müziğini sisteme yükler. Sistem otomatik analiz, kurgu ve renk grading yaparak onay için bir demo çıkarır. Kullanıcı bu demo üzerinden iteratif düzenlemeler yaparak final render'a ulaşır.

**Hedef kullanıcı:** Türkiye'de marka ve ürün reklamı çeken, müşterilere profesyonel iş teslim eden bireysel videograflar ve küçük prodüksiyon ekipleri.

**Platform:** Windows masaüstü uygulaması (.exe — Electron.js tabanlı)

---

## 2. Problem ve Hedef

### Problem

- Ham medyadan profesyonel bir demo çıkarmak saatler alır — klip seçimi, sıralama, müzik senkronizasyonu, renk düzeltme hepsi manuel yapılır.
- Render ayarları bilgisi gerektiren teknik bir adımdır; deneyimsiz kullanıcılar için engel oluşturur.
- Referans analizi tamamen göz kararı yapılır; marka tutarlılığını korumak zordur.
- Sistem kendi ürettiği edit'i denetleyemez; kalite kontrolü tamamen kullanıcıya bırakılmıştır.

### Hedef

- Medya yükleme → demo teslim süresini saatlerden dakikalara indirmek.
- Render bilgisi gerektirmeden profesyonel kalitede çıktı üretmek.
- Referans marka profillerini kaydederek marka tutarlılığını otomatize etmek.
- Sistem kendi kurgunun kalitesini denetleyip kullanıcıya raporlasın.

---

## 3. Kullanıcı Akışı

### Ana Akış

1. Kullanıcı uygulamayı açar — masaüstü ikonuna çift tıklar.
2. Medya yükleme ekranında video kliplerini ve fotoğraflarını sürükler.
3. **Proje Kurulum Sihirbazı** açılır (5 adım):
   - Adım 1: Proje tipi seçimi (ürün reklamı, düğün, sosyal medya, seyahat)
   - Adım 2: Edit tarzı seçimi (dark cinematic, fast cut, warm lifestyle, corporate)
   - Adım 3: Müzik seçimi (yüklenen dosya, AI önerisi veya sonraya bırak)
   - Adım 4: Referans video linki veya kayıtlı marka profili (isteğe bağlı)
   - Adım 5: Özet ekranı ve "Demo Oluştur" butonu
4. Sistem otomatik analiz yapar: müzik BPM, beat noktaları, klip kalite skorları.
5. Kurgu oluşturulur, demo render alınır (düşük çözünürlük, hızlı).
6. QA modülü otomatik devreye girer — 3 katman kontrol.
7. QA raporu ve demo kullanıcıya sunulur.
8. Kullanıcı chat üzerinden iteratif düzenlemeler yapar.
9. "Final Render" komutu verilir — 4K, H.265, müşteri formatında çıkar.

### Sihirbaz Validasyon Kuralları

- Adım 1, 2 ve 3 zorunludur — seçim yapılmadan "Devam" butonu kilitlidir.
- Adım 4 isteğe bağlıdır — referans olmadan da ilerlenebilir.
- Seçim yapılmadan devam denenirse uyarı mesajı gösterilir.

---

## 4. Özellik Listesi

### 4.1 Otomatik Analiz Motoru

| Özellik | Açıklama | Öncelik |
|---------|----------|---------|
| Müzik analizi | BPM, beat noktaları, drop tespiti (librosa) | Yüksek |
| Klip skorlama | Hareket yoğunluğu, ışık kalitesi, odak puanlaması (opencv) | Yüksek |
| Sahne segmentasyonu | Videolarda otomatik sahne kesim noktası tespiti | Yüksek |
| En iyi kare seçimi | Fotoğrafları otomatik kalite sıralaması | Orta |

### 4.2 Otomatik Kurgu (Auto-Draft)

| Özellik | Açıklama | Öncelik |
|---------|----------|---------|
| Beat-sync kurgu | Müzik beatlerine göre otomatik klip sıralama | Yüksek |
| Tarz şablonları | Dark cinematic, warm lifestyle, fast-cut, corporate | Yüksek |
| Geçiş seçimi | Hard cut, dissolve, whip pan — tarza göre otomatik | Yüksek |
| Demo render | Hızlı düşük çözünürlüklü önizleme (FFmpeg) | Yüksek |

### 4.3 Referans Profil Sistemi

| Özellik | Açıklama | Öncelik |
|---------|----------|---------|
| Referans analizi | Video linkinden kesim hızı, renk tonu, geçiş tipi çıkarımı | Yüksek |
| Profil kaydetme | Marka bazında profil kaydı ve tekrar kullanımı | Orta |
| Profil uygulama | Kaydedilmiş profili yeni projeye tek komutla uygulama | Orta |

### 4.4 Renk Grading (DaVinci Resolve)

| Özellik | Açıklama | Öncelik |
|---------|----------|---------|
| LUT uygulaması | Referans veya tarz bazında otomatik LUT seçimi | Yüksek |
| Color match | Sahne bazında otomatik exposure ve white balance | Yüksek |
| Tarz bazlı grading | Dark/warm/cool/desaturate profil uygulaması | Orta |
| Manuel override | Kullanıcının komutla renk değişikliği talep edebilmesi | Orta |

### 4.5 Motion Graphics (After Effects)

| Özellik | Açıklama | Öncelik |
|---------|----------|---------|
| Logo reveal | Marka logosunun animasyonlu ekrana girişi | Yüksek |
| Metin animasyonu | Alt başlık, ürün adı, fiyat gibi metin overlay'leri | Yüksek |
| Geçiş efektleri | Flash, glitch — tarza göre seçim | Orta |
| ExtendScript kontrolü | Python agent'tan AE'ye otomatik komut gönderimi | Yüksek |

### 4.6 QA Modülü — Kalite Kontrol

| Özellik | Açıklama | Öncelik |
|---------|----------|---------|
| Katman 1 — Metrik | Beat sync, siyah kare, ses-video senkron, klip tekrarı | Yüksek |
| Katman 2 — Claude | Timeline mantığı, tarz uyumu, açılış/kapanış gücü | Yüksek |
| Katman 3 — Vision | Frame bazlı görsel kalite, kompozisyon, profesyonellik | Yüksek |
| Otomatik düzeltme | Kritik sorunları kullanıcı onayı olmadan düzeltme | Orta |
| QA raporu | Birleşik skor (0–100), not (A–F), öneri listesi | Yüksek |

### 4.7 Final Render

| Özellik | Açıklama | Öncelik |
|---------|----------|---------|
| 4K H.265 render | Müşteri teslim kalitesinde final export | Yüksek |
| Format seçenekleri | MP4, MOV, sosyal medya optimize formatları | Orta |
| Render profili | Bir kez ayarla, her projede otomatik uygula | Orta |

### 4.8 Masaüstü Uygulama (Electron.js)

| Özellik | Açıklama | Öncelik |
|---------|----------|---------|
| Kurulabilir .exe | Çift tıkla açılan Windows masaüstü uygulaması | Yüksek |
| Sürükle-bırak | Medya dosyalarını doğrudan uygulamaya sürükleme | Yüksek |
| Dahili oynatıcı | Demo ve final render'ı uygulama içinde izleme | Yüksek |
| Chat arayüzü | Claude ile iteratif düzenleme için chat paneli | Yüksek |
| Hızlı komutlar | Sık kullanılan işlemler için tek tıklık butonlar | Orta |
| Dark/Light tema | Kullanıcı seçimine göre tema geçişi | Orta |
| Proje yönetimi | Proje kaydetme, açma, marka profil arşivi | Orta |

---

## 5. Teknoloji Stack

| Teknoloji | Rol | Zorunlu mu? |
|-----------|-----|-------------|
| FFmpeg | Video render, kesim, birleştirme, ses sync | Zorunlu |
| DaVinci Resolve | Profesyonel renk grading, LUT yönetimi | Zorunlu |
| After Effects | Motion graphics, logo animasyonu | Opsiyonel |
| Premiere Pro | İleri timeline düzenleme | Opsiyonel |
| Electron.js | Masaüstü uygulama çatısı (Windows .exe) | Zorunlu |
| Python + FastAPI | Local agent, araç köprüsü | Zorunlu |
| librosa | Müzik analizi, BPM, beat tespiti | Zorunlu |
| opencv | Video sahne analizi, klip skorlama | Zorunlu |
| moviepy | Python içi video manipülasyon | Zorunlu |
| Anthropic Claude API | Komut yorumlama, karar motoru, QA | Zorunlu |

---

## 6. Sistem Mimarisi (Genel)

```
Kullanıcı (Electron Arayüzü)
        ↓ WebSocket
Python Local Agent (FastAPI)
        ↓
Claude API (Karar Motoru)
        ↓
Lokal Araçlar: FFmpeg | DaVinci Resolve | After Effects
        ↓
Çıktı: Demo MP4 → QA → Final 4K Render
```

### 4 Katmanlı Yapı

**Katman 1 — Arayüz (Electron.js)**
Kullanıcı ile tek iletişim noktası. Medya yükleme, tarz seçimi, chat paneli, video oynatıcı.

**Katman 2 — Beyin (Claude API)**
Kullanıcı komutlarını yorumlar, hangi aracın çalışacağına karar verir, kurgu ve QA kararları üretir.

**Katman 3 — Eller (Python Local Agent)**
Claude kararlarını alır, lokal araçlara iletir, sonuçları Claude'a bildirir.

**Katman 4 — Araçlar**
FFmpeg, DaVinci Resolve, After Effects, Python kütüphaneleri.

---

## 7. Geliştirme Planı

| Faz | Modül | Kapsam | Tahmini Süre |
|-----|-------|--------|--------------|
| 1 | Temel Altyapı | FFmpeg, Python agent, Electron iskelet | 1–2 hafta |
| 2 | Analiz Motoru | librosa, opencv, beat-sync kurgu | 2–3 hafta |
| 3 | Claude Entegrasyonu | API bağlantısı, tool döngüsü, iteratif düzenleme | 1–2 hafta |
| 4 | Renk & Grafik | DaVinci Resolve, After Effects, LUT sistemi | 2–3 hafta |
| 5 | QA Modülü | 3 katman kalite kontrol, otomatik düzeltme | 1–2 hafta |
| 6 | Paketleme | Windows .exe installer | 1 hafta |

---

## 8. Kapsam Dışı (v1.0)

- Rotoscoping veya obje takibi — manuel After Effects işi gerektirir
- Yapay zeka ile ses üretimi veya voiceover
- Bulut tabanlı render — tüm işlem lokalde yapılır
- macOS veya Linux desteği — v1.0 yalnızca Windows
- Çok kullanıcılı veya ekip özellikleri
- Otomatik sosyal medya yükleme

---

## 9. Başarı Kriterleri

- Ham medyadan demo render'a geçiş süresi 10 dakikanın altında
- Final render kalitesi: en az 1080p H.264, hedef 4K H.265
- Beat-sync hassasiyeti: kesim noktaları ±100ms tolerans içinde
- QA modülü beat senkronunu, siyah kareleri ve ses-video senkronunu tespit ediyor
- Referans profil analizi renk tonu ve kesim hızını doğru sınıflandırıyor
- Uygulama kurulumu: standart Windows .exe installer ile 5 dakika altında

---

*Bu PRD yaşayan bir belgedir. Geliştirme sürecinde güncellenecektir.*
