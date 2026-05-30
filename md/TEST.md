# AI Video Editor - Kapsamli Test Plani

**Versiyon:** 1.0  
**Tarih:** Mayis 2026  
**Durum:** Test Stratejisi  
**Bagli belge:** PRD.md, TRD.md, FIX_PLAN.md

---

## 1. Amac ve Kapsam

Bu belge, AI Video Editor projesinin PRD'deki tum ozelliklerini, mevcut kod modullerini, kritik hata yollarini ve en uc kullanim senaryolarini test etmek icin hazirlanmistir. Hedef, hicbir ozellik, bolum, API, fonksiyon veya urun akisinin test disinda kalmamasidir.

Test kapsami su alanlari icerir:

- Windows masaustu uygulamasi ve Electron UI.
- Python FastAPI local agent ve WebSocket protokolu.
- Claude tool dongusu ve kullanici komut yorumlama akisi.
- FFmpeg, librosa, OpenCV, moviepy ve dosya tabanli medya islemleri.
- Otomatik analiz, auto-draft, demo render, final render.
- Referans profil sistemi, LUT/color grading, motion graphics.
- 3 katman QA modulu ve otomatik duzeltme davranislari.
- Paketleme, installer, ilk acilis ve temiz Windows kurulumu.
- Performans, guvenlik, gizlilik, hata toleransi ve regresyon testleri.

---

## 2. Test Seviyeleri

| Seviye | Amac | Kapsam |
|--------|------|--------|
| Statik kontrol | Kod ve dokuman uyumsuzluklarini erken yakalamak | import, compile, lint, dependency, dosya varligi |
| Unit test | Tek fonksiyon/sinif davranisini izole dogrulamak | `agent/tools`, `agent/qa`, modeller |
| Integration test | Modul baglantilarini dogrulamak | Claude tool -> FFmpeg, render -> QA, REST -> dosya sistemi |
| E2E test | PRD ana kullanici akisini dogrulamak | medya yukle -> sihirbaz -> demo -> QA -> revizyon -> final |
| Manual UI test | Electron ekranlarini ve kullanici deneyimini dogrulamak | drag-drop, oynatici, chat, tema, proje yonetimi |
| Paket test | Kurulabilir Windows urununu dogrulamak | agent.exe, installer, resources, ilk acilis |
| Stress/edge test | Uc durumlarda kirilma, veri kaybi ve yanlis sonuc aramak | bozuk medya, uzun dosya yolu, Unicode adlar, buyuk projeler |

---

## 3. Test Ortamlari

### 3.1 Zorunlu Ortamlar

| Ortam | Test Edilecekler |
|-------|------------------|
| Windows 11 x64, gelistirme modu | Tum unit, integration, UI ve E2E testleri |
| Windows 10 x64, temiz kurulum | Installer, ilk acilis, FFmpeg/agent paket davranisi |
| Internet var | Claude, reference URL, yt-dlp, Vision QA |
| Internet yok | Offline hata mesaji, lokal render, Claude fallback |
| FFmpeg PATH'te var | Normal render ve QA |
| FFmpeg yok | Kullaniciya kurulum hatasi, agent'in kontrollu fail etmesi |
| DaVinci Resolve yok | Color grading fallback |
| DaVinci Resolve var | LUT apply, Resolve bridge |
| After Effects yok | Motion graphics fallback |
| After Effects var | logo reveal, text overlay, transition render |

### 3.2 Test Verisi Klasoru

Onerilen test verisi dizini:

```text
test_assets/
  video/
  photo/
  audio/
  logo/
  reference/
  expected/
```

Bu klasor repo'ya buyuk binary dosyalarla commit edilmemeli. Hafif fixture dosyalari gerekiyorsa sentetik FFmpeg komutlariyla test sirasinda uretilmelidir.

---

## 4. Test Verisi Matrisi

### 4.1 Video Dosyalari

| ID | Veri | Amac |
|----|------|------|
| VID-001 | 5 sn 1080p temiz MP4, H.264, sesli | Smoke demo render |
| VID-002 | 5 sn 4K MP4 | Final 4K render ve downscale/upscale |
| VID-003 | 1 sn tamamen siyah video | QA siyah kare tespiti |
| VID-004 | Ortasinda 0.2 sn siyah kare olan video | QA kisa siyah kare tespiti |
| VID-005 | Sessiz video | AV sync ve audio fallback |
| VID-006 | Sadece audio stream, video yok | Gecersiz video hatasi |
| VID-007 | Bozuk MP4 header | Hata toleransi |
| VID-008 | Degisken FPS video | timeline/render stabilitesi |
| VID-009 | Dikey 9:16 video | sosyal medya format ve player davranisi |
| VID-010 | Kare 1:1 video | format secenekleri |
| VID-011 | Cok karanlik video | klip skor exposure |
| VID-012 | Asiri parlak video | klip skor exposure |
| VID-013 | Bulanik video | odak/keskinlik skoru |
| VID-014 | Cok hareketli video | hareket yogunlugu skoru |
| VID-015 | Sabit tripod video | dusuk hareket skoru |
| VID-016 | 100 adet kisa klip | performans ve repeat kontrolu |
| VID-017 | Uzun 30 dk video | sahne segmentasyonu ve sure limiti |
| VID-018 | Dosya adi bosluklu video | path handling |
| VID-019 | Dosya adi ozel karakterli video: `clip & cut [v1].mp4` | shell/path guvenligi |
| VID-020 | Unicode dosya adi: `çalışma_ürün_ışık.mp4` | Windows Unicode path |

### 4.2 Fotoğraf Dosyalari

| ID | Veri | Amac |
|----|------|------|
| IMG-001 | Net JPG | en iyi kare secimi |
| IMG-002 | Bulanik JPG | dusuk kalite skoru |
| IMG-003 | Cok karanlik JPG | exposure skoru |
| IMG-004 | Cok parlak JPG | exposure skoru |
| IMG-005 | PNG transparan logo olmayan gorsel | foto import |
| IMG-006 | CMYK JPG | decoder uyumlulugu |
| IMG-007 | Cok buyuk 8000px gorsel | bellek ve resize |
| IMG-008 | Bozuk JPG | hata toleransi |
| IMG-009 | Sadece fotoğraf projesi icin 20 dosya | slideshow/demo fallback |

### 4.3 Ses Dosyalari

| ID | Veri | Amac |
|----|------|------|
| AUD-001 | 120 BPM duzenli beat MP3 | BPM ve beat dogrulugu |
| AUD-002 | Degisken BPM muzik | beat analizi toleransi |
| AUD-003 | Sessizlik audio | BPM yok/fallback |
| AUD-004 | WAV 48kHz stereo | format uyumlulugu |
| AUD-005 | FLAC | format uyumlulugu |
| AUD-006 | Bozuk MP3 | hata toleransi |
| AUD-007 | 10 dk muzik | performans |
| AUD-008 | Drop noktasi belirgin muzik | drop tespiti |

### 4.4 Logo ve Referans

| ID | Veri | Amac |
|----|------|------|
| LOGO-001 | PNG transparan logo | AE logo reveal |
| LOGO-002 | SVG logo | desteklenmeyen/convert ihtiyaci |
| LOGO-003 | Cok buyuk PNG | resize ve bellek |
| REF-001 | Lokal referans video | profil analizi |
| REF-002 | YouTube/Vimeo linki | yt-dlp analiz |
| REF-003 | Gecersiz link | hata mesaji |
| REF-004 | Gizli/erisim olmayan link | hata mesaji |

---

## 5. PRD Ozellik Kapsam Matrisi

| PRD Ozelligi | Test ID Grubu | Kabul Kriteri |
|--------------|---------------|---------------|
| Muzik analizi | ANL-MUS-* | BPM, beat, drop, sure alanlari dogru ve hata durumlari kontrollu |
| Klip skorlama | ANL-CLIP-* | hareket, isik, odak skorlanir; bozuk dosya sistemi bozmaz |
| Sahne segmentasyonu | ANL-SCENE-* | kesim noktalari dogru bulunur, uzun videoda sure asimi olmaz |
| En iyi kare secimi | ANL-PHOTO-* | fotoğraflar kaliteye gore siralanir |
| Beat-sync kurgu | DRAFT-BEAT-* | kesimler beat'e +/-100ms toleransla oturur |
| Tarz sablonlari | DRAFT-STYLE-* | dark, fast, warm, corporate farkli timeline davranisi verir |
| Gecis secimi | DRAFT-TRANS-* | tarz bazli hard cut/dissolve/whip pan secilir |
| Demo render | RENDER-DEMO-* | hizli dusuk cozunurluk preview uretilir |
| Referans analizi | PROF-REF-* | kesim hizi, renk tonu, gecis tipi cikarilir |
| Profil kaydetme | PROF-SAVE-* | profil JSON olarak saklanir |
| Profil uygulama | PROF-APPLY-* | profil yeni projeyi etkiler |
| LUT uygulamasi | COLOR-LUT-* | stil veya profil LUT'u uygulanir |
| Color match | COLOR-MATCH-* | exposure/white balance tutarliligi artar |
| Manuel renk override | COLOR-OVR-* | chat komutuyla renk niyeti degisir |
| Logo reveal | AE-LOGO-* | logo animasyonu uretilir ve render'a girer |
| Metin animasyonu | AE-TEXT-* | title/subtitle overlay uretilir |
| Gecis efektleri | AE-TRANS-* | flash/glitch gecis eklenir |
| ExtendScript kontrolu | AE-EXT-* | Python agent AE komutu calistirir |
| QA Katman 1 | QA-L1-* | beat, siyah kare, AV sync, tekrar yakalanir |
| QA Katman 2 | QA-L2-* | timeline mantigi JSON raporlanir |
| QA Katman 3 | QA-L3-* | frame kalite analizi raporlanir |
| Otomatik duzeltme | QA-FIX-* | kritik sorunlar onay gerektirmeden duzeltilir veya raporlanir |
| QA raporu | QA-REPORT-* | 0-100 skor, A-F not, oneriler gorunur |
| 4K H.265 final | RENDER-FINAL-* | final HEVC ve 4K uretilir |
| Format secenekleri | RENDER-FORMAT-* | MP4/MOV/sosyal medya presetleri dogrulanir |
| Render profili | RENDER-PROFILE-* | kayitli profil tekrar kullanilir |
| Kurulabilir exe | PKG-* | installer kurulur ve uygulama acilir |
| Drag-drop | UI-DND-* | medya uygulamaya suruklenir |
| Dahili oynatici | UI-PLAYER-* | demo/final oynatilir |
| Chat arayuzu | UI-CHAT-* | iteratif komutlar agent'a gider |
| Hizli komutlar | UI-QUICK-* | demo/final/QA/acikla butonlari calisir |
| Dark/Light tema | UI-THEME-* | tema degisir ve kalici olur |
| Proje yonetimi | UI-PROJECT-* | proje kaydet/ac/profil arsivi calisir |

---

## 6. Backend ve Fonksiyon Bazli Testler

### 6.1 `agent/main.py`

| ID | Fonksiyon/Endpoint | Senaryo | Beklenen |
|----|--------------------|---------|----------|
| AG-MAIN-001 | `health` | GET `/health` | `status=ok`, client sayisi doner |
| AG-MAIN-002 | `list_projects` | `projects/` bos | bos liste doner, klasor olusur |
| AG-MAIN-003 | `list_projects` | gecersiz JSON dosyasi var | listeleme kirilmaz |
| AG-MAIN-004 | `list_profiles` | profil JSON'lari var | stem listesi doner |
| AG-MAIN-005 | `list_luts` | LUT klasoru dolu | cube dosyalari listelenir |
| AG-MAIN-006 | `websocket_endpoint` | gecerli komut | progress ve result mesajlari akar |
| AG-MAIN-007 | `websocket_endpoint` | bos komut | error mesaji doner |
| AG-MAIN-008 | `websocket_endpoint` | client aniden kopar | server client listesini temizler |
| AG-MAIN-009 | `handle_command` | Claude hata firlatir | WebSocket error mesaji doner |
| AG-MAIN-010 | CORS | Electron origin | izinli olur |
| AG-MAIN-011 | CORS | yabanci origin | beklenen policy uygulanir |

### 6.2 `agent/claude_client.py`

| ID | Fonksiyon | Senaryo | Beklenen |
|----|-----------|---------|----------|
| CLD-001 | `__init__` | API key var | client ve tool siniflari olusur |
| CLD-002 | `__init__` | API key yok | kontrollu hata/fallback |
| CLD-003 | `process` | bos command | `Komut bos olamaz` error |
| CLD-004 | `process` | normal demo komutu | progress -> tool_use -> result sirasi |
| CLD-005 | `process` | Claude API timeout | kullaniciya hata, agent crash yok |
| CLD-006 | `process` | Claude gecersiz tool ister | bilinmeyen arac hatasi |
| CLD-007 | `_run_tool` | `analyze_music` | muzik analiz sonucu doner |
| CLD-008 | `_run_tool` | `score_clips` | skor listesi doner |
| CLD-009 | `_run_tool` | `build_timeline` | context timeline set edilir |
| CLD-010 | `_run_tool` | `render_timeline` | output_path doner |
| CLD-011 | `_run_tool` | `run_ffmpeg` | operation sonucunu doner |
| CLD-012 | `_render_timeline` | bos timeline | anlamli error |
| CLD-013 | `_render_timeline` | bir segment trim fail | diger segmentlerle devam veya rapor |
| CLD-014 | `_render_timeline` | tum trim fail | `Hicbir segment trim edilemedi` |
| CLD-015 | `_render_timeline` | concat fail | stderr ozetli error |
| CLD-016 | `_render_timeline` | demo + muzik | 960x540 H.264 + AAC cikti |
| CLD-017 | `_render_timeline` | final + muzik | 3840x2160 H.265 + AAC cikti |
| CLD-018 | `_render_timeline` | output path yazilamaz | anlamli error |
| CLD-019 | `_handle_ffmpeg` | trim | dogru output uretir |
| CLD-020 | `_handle_ffmpeg` | concat | dogru output uretir |
| CLD-021 | `_handle_ffmpeg` | demo_render | context last_output set edilir |
| CLD-022 | `_handle_ffmpeg` | final_render | 4K H.265 cikti |
| CLD-023 | `_handle_ffmpeg` | bilinmeyen op | error doner |
| CLD-024 | `_auto_path` | coklu cagrilar | benzersiz veya overwrite guvenli path |
| CLD-025 | `_build_prompt` | tum medya var | clips/photos/music/logo promptta var |
| CLD-026 | `_build_prompt` | medya yok | prompt kirilmaz |

### 6.3 `agent/tools/music_analyzer.py`

| ID | Fonksiyon | Senaryo | Beklenen |
|----|-----------|---------|----------|
| ANL-MUS-001 | `MusicAnalyzer.analyze` | 120 BPM MP3 | BPM tolerans icinde |
| ANL-MUS-002 | `analyze` | WAV 48kHz | sample_rate dogru |
| ANL-MUS-003 | `analyze` | sessiz audio | sifir/duzgun fallback, crash yok |
| ANL-MUS-004 | `analyze` | bozuk MP3 | `error` doner |
| ANL-MUS-005 | `analyze` | cok uzun audio | sure limiti veya makul zamanda tamam |
| ANL-MUS-006 | `analyze` | drop belirgin audio | drop_times bos degil |
| ANL-MUS-007 | `analyze` | dosya yok | error doner |
| ANL-MUS-008 | `analyze` | Unicode path | dosya okunur |

### 6.4 `agent/tools/clip_scorer.py`

| ID | Fonksiyon | Senaryo | Beklenen |
|----|-----------|---------|----------|
| ANL-CLIP-001 | `ClipScorer.score` | tek temiz klip | skor listesi 1 eleman |
| ANL-CLIP-002 | `score` | coklu klip | total_score desc siralanir |
| ANL-CLIP-003 | `score` | dosya yok | atlanir, crash yok |
| ANL-CLIP-004 | `_score_clip` | karanlik video | brightness dusuk |
| ANL-CLIP-005 | `_score_clip` | parlak video | brightness yuksek |
| ANL-CLIP-006 | `_score_clip` | bulanik video | sharpness dusuk |
| ANL-CLIP-007 | `_score_clip` | hareketli video | motion yuksek |
| ANL-CLIP-008 | `_score_clip` | bozuk video | total_score 0 ve error |
| ANL-CLIP-009 | `_score_clip` | 0 frame video | kare okunamadi error |
| ANL-CLIP-010 | `_score_clip` | dikey video | skor hesaplanir |

### 6.5 `agent/tools/auto_editor.py`

| ID | Fonksiyon | Senaryo | Beklenen |
|----|-----------|---------|----------|
| DRAFT-001 | `build_timeline` | dark style | 4 beat/sahne |
| DRAFT-002 | `build_timeline` | fast style | 1 beat/sahne |
| DRAFT-003 | `build_timeline` | warm style | 3 beat/sahne |
| DRAFT-004 | `build_timeline` | corp style | 2 beat/sahne |
| DRAFT-005 | `build_timeline` | bilinmeyen style | default davranis |
| DRAFT-006 | `build_timeline` | bos scored_clips | bos timeline |
| DRAFT-007 | `build_timeline` | bos beat_times | bos timeline |
| DRAFT-008 | `build_timeline` | beat music_duration disinda | disaridaki beat atlanir |
| DRAFT-009 | `build_timeline` | cok kisa segment | segment atlanir |
| DRAFT-010 | `build_timeline` | az klip cok beat | repeat kontrolu raporlanir |
| DRAFT-011 | `write_concat_list` | normal timeline | concat list dosyasi olusur |
| DRAFT-012 | `write_concat_list` | bos timeline | bos/guvenli liste |

### 6.6 `agent/tools/ffmpeg_tool.py`

| ID | Fonksiyon | Senaryo | Beklenen |
|----|-----------|---------|----------|
| FFM-001 | `find_ffmpeg` | PATH'te ffmpeg var | binary path doner |
| FFM-002 | `find_ffmpeg` | PATH'te yok, C:\ffmpeg var | fallback path doner |
| FFM-003 | `find_ffmpeg` | hic yok | kontrollu hata/uyari |
| FFM-004 | `FFmpegTool.run` | gecerli komut | success true |
| FFM-005 | `run` | gecersiz input | success false, stderr_tail |
| FFM-006 | `run` | path bosluklu | basarili |
| FFM-007 | `run` | ozel karakterli path | shell injection yok |
| FFM-008 | `trim_cmd` | 0-2 sn trim | dogru sure |
| FFM-009 | `trim_cmd` | negatif start | reddedilir veya normalize edilir |
| FFM-010 | `trim_cmd` | duration 0 | error |
| FFM-011 | `concat_cmd` | iki segment | tek video |
| FFM-012 | `concat_cmd` | codec mismatch | anlamli fail |
| FFM-013 | `render_cmd` | 1080p render | H.264 output |
| FFM-014 | `render_4k_cmd` | final render | 3840x2160 HEVC |
| FFM-015 | `demo_render_cmd` | demo render | 960x540 H.264 |
| FFM-016 | `get_duration` | normal video | sure > 0 |
| FFM-017 | `get_duration` | bozuk video | 0 veya error fallback |
| FFM-018 | `get_video_info` | normal video | streams/format JSON |
| FFM-019 | `get_video_info` | bozuk JSON | bos dict |

### 6.7 `agent/qa/layer1_metrics.py`

| ID | Fonksiyon | Senaryo | Beklenen |
|----|-----------|---------|----------|
| QA-L1-001 | `MetricQA.run` | tum inputlar var | overall_score 0-100 |
| QA-L1-002 | `run` | checker exception | ilgili check score 50, crash yok |
| QA-L1-003 | `_check_beat_sync` | kesimler beat uzerinde | score 100'e yakin |
| QA-L1-004 | `_check_beat_sync` | 200ms sapma | score duser |
| QA-L1-005 | `_check_beat_sync` | muzik yok | score 50 note |
| QA-L1-006 | `_check_black_frames` | siyah video | black_events > 0 |
| QA-L1-007 | `_check_black_frames` | temiz video | black_events 0 |
| QA-L1-008 | `_check_black_frames` | FFmpeg hata | score 100 verilmez |
| QA-L1-009 | `_check_av_sync` | sync video | diff_ms dusuk |
| QA-L1-010 | `_check_av_sync` | audio offset | diff_ms yuksek |
| QA-L1-011 | `_check_av_sync` | audio yok | note doner |
| QA-L1-012 | `_check_duration` | muzik-video ayni sure | score 100 |
| QA-L1-013 | `_check_duration` | 10 sn fark | score duser |
| QA-L1-014 | `_check_clip_repeat` | tekrar az | score 100 |
| QA-L1-015 | `_check_clip_repeat` | tek klip cok tekrar | score dusuk |
| QA-L1-016 | `_check_color_consistency` | tutarli renk | score yuksek |
| QA-L1-017 | `_check_color_consistency` | farkli renk sahneleri | score duser |

### 6.8 `agent/qa/layer2_claude.py`

| ID | Fonksiyon | Senaryo | Beklenen |
|----|-----------|---------|----------|
| QA-L2-001 | `ClaudeQA.run` | gecerli JSON yanit | score ve fields parse edilir |
| QA-L2-002 | `run` | markdown JSON bloğu | temizlenip parse edilir |
| QA-L2-003 | `run` | bozuk JSON | fallback_result |
| QA-L2-004 | `run` | API timeout | fallback_result |
| QA-L2-005 | `_build_prompt` | timeline dolu | opening/closing/metrikler promptta |
| QA-L2-006 | `_build_prompt` | timeline bos | prompt kirilmaz |
| QA-L2-007 | `_fallback_result` | hata metni | issues icinde hata |

### 6.9 `agent/qa/layer3_vision.py`

| ID | Fonksiyon | Senaryo | Beklenen |
|----|-----------|---------|----------|
| QA-L3-001 | `VisionQA.run` | video var | frames_analyzed > 0 |
| QA-L3-002 | `run` | video yok | score 50 error |
| QA-L3-003 | `_select_timestamps` | timeline + drop var | acilis, ilk sahneler, drop, son sahne |
| QA-L3-004 | `_select_timestamps` | cok uzun timeline | max 7 timestamp |
| QA-L3-005 | `_extract_frames` | gecerli video | jpg dosyalari olusur |
| QA-L3-006 | `_extract_frames` | timestamp video disinda | ilgili frame atlanir |
| QA-L3-007 | `_analyze_frames` | coklu frame | her frame icin sonuc |
| QA-L3-008 | `_analyze_single_frame` | gecerli Claude JSON | overall parse edilir |
| QA-L3-009 | `_analyze_single_frame` | bozuk JSON | overall 50 |
| QA-L3-010 | `_compute_score` | skorlar var | ortalama |
| QA-L3-011 | `_compute_score` | bos liste | 50 |

### 6.10 `agent/qa/orchestrator.py`

| ID | Fonksiyon | Senaryo | Beklenen |
|----|-----------|---------|----------|
| QA-ORCH-001 | `QAOrchestrator.run` | tum katmanlar basarili | final_score agirlikli ortalama |
| QA-ORCH-002 | `run` | Layer 2 fallback | rapor uretilir |
| QA-ORCH-003 | `run` | Layer 3 fallback | rapor uretilir |
| QA-ORCH-004 | `_collect_auto_fixes` | siyah kare var | fix onerisi |
| QA-ORCH-005 | `_collect_auto_fixes` | AV desync var | fix onerisi |
| QA-ORCH-006 | `_collect_auto_fixes` | sure farki var | fix onerisi |
| QA-ORCH-007 | `_grade` | 90+ | A |
| QA-ORCH-008 | `_grade` | 75-89 | B |
| QA-ORCH-009 | `_grade` | 60-74 | C |
| QA-ORCH-010 | `_grade` | 45-59 | D |
| QA-ORCH-011 | `_grade` | <45 | F |
| QA-ORCH-012 | `quick_check` | sadece Layer 1 | hizli rapor |

### 6.11 DaVinci, Resolve Bridge ve Launcher

| ID | Modul/Fonksiyon | Senaryo | Beklenen |
|----|-----------------|---------|----------|
| COLOR-DV-001 | `DaVinciTool.check_connection` | bridge hazir | connected true |
| COLOR-DV-002 | `check_connection` | Resolve kapali | error ve rehber mesaj |
| COLOR-DV-003 | `apply_lut` | LUT var | applied sayisi > 0 |
| COLOR-DV-004 | `apply_lut` | LUT yok | error |
| COLOR-DV-005 | `apply_color_preset` | dark/warm/corp/fast | dogru LUT secilir |
| COLOR-DV-006 | `import_clips` | gecerli klipler | imported count |
| COLOR-DV-007 | `create_timeline_from_clips` | gecerli klipler | timeline olusur |
| COLOR-DV-008 | `render` | aktif timeline | output_path uretilir |
| COLOR-DV-009 | `get_project_info` | aktif proje | proje/timeline bilgisi |
| COLOR-DV-010 | `bridge_command` | komut uretimi | resolve_bridge path dogru |
| COLOR-RB-001 | `resolve_bridge.py` | `check` op | version/project/timeline |
| COLOR-RB-002 | `resolve_bridge.py` | bilinmeyen op | error |
| COLOR-RB-003 | `resolve_bridge.py` | proje yok | kontrollu error |
| COLOR-RL-001 | `ResolveLauncher.ensure_ready` | bridge zaten hazir | true |
| COLOR-RL-002 | `ensure_ready` | Resolve yok | false/error |
| COLOR-RL-003 | `_ping_bridge` | sonuc dosyasi gecersiz | false, crash yok |

### 6.12 After Effects ve Premiere Tool Testleri

| ID | Modul/Fonksiyon | Senaryo | Beklenen |
|----|-----------------|---------|----------|
| AE-001 | `_find_ae_dir` | AE kurulu | path bulunur |
| AE-002 | `_find_ae_dir` | AE yok | fallback path ve anlamli fail |
| AE-003 | `_run_jsx` | basit JSX | ok true |
| AE-004 | `_run_jsx` | timeout | ok false |
| AE-005 | `_aerender` | gecerli AEP | output uretilir |
| AE-006 | `logo_reveal` | PNG logo | MP4 logo reveal |
| AE-007 | `logo_reveal` | logo yok | error |
| AE-008 | `add_text_overlay` | title/subtitle | MP4 overlay |
| AE-009 | `add_text_overlay` | tirnakli metin | escape dogru |
| AE-010 | `flash_transition` | 0.5 sn | transition MP4 |
| AE-011 | `is_ae_running` | AE acik/kapali | dogru bool |
| PP-001 | `_find_pp_dir` | Premiere kurulu | path bulunur |
| PP-002 | `PremiereTool.create_sequence` | klip listesi | sequence/proje |
| PP-003 | `export_sequence` | gecerli proje | output |
| PP-004 | `apply_lumetri` | style dark/warm/corp/fast | lumetri parametreleri |
| PP-005 | `is_pp_running` | PP acik/kapali | dogru bool |

### 6.13 Pydantic Modeller

| ID | Model | Senaryo | Beklenen |
|----|-------|---------|----------|
| MODEL-001 | `MediaFiles` | bos init | listeler bos |
| MODEL-002 | `MediaFiles` | clips/photos/music/logo | alanlar korunur |
| MODEL-003 | `ProjectConfig` | tum required alanlar | model valid |
| MODEL-004 | `ProjectConfig` | eksik required | validation error |
| MODEL-005 | `CommandMessage` | files null | valid |
| MODEL-006 | `BrandProfile` | tum alanlar | valid |
| MODEL-007 | `BrandProfile` | lut_file null | valid |
| MODEL-008 | `BrandProfile` | eksik name | validation error |

---

## 7. Electron UI Testleri

### 7.1 `electron/main.js`

| ID | Alan | Senaryo | Beklenen |
|----|------|---------|----------|
| EL-MAIN-001 | `getAgentCommand` | dev mode, venv var | venv python secilir |
| EL-MAIN-002 | `getAgentCommand` | dev mode, venv yok | `python` fallback |
| EL-MAIN-003 | `getAgentCommand` | packaged, agent.exe var | resourcesPath agent |
| EL-MAIN-004 | `getAgentCommand` | packaged, agent.exe yok | error box ve quit |
| EL-MAIN-005 | `startAgent` | agent basarili | stdout/stderr loglanir |
| EL-MAIN-006 | `startAgent` | agent crash | renderer'a `agent-crashed` |
| EL-MAIN-007 | `waitForAgent` | health hazir | true |
| EL-MAIN-008 | `waitForAgent` | timeout | false, UI yine acilir |
| EL-MAIN-009 | pencere | min size | 1200x700 altina inmez |
| EL-MAIN-010 | IPC `open-file-dialog` | multiple true | coklu path doner |

### 7.2 `electron/preload.js`

| ID | Alan | Senaryo | Beklenen |
|----|------|---------|----------|
| EL-PRE-001 | `contextBridge` | renderer | sadece izinli API gorunur |
| EL-PRE-002 | `agentWsUrl` | cagrilir | `ws://localhost:8765/ws` |
| EL-PRE-003 | `agentHttpUrl` | cagrilir | `http://localhost:8765` |
| EL-PRE-004 | `openFileDialog` | options | ipc invoke calisir |
| EL-PRE-005 | nodeIsolation | renderer console | `require` erisimi yok |

### 7.3 `electron/renderer/app.js`

| ID | Alan/Fonksiyon | Senaryo | Beklenen |
|----|----------------|---------|----------|
| UI-APP-001 | `AgentConnection.connect` | agent acik | status connected |
| UI-APP-002 | `connect` | agent kapali | retry yapar |
| UI-APP-003 | `send` | ws open | true |
| UI-APP-004 | `send` | ws closed | false ve mesaj |
| UI-APP-005 | `_dispatch` | bilinen type | handler cagrilir |
| UI-APP-006 | `_dispatch` | bilinmeyen type | console log, crash yok |
| UI-APP-007 | `setStatus` | connected | label/dot guncellenir |
| UI-APP-008 | `setProgress` | her tool | progress bar dogru |
| UI-APP-009 | `resetProgress` | result/error | label dogru |
| UI-APP-010 | chat methods | user/assistant/system/error | mesaj UI'a eklenir |
| UI-APP-011 | `renderTimeline` | timeline var | segmentler gorunur |
| UI-APP-012 | `renderTimeline` | bos timeline | crash yok |
| UI-APP-013 | `loadVideo` | output_path var | player src file URL |
| UI-APP-014 | `addFile` | video | `media.clips` |
| UI-APP-015 | `addFile` | photo | `media.photos` |
| UI-APP-016 | `addFile` | music | `media.music` |
| UI-APP-017 | `addFile` | unsupported ext | yok sayilir |
| UI-APP-018 | `addFile` | duplicate | tekrar eklenmez |
| UI-APP-019 | `sendCommand` | bos input | gondermez |
| UI-APP-020 | `sendCommand` | agent yok | sistem mesaji |
| UI-APP-021 | result handler | output_path + timeline | player + timeline |
| UI-APP-022 | error handler | error | progress hata |
| UI-APP-023 | quick buttons | demo/final/QA/acikla | command gider |
| UI-APP-024 | drag-drop | coklu medya | liste guncellenir |

### 7.4 `electron/renderer/wizard.js`

| ID | Alan/Fonksiyon | Senaryo | Beklenen |
|----|----------------|---------|----------|
| UI-WIZ-001 | constructor | acilis | 5 adimli overlay |
| UI-WIZ-002 | `_step1` | proje tipi secimi | type set |
| UI-WIZ-003 | `_step2` | tarz secimi | style set |
| UI-WIZ-004 | `_step3` | muzik drop | music path set |
| UI-WIZ-005 | `_step3` | AI onerisi | onerilen muzik secilir veya roadmap |
| UI-WIZ-006 | `_step3` | sonraya birak | PRD validasyonuna gore kabul/red |
| UI-WIZ-007 | `_step4` | referanssiz | devam |
| UI-WIZ-008 | `_step4` | referans link | link config'e girer |
| UI-WIZ-009 | `_step4` | profil secimi | selectedProfile set |
| UI-WIZ-010 | `_step5` | ozet | tum secimler dogru gorunur |
| UI-WIZ-011 | `_validate` | step 1 bos | uyari |
| UI-WIZ-012 | `_validate` | step 2 bos | uyari |
| UI-WIZ-013 | `_validate` | step 3 bos | PRD'ye uygun uyari |
| UI-WIZ-014 | `next` | valid step | ilerler |
| UI-WIZ-015 | `back` | step > 1 | geri doner |
| UI-WIZ-016 | `setMedia` | mevcut medya | config'e alinir |
| UI-WIZ-017 | `_finish` | tamamla | onComplete config |
| UI-WIZ-018 | `destroy` | iptal | overlay kalkar |

### 7.5 `electron/renderer/styles.css`

| ID | Alan | Senaryo | Beklenen |
|----|------|---------|----------|
| UI-CSS-001 | layout | 1200x700 | tasma/overlap yok |
| UI-CSS-002 | layout | 1920x1080 | paneller dengeli |
| UI-CSS-003 | long names | cok uzun dosya adi | ellipsis |
| UI-CSS-004 | chat | uzun komut | bubble tasmaz |
| UI-CSS-005 | timeline | 100 segment | yatay scroll |
| UI-CSS-006 | wizard | kucuk ekran | modal viewport icinde |
| UI-CSS-007 | contrast | dark tema | okunabilirlik |
| UI-CSS-008 | light tema | tema gelince | kontrast korunur |

---

## 8. E2E PRD Akis Testleri

### 8.1 Ana Basarili Akis

| ID | Adimlar | Beklenen |
|----|---------|----------|
| E2E-001 | Uygulamayi ac -> video/photo/music drag-drop -> sihirbaz -> demo olustur | demo MP4, timeline, QA raporu |
| E2E-002 | Demo sonrasi chat ile "daha hizli kes" -> yeniden demo | yeni timeline daha kisa segmentli |
| E2E-003 | Demo sonrasi final render | 4K H.265 final cikti |
| E2E-004 | Finali dahili player'da ac | oynar, ses var |
| E2E-005 | Projeyi kaydet -> uygulamayi kapat/ac -> projeyi ac | medya, style, timeline, profil korunur |

### 8.2 Proje Tipi ve Tarz Kombinasyonlari

Her proje tipi her tarzla test edilmelidir:

| Proje Tipi | Dark | Fast | Warm | Corporate |
|------------|------|------|------|-----------|
| Urun reklami | E2E-STYLE-001 | E2E-STYLE-002 | E2E-STYLE-003 | E2E-STYLE-004 |
| Dugun/etkinlik | E2E-STYLE-005 | E2E-STYLE-006 | E2E-STYLE-007 | E2E-STYLE-008 |
| Sosyal medya | E2E-STYLE-009 | E2E-STYLE-010 | E2E-STYLE-011 | E2E-STYLE-012 |
| Seyahat | E2E-STYLE-013 | E2E-STYLE-014 | E2E-STYLE-015 | E2E-STYLE-016 |

Beklenen:

- Fast cut: daha kisa sahneler, daha sik cut.
- Dark cinematic: daha dramatik LUT, daha uzun sahne araliklari.
- Warm lifestyle: sicak LUT, soft gecis.
- Corporate: temiz/nötr renk, kontrollu tempo.

### 8.3 Negatif Ana Akislar

| ID | Senaryo | Beklenen |
|----|---------|----------|
| E2E-NEG-001 | medya yokken demo | kullaniciya uyari |
| E2E-NEG-002 | sadece fotoğraf | slideshow veya desteklenmiyor mesaji |
| E2E-NEG-003 | sadece muzik | medya gerekli uyari |
| E2E-NEG-004 | bozuk video | ilgili dosya atlanir veya acik hata |
| E2E-NEG-005 | Claude API yok | lokal analiz/render mumkunse devam, Claude gereken yerde hata |
| E2E-NEG-006 | FFmpeg yok | kurulum uyari |
| E2E-NEG-007 | disk dolu | render fail, temp temizlik |
| E2E-NEG-008 | output dosyasi kilitli | kullaniciya hata |
| E2E-NEG-009 | agent render sirasinda kapanir | UI agent crash bildirir |
| E2E-NEG-010 | internet kesilir | API istekleri kontrollu fail |

---

## 9. QA Modul Kabul Testleri

### 9.1 Layer 1 Metrik QA

| ID | Senaryo | Kabul |
|----|---------|-------|
| QA-ACC-001 | beat-sync tam | score >= 95 |
| QA-ACC-002 | cut'lar 150ms kayik | score belirgin duser |
| QA-ACC-003 | siyah frame var | black_events > 0 |
| QA-ACC-004 | audio-video 80ms kayik | AV sync score <= 60 |
| QA-ACC-005 | ayni klip timeline'in %80'i | clip_repeat score dusuk |
| QA-ACC-006 | video-muzik sure farki 8 sn | duration score duser |
| QA-ACC-007 | renkler sahneler arasi cok farkli | color_consistency score duser |

### 9.2 Layer 2 Claude QA

| ID | Senaryo | Kabul |
|----|---------|-------|
| QA-CLD-001 | zayif acilis timeline | opening_strength dusuk, issue var |
| QA-CLD-002 | zayif kapanis timeline | closing_strength dusuk, suggestion var |
| QA-CLD-003 | style uyumsuz timeline | style_adherence dusuk |
| QA-CLD-004 | cok tekrar eden klip | issues icinde tekrar |
| QA-CLD-005 | Claude bozuk JSON | fallback rapor |

### 9.3 Layer 3 Vision QA

| ID | Senaryo | Kabul |
|----|---------|-------|
| QA-VIS-001 | iyi kompozisyonlu frame | overall yuksek |
| QA-VIS-002 | karanlik frame | lighting dusuk |
| QA-VIS-003 | bulanik frame | motion_blur/professional dusuk |
| QA-VIS-004 | urun odagi zayif | product_focus dusuk |
| QA-VIS-005 | Vision API hata | score 50 fallback |

### 9.4 Otomatik Duzeltme

| ID | Sorun | Beklenen Duzeltme |
|----|-------|-------------------|
| QA-FIX-001 | siyah kare | komsu kareden dolgu veya segment degisimi |
| QA-FIX-002 | AV desync | audio offset duzeltme |
| QA-FIX-003 | sure uyumsuzlugu | son segment snap/trim |
| QA-FIX-004 | klip tekrar | alternatif klip/segment |
| QA-FIX-005 | zayif kapanis | yuksek skor segment ile kapanis |

---

## 10. Render Kabul Testleri

### 10.1 Demo Render

| ID | Senaryo | Kabul |
|----|---------|-------|
| RENDER-DEMO-001 | normal proje | output exists |
| RENDER-DEMO-002 | metadata | width=960, height=540 |
| RENDER-DEMO-003 | codec | H.264 video, AAC audio |
| RENDER-DEMO-004 | hiz | kisa proje makul surede tamam |
| RENDER-DEMO-005 | muzik yok | sessiz/varsa kaynak ses ile render |
| RENDER-DEMO-006 | segment codec mismatch | normalize veya anlamli fail |

### 10.2 Final Render

| ID | Senaryo | Kabul |
|----|---------|-------|
| RENDER-FINAL-001 | final komut | output exists |
| RENDER-FINAL-002 | metadata | width=3840, height=2160 |
| RENDER-FINAL-003 | codec | HEVC/H.265 |
| RENDER-FINAL-004 | audio | AAC 320k veya profil degeri |
| RENDER-FINAL-005 | muzikli final | scale hala 4K |
| RENDER-FINAL-006 | render profili | kayitli preset uygulanir |
| RENDER-FINAL-007 | MOV format | container MOV ise acilir |
| RENDER-FINAL-008 | sosyal medya preset | 9:16/1:1 beklenen cikti |

---

## 11. Guvenlik, Gizlilik ve Dayaniklilik Testleri

| ID | Alan | Senaryo | Beklenen |
|----|------|---------|----------|
| SEC-001 | API key | `.env` git'e girmez | gitignore korur |
| SEC-002 | medya gizliligi | lokal medya | sadece gerekli frame/text API'ye gider |
| SEC-003 | Vision privacy | frame gonderimi | kullanici dokumaninda acik |
| SEC-004 | path injection | `clip"; del *.mp4` benzeri ad | komut calistirilmaz |
| SEC-005 | WebSocket | localhost disi baglanti | reddedilir veya policy |
| SEC-006 | Electron | nodeIntegration false | renderer Node'a erisemez |
| SEC-007 | temp cleanup | render sonrasi | gecici frame/JSX dosyalari temiz |
| SEC-008 | crash recovery | agent crash | UI kullaniciya bildirir |
| SEC-009 | log privacy | loglar | API key ve hassas path maskelenir |
| SEC-010 | file overwrite | output var | overwrite politikasi net |

---

## 12. Performans ve Limit Testleri

| ID | Senaryo | Kabul |
|----|---------|-------|
| PERF-001 | 10 klip + 1 muzik | demo < 10 dk |
| PERF-002 | 100 kisa klip | UI donmaz, agent ilerleme verir |
| PERF-003 | 30 dk video analizi | timeout veya progress |
| PERF-004 | 4K final render | progress ve tamamlanma |
| PERF-005 | Vision QA 7 frame | makul sure ve cleanup |
| PERF-006 | 500 medya dosyasi drag-drop | liste scroll ve bellek kontrolu |
| PERF-007 | uzun chat gecmisi | UI yavaslamaz |
| PERF-008 | cok uzun path > 240 karakter | Windows path handling |
| PERF-009 | disk dolmaya yakin | render kontrollu fail |
| PERF-010 | dusuk RAM | buyuk gorsellerde crash yok |

---

## 13. Paketleme ve Installer Testleri

| ID | Senaryo | Beklenen |
|----|---------|----------|
| PKG-001 | `npm run build:agent` | `dist/agent.exe` uretilir |
| PKG-002 | `npm run build` | NSIS installer uretilir |
| PKG-003 | temiz Windows kurulum | installer tamamlanir |
| PKG-004 | masaustu kisa yolu | uygulama acilir |
| PKG-005 | packaged app agent path | `resourcesPath/agent.exe` bulunur |
| PKG-006 | packaged luts/profiles | resources icinde var |
| PKG-007 | ilk acilis | agent health 25 sn icinde |
| PKG-008 | uninstall | kullanici data politikasi dogru |
| PKG-009 | internet yok ilk acilis | UI acilir, Claude gereken yerde hata |
| PKG-010 | FFmpeg yok packaged | kurulum/eksik arac mesaji |

---

## 14. Kapsam Disi Ozelliklerin Negatif Testleri

PRD v1.0 kapsami disinda olan ozellikler yanlislikla urun vaadi gibi davranmamalidir.

| ID | Senaryo | Beklenen |
|----|---------|----------|
| OOS-001 | rotoscoping istegi | desteklenmiyor/manuel AE isi mesaji |
| OOS-002 | obje takibi istegi | desteklenmiyor mesaji |
| OOS-003 | AI voiceover istegi | kapsam disi mesaji |
| OOS-004 | bulut render istegi | lokal render politikasi aciklanir |
| OOS-005 | macOS/Linux paket istegi | v1 Windows mesaji |
| OOS-006 | ekip/cok kullanici istegi | kapsam disi mesaji |
| OOS-007 | sosyal medyaya otomatik yukle | kapsam disi mesaji |

---

## 15. Manuel Kabul Checklist

Release oncesi asagidaki liste eksiksiz tamamlanmalidir.

- [ ] Uygulama Windows'ta cift tikla aciliyor.
- [ ] Agent otomatik basliyor ve UI baglanti durumunu dogru gosteriyor.
- [ ] Video, fotoğraf, muzik ve logo drag-drop ile ekleniyor.
- [ ] 5 adimli sihirbaz PRD validasyonlarini uyguluyor.
- [ ] Demo render uretiliyor ve dahili player'da oynuyor.
- [ ] Timeline UI segmentleri gosteriyor.
- [ ] QA raporu demo sonrasi otomatik gorunuyor.
- [ ] Chat ile en az 5 iteratif komut calisiyor.
- [ ] Final render 4K H.265 uretiliyor.
- [ ] Referans profil kaydediliyor ve yeni projede uygulanabiliyor.
- [ ] LUT/color grading secimi ciktiyi etkiliyor.
- [ ] Logo reveal veya text overlay render'a giriyor.
- [ ] Proje kaydedilip yeniden aciliyor.
- [ ] Dark/light tema degisiyor ve kalici oluyor.
- [ ] Paketlenmis installer temiz Windows'ta kuruluyor.
- [ ] Hata mesajlari kullaniciya teknik ama anlasilir bilgi veriyor.

---

## 16. Otomasyon Komutlari

### 16.1 Statik ve Import Kontrolleri

```powershell
venv\Scripts\python.exe -m compileall agent
```

```powershell
@'
from agent.claude_client import ClaudeClient, TOOLS
from agent.qa.orchestrator import QAOrchestrator
from agent.tools.ffmpeg_tool import FFMPEG_BIN, FFPROBE_BIN
print([t["name"] for t in TOOLS])
print(FFMPEG_BIN, FFPROBE_BIN)
print(QAOrchestrator.__name__)
'@ | venv\Scripts\python.exe -
```

### 16.2 FastAPI Endpoint Smoke Test

```powershell
@'
from fastapi.testclient import TestClient
from agent.main import app

client = TestClient(app)
for path in ["/health", "/projects", "/profiles", "/luts"]:
    r = client.get(path)
    print(path, r.status_code, r.text[:200])
'@ | venv\Scripts\python.exe -
```

### 16.3 FFmpeg Sentetik Medya Uretimi

```powershell
New-Item -ItemType Directory -Force -Path test_assets\video | Out-Null
ffmpeg -y -f lavfi -i testsrc=size=1920x1080:rate=30:duration=5 -f lavfi -i sine=frequency=1000:duration=5 -c:v libx264 -c:a aac test_assets\video\clean_1080p.mp4
ffmpeg -y -f lavfi -i color=c=black:s=320x240:d=1 -f lavfi -i anullsrc=channel_layout=stereo:sample_rate=44100 -shortest -c:v libx264 -c:a aac test_assets\video\black.mp4
ffmpeg -y -f lavfi -i sine=frequency=440:duration=10 -c:a mp3 test_assets\audio\test_440hz.mp3
```

### 16.4 Paketleme Kontrolleri

```powershell
npm run build:agent
npm run build
```

---

## 17. Release Gate

Bir surum release adayi sayilmak icin asagidaki sartlari gecmelidir:

| Gate | Sart |
|------|------|
| RG-001 | Tum statik/import testleri gecer |
| RG-002 | Kritik PRD akisi E2E-001, E2E-003 ve E2E-005 gecer |
| RG-003 | QA siyah kare, beat-sync ve AV sync testleri gecer |
| RG-004 | Final render metadata 4K H.265 dogrulanir |
| RG-005 | Installer temiz Windows'ta kurulup acilir |
| RG-006 | API key yok, FFmpeg yok, Claude offline gibi hata yollari kontrollu |
| RG-007 | Guvenlik testlerinde API key veya shell injection riski yok |
| RG-008 | PRD disi ozellikler yanlis urun vaadi uretmez |

---

## 18. Test Sonuc Rapor Sablonu

Her test turundan sonra asagidaki formatla rapor tutulmalidir:

```text
Test Tarihi:
Tester:
Commit/Branch:
Ortam:
Node/Python/FFmpeg Versiyonlari:
Claude API Durumu:
DaVinci/AE Durumu:

Calistirilan Test Gruplari:
- 

Gecen:
Kalan:
Bloklanan:

Kritik Hatalar:
- ID:
  Baslik:
  Repro:
  Beklenen:
  Gercek:
  Log/Output:

Release Gate Durumu:
- RG-001:
- RG-002:
- RG-003:
- RG-004:
- RG-005:
- RG-006:
- RG-007:
- RG-008:
```

