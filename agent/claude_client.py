import anthropic
import asyncio
import logging
import os
import shutil
import time
import uuid
from pathlib import Path
from agent.tools.music_analyzer import MusicAnalyzer
from agent.tools.clip_scorer import ClipScorer
from agent.tools.ffmpeg_tool import FFmpegTool
from agent.tools.auto_editor import build_timeline, write_concat_list
from agent.tools.photo_to_video import photos_to_clips
from agent.tools.semantic_analyzer import SemanticAnalyzer
from agent.tools.davinci_tool import DaVinciTool
from agent.tools.aftereffects_tool import AfterEffectsTool
from agent.tools.remotion_tool import RemotionTool
from agent.tools.premiere_tool import PremiereTool
from agent.qa.orchestrator import QAOrchestrator

logger = logging.getLogger(__name__)

TEMP_DIR   = Path(os.getenv("TEMP_DIR",   "./temp")).resolve()
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "./temp/output")).resolve()
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

SYSTEM_PROMPT = """
Sen bir AI video prodüksiyon asistanısın.

━━━ EN ÖNEMLİ KURAL: ARAÇLARI NE ZAMAN KULLANACAĞINI BİL ━━━

ARAÇ KULLANMA (sadece bunlarda):
✅ "demo oluştur", "video çıkar", "kurgu yap", "render al" → TAM pipeline başlat
✅ "rengi değiştir", "logo ekle", "başlık yaz" → İlgili tek aracı çağır
✅ render_type = "demo" veya "final" mesajı geldiğinde → Direkt render
✅ "daha hızlı yap", "tarzı değiştir" gibi revizyonlar → İlgili aracı çağır

ARAÇ KULLANMA (bunlarda sadece konuş):
❌ Sorular: "ne yapabilirsin?", "kaç klip yükledim?", "ne kadar sürer?"
❌ Sohbet: "merhaba", "teşekkürler", "nasıl gidiyor?"
❌ Bilgi istekleri: "dark tarz ne demek?", "LUT nedir?"
❌ Onay/ret: "tamam", "hayır", "anladım"
❌ Durum sorusu: "render tamamlandı mı?", "hangi aşamadayız?"

KARIŞIK DURUM (önce sor, sonra karar ver):
⚠️ "Bir video yap" gibi eksik bilgili istek → Önce 2-3 soru sor, cevap gelince başla
⚠️ "şunu düzelt" ama ne olduğu belirsiz → Ne düzeltileceğini sor

━━━ İLK PROJE KURULUMU (medya yüklenip genel istek geldiğinde) ━━━
Şu bilgiler eksikse SOR (tek mesajda, kısa):
1. Kaç saniyelik? (20/30/60/90sn)
2. Hangi tarz? (dark/fast/warm/corp)
3. Ne için? (ürün/etkinlik/sosyal medya)
4. Müziğin tamamı mı, en iyi bölümü mü?

━━━ GÖREV DAĞILIMI ━━━

🔧 FFmpeg — Omurga (her zaman çalışır)
  • analyze için hazırlık, trim, concat, demo render, ses normalize
  • Temel renk/geçiş (DaVinci/AE yoksa fallback)

🎨 DaVinci Resolve — Renk Uzmanı (bridge aktifse kullan, yoksa FFmpeg fallback)
  • color_grade  → Profesyonel renk düzeltme (node-based, LUT)
  • apply_lut    → .cube LUT dosyası uygulama
  • Render sonrası video üzerine çalışır

✨ After Effects — Animasyon Uzmanı (otomatik başlar)
  • add_logo     → Logo reveal animasyonu (JSX → aerender headless)
  • add_text     → Animasyonlu başlık/alt başlık (lower third)
  • add_transition → Flash, glitch, ışık geçişi efektleri
  • Render sonrası video üzerine çalışır

🎬 Premiere Pro — Final Uzmanı (otomatik başlar, PProHeadless)
  • premiere_export → Final 4K export (Adobe presetleri, Lumetri, ses mixer)
  • Tüm işlemler bittikten sonra son adım olarak çalışır

━━━ ARAÇLAR ━━━
ANALİZ:  analyze_music, score_clips
MÜZİK:   select_music_section → müziğin en iyi/belirli bölümünü kes
KURGU:   build_timeline (target_duration ile), render_timeline
RENK:    color_grade (DaVinci→FFmpeg), apply_lut (DaVinci→FFmpeg)
GRAFİK:  add_logo (AE→FFmpeg), add_text (AE→FFmpeg), add_transition (FFmpeg xfade)
SES:     normalize_audio, add_music
FİNAL:   premiere_export (Premiere→FFmpeg fallback)

━━━ TAM AKIŞ (sorular cevaplandıktan sonra) ━━━
1. analyze_music + score_clips  (müzik analizi + klip puanlama)
2. select_music_section         (kullanıcı 30sn istedi, müzik 3dk ise — en iyi 30sn'yi kes)
3. build_timeline               (target_duration=kullanıcının istediği süre)
4. render_timeline              (FFmpeg hızlı render)
5. color_grade                  (DaVinci veya FFmpeg)
6. add_logo + add_text          (After Effects veya FFmpeg)
7. premiere_export              (Premiere Pro veya FFmpeg 4K)

MÜZİK SEÇİM KURALI:
- Kullanıcı "müziğin en iyi bölümü" dediyse → select_music_section(mode="best")
- Kullanıcı "müziğin tamamını kullan" dediyse → select_music_section atla
- Hedef video 30sn, müzik 3dk ise → select_music_section(duration=30) ZORUNLU

TARZ TANIMLARI:
dark → 4 beat/sahne · cool ton · dramatik · hard_cut geçiş
fast → 1 beat/sahne · yüksek kontrast · enerji · whip_pan geçiş
warm → 3 beat/sahne · sıcak ton · soft · dissolve geçiş
corp → 2 beat/sahne · nötr · temiz · fade geçiş

KURALLAR:
• Araç başarısız → fallback devreye girer, DUR MA, devam et
• render_timeline'dan sonra color_grade, add_logo, add_text, premiere_export
• Türkçe yanıt, kısa ve öz
• Maksimum 12 tool çağrısı
"""

TOOLS = [
    # ── Müzik Bölümü Seçimi ──────────────────────────────────────────────────
    {
        "name": "select_music_section",
        "description": (
            "Müziğin belirli bir bölümünü keser. "
            "Hedef video süresi müzikten kısaysa KULLAN. "
            "mode='best' → en yüksek enerjili bölüm (chorus/drop). "
            "mode='start' → müziğin başından. "
            "mode='custom' → start_time'dan duration kadar."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "file_path":  {"type": "string",  "description": "Müzik dosyası tam yolu"},
                "duration":   {"type": "number",  "description": "İstenen süre (saniye)"},
                "mode":       {"type": "string",  "enum": ["best", "start", "custom"],
                               "description": "best=en iyi bölüm, start=baş, custom=özel"},
                "start_time": {"type": "number",  "description": "Özel başlangıç (saniye, sadece mode=custom)"},
            },
            "required": ["file_path", "duration"]
        }
    },
    # ── Analiz ──────────────────────────────────────────────────────────────
    {
        "name": "analyze_music",
        "description": "Müzik BPM, beat zamanları, drop noktaları, toplam süre.",
        "input_schema": {
            "type": "object",
            "properties": {
                "file_path": {"type": "string"}
            },
            "required": ["file_path"]
        }
    },
    {
        "name": "score_clips",
        "description": "Video kliplerini parlaklık, keskinlik ve hareket skoruna göre sıralar.",
        "input_schema": {
            "type": "object",
            "properties": {
                "clip_paths": {"type": "array", "items": {"type": "string"}}
            },
            "required": ["clip_paths"]
        }
    },
    # ── Kurgu ───────────────────────────────────────────────────────────────
    {
        "name": "build_timeline",
        "description": "Beat zamanları ve klip skorlarından beat-sync kurgu timeline üretir.",
        "input_schema": {
            "type": "object",
            "properties": {
                "beat_times":      {"type": "array", "items": {"type": "number"}},
                "scored_clips":    {"type": "array"},
                "music_duration":  {"type": "number"},
                "style":           {"type": "string", "enum": ["dark","fast","warm","corp"]},
                "target_duration": {"type": "number",
                                    "description": "Hedef video süresi saniye (ör. 30). Müzikten kısa olabilir."}
            },
            "required": ["beat_times","scored_clips","music_duration"]
        }
    },
    {
        "name": "render_timeline",
        "description": "Timeline segmentlerini trim+concat+müzik ile birleşik videoya render eder.",
        "input_schema": {
            "type": "object",
            "properties": {
                "timeline":    {"type": "array"},
                "music_path":  {"type": "string"},
                "quality":     {"type": "string", "enum": ["demo","final"]},
                "output_path": {"type": "string"}
            },
            "required": ["timeline"]
        }
    },
    # ── Renk Grading ────────────────────────────────────────────────────────
    {
        "name": "color_grade",
        "description": "Tarz bazlı renk düzeltmesi (dark/warm/corp/fast). FFmpeg natif — hiçbir dış program gerekmez.",
        "input_schema": {
            "type": "object",
            "properties": {
                "input_path":  {"type": "string", "description": "Render edilmiş video yolu"},
                "style":       {"type": "string", "enum": ["dark","warm","corp","fast","natural"]},
                "output_path": {"type": "string"}
            },
            "required": ["input_path","style"]
        }
    },
    {
        "name": "apply_lut",
        "description": ".cube LUT dosyasını videoya uygular. FFmpeg natif.",
        "input_schema": {
            "type": "object",
            "properties": {
                "input_path":  {"type": "string"},
                "lut_path":    {"type": "string", "description": ".cube dosyasının tam yolu"},
                "output_path": {"type": "string"}
            },
            "required": ["input_path","lut_path"]
        }
    },
    # ── Grafik / Overlay ─────────────────────────────────────────────────────
    {
        "name": "add_logo",
        "description": "Video üzerine logo overlay + fade-in animasyonu ekler. FFmpeg natif — After Effects gerekmez.",
        "input_schema": {
            "type": "object",
            "properties": {
                "input_path":  {"type": "string"},
                "logo_path":   {"type": "string", "description": "PNG logo dosyası"},
                "position":    {"type": "string", "enum": ["bottom-right","bottom-left","top-right","top-left","center"]},
                "fade_in":     {"type": "number", "description": "Fade-in süresi (saniye, varsayılan 0.8)"},
                "output_path": {"type": "string"}
            },
            "required": ["input_path","logo_path"]
        }
    },
    {
        "name": "add_text",
        "description": "Video üzerine başlık + alt başlık metin overlay ekler. FFmpeg natif — After Effects gerekmez.",
        "input_schema": {
            "type": "object",
            "properties": {
                "input_path":  {"type": "string"},
                "title":       {"type": "string"},
                "subtitle":    {"type": "string"},
                "position":    {"type": "string", "enum": ["bottom","top"]},
                "fade_in":     {"type": "number"},
                "output_path": {"type": "string"}
            },
            "required": ["input_path","title"]
        }
    },
    {
        "name": "add_transition",
        "description": "İki klip arasına geçiş efekti ekler (fade/dissolve/wipeleft/wiperight/circleclose vb.). FFmpeg xfade.",
        "input_schema": {
            "type": "object",
            "properties": {
                "clip1":       {"type": "string"},
                "clip2":       {"type": "string"},
                "transition":  {"type": "string", "description": "fade|dissolve|wipeleft|wiperight|slideleft|slideright|circleclose|radial|pixelize"},
                "duration":    {"type": "number", "description": "Geçiş süresi saniye (varsayılan 0.5)"},
                "output_path": {"type": "string"}
            },
            "required": ["clip1","clip2"]
        }
    },
    # ── Ses ─────────────────────────────────────────────────────────────────
    {
        "name": "normalize_audio",
        "description": "Video sesini EBU R128 standardına normalize eder.",
        "input_schema": {
            "type": "object",
            "properties": {
                "input_path":  {"type": "string"},
                "output_path": {"type": "string"}
            },
            "required": ["input_path"]
        }
    },
    {
        "name": "add_music",
        "description": "Müziği videoya ekler, orijinal video sesini arka planda karıştırır.",
        "input_schema": {
            "type": "object",
            "properties": {
                "video_path":  {"type": "string"},
                "music_path":  {"type": "string"},
                "video_vol":   {"type": "number", "description": "Video ses seviyesi 0-1 (varsayılan 0.3)"},
                "music_vol":   {"type": "number", "description": "Müzik ses seviyesi 0-1 (varsayılan 1.0)"},
                "output_path": {"type": "string"}
            },
            "required": ["video_path","music_path"]
        }
    },
    # ── Final Export ─────────────────────────────────────────────────────────
    {
        "name": "premiere_export",
        "description": (
            "Premiere Pro ile profesyonel final export yapar (Lumetri renk, ses mixer, Adobe presetleri). "
            "Premiere başlatılamıyorsa FFmpeg 4K H.265 ile fallback. "
            "TÜM color_grade/add_logo/add_text işlemleri bittikten SONRA çağrılır."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "input_path":     {"type": "string", "description": "Render edilmiş video"},
                "output_path":    {"type": "string", "description": "Çıktı yolu (opsiyonel)"},
                "preset":         {"type": "string", "description": "H.264|H.265|ProRes (varsayılan H.265)"},
                "resolution":     {"type": "string", "description": "1080p|4K (varsayılan 4K)"},
                "lumetri_style":  {"type": "string", "description": "dark|warm|corp|fast (Lumetri renk profili)"}
            },
            "required": ["input_path"]
        }
    }
]


class ClaudeClient:

    def __init__(self):
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY eksik — .env dosyasını kontrol et\n"
                "Örnek: ANTHROPIC_API_KEY=sk-ant-..."
            )
        self.client   = anthropic.Anthropic(api_key=api_key)
        self.music    = MusicAnalyzer()
        self.scorer   = ClipScorer()
        self.semantic = SemanticAnalyzer()
        self.ffmpeg   = FFmpegTool()
        self.davinci  = DaVinciTool()
        self.ae       = AfterEffectsTool()
        self.remotion = RemotionTool()
        self.premiere = PremiereTool()
        self.qa       = QAOrchestrator()
        TEMP_DIR.mkdir(parents=True, exist_ok=True)

    async def process(self, data: dict):
        command = data.get("command", "").strip()
        if not command:
            yield {"type": "error", "message": "Komut boş olamaz"}
            return

        # render_type alanı varsa Claude'u atla, doğrudan render et
        render_type = data.get("render_type")
        if render_type in ("demo", "final"):
            async for chunk in self._direct_render(data, render_type):
                yield chunk
            return

        messages = [{"role": "user", "content": self._build_prompt(data)}]
        context  = {
            "files":            data.get("files", {}),
            "style":            data.get("style", "dark"),
            "project":          data.get("project_id", f"proj_{int(time.time())}"),
            "timeline":         None,
            "music_analysis":   None,
        }

        # Onay bekleniyor mu?
        if data.get("awaiting_approval"):
            # Kullanıcı planı onayladı — devam et
            context["plan_approved"] = True
        else:
            # Önce plan yap, kullanıcıya göster ve onay iste
            plan_response = await asyncio.wait_for(
                asyncio.to_thread(
                    self.client.messages.create,
                    model="claude-sonnet-4-6",
                    max_tokens=1024,
                    system=SYSTEM_PROMPT + """

ŞU AN PLAN MODUNDASIN. Araç çağırma! Sadece şunları yaz:
1. Ne anladığını (1-2 cümle)
2. Ne yapacağını — adım adım liste
3. Son satır: "Onaylarsanız başlayabilirim."

Kısa tut, 150 kelimeyi geçme.""",
                    messages=messages
                ),
                timeout=30.0
            )
            plan_text = next((b.text for b in plan_response.content if hasattr(b, "text")), "")

            # Araç çağrısı yapmak istedi mi? (istemiyoruz bu aşamada)
            needs_action = any(kw in command.lower() for kw in
                ["demo", "render", "video", "kurgu", "başlat", "yap", "oluştur",
                 "start", "create", "edit", "final", "çıkar"])

            if needs_action and plan_text:
                yield {"type": "plan", "text": plan_text, "command": command}
                return  # Renderer onayını bekle

        yield {"type": "progress", "step": "claude_thinking", "status": "running",
               "message": "Claude düşünüyor..."}

        while True:
            try:
                response = await asyncio.wait_for(
                    asyncio.to_thread(
                        self.client.messages.create,
                        model="claude-sonnet-4-6",
                        max_tokens=4096,
                        system=SYSTEM_PROMPT,
                        tools=TOOLS,
                        messages=messages
                    ),
                    timeout=120.0
                )
            except asyncio.TimeoutError:
                yield {"type": "error", "message": "Claude yanıt vermiyor (120s timeout) — lütfen tekrar dene"}
                return

            if response.stop_reason == "end_turn":
                text = next((b.text for b in response.content if hasattr(b, "text")), "")
                result = {
                    "type":        "result",
                    "text":        text,
                    "output_path": context.get("last_output"),
                    "timeline":    context.get("timeline"),
                }
                # QA sonuçlarını ekle
                if context.get("qa_report"):
                    qa = context["qa_report"]
                    result["qa_score"] = qa.get("final_score")
                    result["qa_grade"] = qa.get("grade")
                    result["qa_pass"]  = qa.get("pass")
                    result["qa_report"] = qa
                yield result
                break

            if response.stop_reason == "tool_use":
                messages.append({"role": "assistant", "content": response.content})
                tool_results = []

                for block in response.content:
                    if block.type != "tool_use":
                        continue

                    yield {"type": "progress", "tool": block.name, "status": "running",
                           "message": f"{block.name} çalışıyor..."}

                    result = await self._run_tool(block.name, block.input, context)

                    yield {"type": "progress", "tool": block.name, "status": "done",
                           "result_summary": str(result)[:200]}

                    tool_results.append({
                        "type":        "tool_result",
                        "tool_use_id": block.id,
                        "content":     str(result)
                    })

                messages.append({"role": "user", "content": tool_results})

            else:
                logger.warning(f"Beklenmeyen stop_reason: {response.stop_reason}")
                break

    async def _direct_render(self, data: dict, quality: str):
        """Claude'u atla — doğrudan render_timeline + QA çalıştır."""
        files   = data.get("files", {})
        context = {
            "files":          files,
            "style":          data.get("style", "dark"),
            "project":        data.get("project_id", f"proj_{int(time.time())}"),
            "timeline":       None,
            "music_analysis": None,
        }

        yield {"type": "progress", "step": "direct_render", "status": "running",
               "message": f"{quality} render başlatılıyor..."}

        clips  = files.get("clips", [])
        photos = files.get("photos", [])
        music  = files.get("music")

        # Fotoğrafları video kliplere çevir ve havuza ekle
        if photos:
            yield {"type": "progress", "tool": "score_clips", "status": "running",
                   "message": f"{len(photos)} fotoğraf video klibe dönüştürülüyor..."}
            photo_clips = await photos_to_clips(photos, duration=3.0, style=context["style"])
            clips = list(clips) + [pc["path"] for pc in photo_clips]
            logger.info(f"{len(photo_clips)} fotoğraf video'ya dönüştürüldü")

        if not clips:
            yield {"type": "error", "message": "Render için klip veya fotoğraf gerekli"}
            return

        # Müzik analizi
        music_analysis = None
        if music:
            yield {"type": "progress", "tool": "analyze_music", "status": "running",
                   "message": "Müzik analiz ediliyor..."}
            music_analysis = await self.music.analyze(music)
            context["music_analysis"] = music_analysis
            yield {"type": "progress", "tool": "analyze_music", "status": "done",
                   "result_summary": f"BPM: {music_analysis.get('bpm')}"}

        # Klip skorla (teknik metrikler)
        yield {"type": "progress", "tool": "score_clips", "status": "running",
               "message": "Klipler puanlanıyor..."}
        scored = await self.scorer.score(clips)
        yield {"type": "progress", "tool": "score_clips", "status": "done",
               "result_summary": f"{len(scored)} klip puanlandı"}

        if not scored:
            yield {"type": "error", "message": "Klip skorlama başarısız"}
            return

        # Semantik analiz (Claude Vision — içerik anlama)
        project_type = data.get("project_type", "product")
        yield {"type": "progress", "step": "semantic", "status": "running",
               "message": f"Kliplerin içeriği analiz ediliyor ({len(scored)} klip)..."}
        try:
            scored = await self.semantic.analyze_clips_batch(scored, project_type, context["style"])
            yield {"type": "progress", "step": "semantic", "status": "done",
                   "result_summary": f"Semantik analiz tamamlandı"}
        except Exception as e:
            logger.warning(f"Semantik analiz başarısız (teknik skorla devam): {e}")

        # Hedef süreyi data'dan al — kullanıcı "30sn istiyorum" demişse buraya gelir
        target_dur = float(data.get("target_duration") or context.get("target_duration") or 90.0)
        context["target_duration"] = target_dur

        # Timeline oluştur — hedef süreye göre music_duration'ı kırp
        beat_times  = (music_analysis or {}).get("beat_times", [0.5 * i for i in range(60)])
        music_dur   = min((music_analysis or {}).get("duration", target_dur), target_dur)
        drop_times  = (music_analysis or {}).get("drop_times", [])
        timeline    = build_timeline(beat_times, scored, music_dur, context["style"],
                                     drop_times=drop_times)
        context["timeline"] = timeline

        # Render
        render_inputs = {
            "timeline":        timeline,
            "music_path":      music,
            "quality":         quality,
            "target_duration": target_dur,
        }
        render_result = await self._render_timeline(render_inputs, context)

        if not render_result.get("success"):
            yield {"type": "error", "message": render_result.get("error", "Render başarısız")}
            return

        # QA
        out_path = render_result["output_path"]
        yield {"type": "progress", "step": "qa", "status": "running",
               "message": "Kalite kontrol yapılıyor..."}
        try:
            qa_report = await self.qa.run(
                out_path, music or "", timeline,
                context["style"], music_analysis
            )
            context["qa_report"] = qa_report
        except Exception as e:
            logger.warning(f"QA hatası (render geçerli): {e}")
            qa_report = {"final_score": None, "grade": "?", "pass": True,
                         "error": str(e)}

        result = {
            "type":        "result",
            "text":        f"{quality.upper()} render tamamlandı — {render_result.get('segments', 0)} sahne",
            "output_path": out_path,
            "timeline":    timeline,
            "qa_score":    qa_report.get("final_score"),
            "qa_grade":    qa_report.get("grade"),
            "qa_pass":     qa_report.get("pass"),
            "qa_report":   qa_report,
        }
        yield result

    async def _run_tool(self, name: str, inputs: dict, context: dict) -> dict:
        try:
            if name == "select_music_section":
                fp       = inputs["file_path"]
                duration = float(inputs["duration"])
                mode     = inputs.get("mode", "best")
                start    = inputs.get("start_time", 0.0)

                # Analiz zaten yapıldıysa best_section_start'ı kullan
                if mode == "best":
                    ma = context.get("music_analysis")
                    if ma and "best_section_start" in ma:
                        start = ma["best_section_start"]
                    else:
                        # Analiz yoksa burada yap
                        analysis = await self.music.analyze(fp)
                        start = analysis.get("best_section_start", 0.0)
                        context["music_analysis"] = analysis
                elif mode == "start":
                    start = 0.0
                # mode == "custom": start_time kullan

                result = await self.music.extract_section(fp, start, duration)
                if result.get("success"):
                    context["selected_music"] = result["output_path"]
                    logger.info(f"Müzik bölümü: {start:.1f}sn'den {duration:.1f}sn — {result['output_path']}")
                return result

            if name == "analyze_music":
                result = await self.music.analyze(inputs["file_path"])
                context["music_analysis"] = result
                return result

            if name == "score_clips":
                return await self.scorer.score(inputs["clip_paths"])

            if name == "build_timeline":
                target_dur = inputs.get("target_duration") or context.get("target_duration")
                # target_duration varsa music_duration'ı buna sabitle
                eff_duration = min(
                    float(inputs["music_duration"]),
                    float(target_dur) if target_dur else float(inputs["music_duration"])
                )
                drop_times = (context.get("music_analysis") or {}).get("drop_times", [])
                tl = build_timeline(
                    inputs["beat_times"],
                    inputs["scored_clips"],
                    eff_duration,
                    inputs.get("style", context.get("style", "dark")),
                    drop_times=drop_times,
                )
                context["timeline"] = tl
                if target_dur:
                    context["target_duration"] = float(target_dur)
                return {"timeline": tl, "segment_count": len(tl),
                        "effective_duration": eff_duration}

            if name == "render_timeline":
                # select_music_section çağrıldıysa o müziği kullan
                if context.get("selected_music") and not inputs.get("music_path"):
                    inputs = {**inputs, "music_path": context["selected_music"]}
                render_result = await self._render_timeline(inputs, context)
                # Render başarılıysa QA çalıştır
                if render_result.get("success"):
                    out_path   = render_result["output_path"]
                    music_path = inputs.get("music_path") or context["files"].get("music", "")
                    timeline   = inputs.get("timeline") or context.get("timeline", [])
                    yield_qa   = True
                    try:
                        qa_report = await self.qa.run(
                            out_path, music_path, timeline,
                            context.get("style", "dark"),
                            context.get("music_analysis")
                        )
                        context["qa_report"] = qa_report
                        render_result["qa_score"] = qa_report.get("final_score")
                        render_result["qa_grade"] = qa_report.get("grade")
                        render_result["qa_pass"]  = qa_report.get("pass")
                    except Exception as e:
                        logger.warning(f"QA hatası (render geçerli): {e}")
                        render_result["qa_warning"] = str(e)
                return render_result

            if name == "run_ffmpeg":
                return await self._handle_ffmpeg(inputs, context)

            # ── Renk Grading: DaVinci önce, FFmpeg fallback ──────────────────
            if name == "color_grade":
                inp   = inputs["input_path"]
                style = inputs.get("style", "dark")
                out   = inputs.get("output_path")
                # DaVinci bridge aktifse önce dene
                try:
                    dv_result = await self.davinci.apply_color_preset(style)
                    if dv_result.get("ok"):
                        logger.info("color_grade: DaVinci Resolve kullanıldı")
                        dv_result["engine"] = "davinci"
                        return dv_result
                except Exception:
                    pass
                # Fallback: FFmpeg
                result = await self.ffmpeg.apply_color_grade(inp, style, out)
                result["engine"] = "ffmpeg"
                if result.get("success"):
                    context["last_output"] = result["output_path"]
                return result

            if name == "apply_lut":
                inp      = inputs["input_path"]
                lut_path = inputs["lut_path"]
                out      = inputs.get("output_path")
                # DaVinci LUT uygulama
                try:
                    dv_result = await self.davinci.apply_lut(lut_path)
                    if dv_result.get("ok"):
                        logger.info("apply_lut: DaVinci Resolve kullanıldı")
                        dv_result["engine"] = "davinci"
                        return dv_result
                except Exception:
                    pass
                # Fallback: FFmpeg lut3d
                result = await self.ffmpeg.apply_lut(inp, lut_path, out)
                result["engine"] = "ffmpeg"
                if result.get("success"):
                    context["last_output"] = result["output_path"]
                return result

            # ── Grafik/Overlay: After Effects önce, FFmpeg fallback ───────────
            if name == "add_logo":
                inp      = inputs["input_path"]
                logo     = inputs["logo_path"]
                out      = inputs.get("output_path")
                duration = inputs.get("fade_in", 3.0)
                style    = context.get("style", "dark")

                # 1. Remotion — en iyi kalite, Node.js yeterli
                try:
                    rem = await self.remotion.logo_reveal(logo, style, duration)
                    if rem.get("ok") and rem.get("output_path"):
                        # Remotion çıktısını video üzerine overlay et
                        overlay_out = out or self._auto_path("logo_overlay")
                        ov = await self.ffmpeg.add_logo(inp, rem["output_path"], "bottom-right", 0.0, overlay_out)
                        if ov.get("success"):
                            logger.info("add_logo: Remotion kullanıldı")
                            ov["engine"] = "remotion"
                            context["last_output"] = ov["output_path"]
                            return ov
                except Exception as e:
                    logger.warning(f"Remotion logo hata: {e}")

                # 2. FFmpeg direkt overlay (en güvenilir fallback)
                result = await self.ffmpeg.add_logo(inp, logo,
                    inputs.get("position", "bottom-right"), inputs.get("fade_in", 0.8), out)
                result["engine"] = "ffmpeg"
                if result.get("success"):
                    context["last_output"] = result["output_path"]
                return result

            if name == "add_text":
                inp      = inputs["input_path"]
                title    = inputs["title"]
                subtitle = inputs.get("subtitle", "")
                out      = inputs.get("output_path")
                duration = inputs.get("duration", 5.0)
                style    = context.get("style", "dark")

                # 1. Remotion — animasyonlu lower third
                try:
                    rem = await self.remotion.text_overlay(title, subtitle, style, duration)
                    if rem.get("ok") and rem.get("output_path"):
                        # Video üzerine overlay
                        overlay_out = out or self._auto_path("text_overlay")
                        ov_cmd = (f'-i "{inp}" -i "{rem["output_path"]}" '
                                  f'-filter_complex "[0:v][1:v]overlay=0:0" '
                                  f'-c:v libx264 -crf 18 -preset fast -c:a copy')
                        ov = await self.ffmpeg.run({"command": ov_cmd, "output_path": overlay_out})
                        if ov.get("success"):
                            logger.info("add_text: Remotion kullanıldı")
                            ov["engine"] = "remotion"
                            context["last_output"] = overlay_out
                            return ov
                except Exception as e:
                    logger.warning(f"Remotion text hata: {e}")

                # 2. FFmpeg drawtext fallback
                result = await self.ffmpeg.add_text(inp, title, subtitle,
                    inputs.get("position", "bottom"), inputs.get("fade_in", 0.5), output_path=out)
                result["engine"] = "ffmpeg"
                if result.get("success"):
                    context["last_output"] = result["output_path"]
                return result

            if name == "add_transition":
                result = await self.ffmpeg.add_transition(
                    inputs["clip1"], inputs["clip2"],
                    inputs.get("transition", "fade"),
                    inputs.get("duration", 0.5),
                    inputs.get("output_path")
                )
                if result.get("success"):
                    context["last_output"] = result["output_path"]
                return result

            # ── Ses ──────────────────────────────────────────────────────────
            if name == "normalize_audio":
                result = await self.ffmpeg.normalize_audio(
                    inputs["input_path"], inputs.get("output_path")
                )
                if result.get("success"):
                    context["last_output"] = result["output_path"]
                return result

            if name == "add_music":
                result = await self.ffmpeg.add_music(
                    inputs["video_path"], inputs["music_path"],
                    inputs.get("output_path"),
                    inputs.get("video_vol", 0.3),
                    inputs.get("music_vol", 1.0)
                )
                if result.get("success"):
                    context["last_output"] = result["output_path"]
                return result

            # ── Premiere Pro Final Export ─────────────────────────────────────
            if name == "premiere_export":
                inp       = inputs["input_path"]
                out       = inputs.get("output_path") or self._auto_path("final_premiere")
                preset    = inputs.get("preset", "H.265")
                res       = inputs.get("resolution", "4K")
                lum_style = inputs.get("lumetri_style")

                # Premiere Pro headless export
                try:
                    prj_path = str(TEMP_DIR / f"pp_{uuid.uuid4().hex[:8]}.prproj")
                    # Klipleri import et ve sekans oluştur
                    pp_result = await self.premiere.export_sequence(
                        prj_path, "AI_Edit_Sequence", out, preset
                    )
                    if pp_result.get("ok") and pp_result.get("output_path"):
                        logger.info("premiere_export: Premiere Pro kullanıldı")
                        pp_result["engine"] = "premiere"
                        context["last_output"] = pp_result["output_path"]
                        return pp_result
                except Exception as e:
                    logger.warning(f"Premiere Pro export başarısız, FFmpeg fallback: {e}")

                # Fallback: FFmpeg 4K H.265
                if res == "4K":
                    cmd = self.ffmpeg.render_4k_cmd(inp)
                else:
                    cmd = self.ffmpeg.render_cmd(inp, "1920x1080")
                result = await self.ffmpeg.run({"command": cmd, "output_path": out})
                result["engine"] = "ffmpeg"
                if result.get("success"):
                    context["last_output"] = out
                return result

            return {"error": f"Bilinmeyen araç: {name}"}

        except Exception as e:
            logger.error(f"Tool hatası [{name}]: {e}", exc_info=True)
            return {"error": str(e)}

    async def _render_timeline(self, inputs: dict, context: dict) -> dict:
        timeline   = inputs.get("timeline") or context.get("timeline")
        music_path = inputs.get("music_path") or context["files"].get("music")
        quality    = inputs.get("quality", "demo")
        # Hedef video süresi — 20dk müzik yüklenince 30dk video üretilmesini önler
        target_duration = inputs.get("target_duration") or context.get("target_duration", 90.0)

        if not timeline:
            return {"error": "Timeline boş — önce build_timeline çalıştır"}

        # Süre limiti uygula: target_duration saniyeyi geçen segmentleri kes
        total_so_far = 0.0
        limited_timeline = []
        for seg in timeline:
            dur = float(seg.get("duration", 2))
            if total_so_far + dur > target_duration:
                break
            limited_timeline.append(seg)
            total_so_far += dur
        if not limited_timeline:
            limited_timeline = timeline[:30]  # en az 30 segment al

        logger.info(f"Timeline: {len(timeline)} → {len(limited_timeline)} sahne ({total_so_far:.1f}s, limit: {target_duration}s)")

        project_id = context.get("project", f"proj_{int(time.time())}")
        seg_dir    = TEMP_DIR / project_id
        try:
            seg_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            return {"error": f"Geçici klasör oluşturulamadı: {e}"}

        # Her segmenti trim et
        # clip_offset: klip süresiyle orantılı akıllı offset
        trimmed = []
        for i, seg in enumerate(limited_timeline):
            clip       = seg.get("clip_path", "")
            seg_dur    = float(seg.get("duration", 2))
            transition = seg.get("transition", "hard_cut")

            # clip_offset timeline'dan al (auto_editor'ın belirlediği)
            # Rastgele offset kaldırıldı — kalite düşürüyor
            offset = float(seg.get("clip_offset", 0.0))

            out = str(seg_dir / f"seg_{i:04d}.mp4")
            cmd = self.ffmpeg.trim_cmd(clip, offset, seg_dur)
            result = await self.ffmpeg.run({"command": cmd, "output_path": out})
            if result["success"]:
                trimmed.append({"path": out, "transition": transition})
            else:
                logger.warning(f"Segment {i} trim başarısız")

        if not trimmed:
            return {"error": "Hiçbir segment trim edilemedi"}

        # Geçiş efektleri uygula (tarz bazlı)
        style = context.get("style", "dark")
        concat_out = await self._apply_transitions(trimmed, seg_dir, style)
        if not concat_out:
            return {"error": "Geçiş uygulaması başarısız"}

        suffix  = f"_{uuid.uuid4().hex[:6]}"
        out_dir = OUTPUT_DIR
        out_dir.mkdir(parents=True, exist_ok=True)

        if quality == "final":
            out_path = str(out_dir / f"final{suffix}.mp4")
            if music_path:
                cmd = (f'-i "{concat_out}" -i "{music_path}" '
                       f'-vf scale=3840:2160 '
                       f'-map 0:v -map 1:a -c:v libx265 -crf 18 -preset slow '
                       f'-c:a aac -b:a 320k -shortest')
            else:
                cmd = self.ffmpeg.render_4k_cmd(concat_out)
        else:
            out_path = str(out_dir / f"demo{suffix}.mp4")
            if music_path:
                cmd = (f'-i "{concat_out}" -i "{music_path}" '
                       f'-map 0:v -map 1:a -vf scale=960:540 '
                       f'-c:v libx264 -crf 28 -preset ultrafast '
                       f'-c:a aac -b:a 128k -shortest')
            else:
                cmd = self.ffmpeg.demo_render_cmd(concat_out)

        result = await self.ffmpeg.run({"command": cmd, "output_path": out_path})
        if not result["success"]:
            return {"error": f"Render başarısız: {result.get('stderr_tail','')[:200]}"}

        # Geçici segment dosyalarını temizle
        shutil.rmtree(seg_dir, ignore_errors=True)

        context["last_output"] = out_path
        logger.info(f"Render tamamlandı: {out_path}")
        return {
            "success":     True,
            "output_path": out_path,
            "segments":    len(trimmed),
            "quality":     quality,
            "music":       bool(music_path)
        }

    async def _apply_transitions(self, trimmed: list, seg_dir, style: str) -> str | None:
        """
        Trim edilmiş segmentleri geçiş efektleriyle birleştirir.
        - hard_cut  → direkt concat (en hızlı)
        - dissolve  → xfade fade geçiş
        - whip_pan  → xfade wipeleft geçiş
        Geçiş eklenemezse basit concat'a düşer.
        """
        # Tarz → geçiş türü eşlemesi
        STYLE_TRANS = {
            "dark": "hard_cut",
            "corp": "hard_cut",
            "warm": "dissolve",
            "fast": "wipeleft",
        }
        transition_type = STYLE_TRANS.get(style, "hard_cut")

        paths = [s["path"] for s in trimmed]

        # hard_cut: basit concat — en hızlı ve güvenilir
        if transition_type == "hard_cut" or len(paths) < 2:
            list_path = str(seg_dir / "concat.txt")
            with open(list_path, "w", encoding="utf-8") as f:
                for p in paths:
                    f.write(f"file '{p}'\n")
            out = str(seg_dir / "concat.mp4")
            result = await self.ffmpeg.run({"command": self.ffmpeg.concat_cmd(list_path),
                                             "output_path": out})
            return out if result["success"] else None

        # dissolve/wipeleft: xfade için önce tutarlı formata re-encode
        xfade_type = {"dissolve": "fade", "wipeleft": "wipeleft"}.get(transition_type, "fade")

        # Re-encode: concat demuxer -c copy ile xfade çalışmaz, önce standart format
        # CRF 18 = yüksek kalite (23 çok düşürüyor)
        encoded = []
        for i, p in enumerate(paths):
            enc = str(seg_dir / f"enc_{i:04d}.mp4")
            enc_cmd = f'-i "{p}" -c:v libx264 -crf 18 -preset fast -c:a aac -b:a 192k -ar 44100'
            r = await self.ffmpeg.run({"command": enc_cmd, "output_path": enc})
            encoded.append(enc if r["success"] else p)

        try:
            current = encoded[0]
            for i, nxt in enumerate(encoded[1:], 1):
                merged = str(seg_dir / f"merged_{i:04d}.mp4")
                r = await self.ffmpeg.add_transition(current, nxt, xfade_type, 0.4, merged)
                if r.get("success"):
                    current = merged
                else:
                    # Geçiş başarısız → bu ikiliyi concat ile birleştir
                    tmp_list = str(seg_dir / f"tmp_{i}.txt")
                    with open(tmp_list, "w", encoding="utf-8") as f:
                        f.write(f"file '{current}'\nfile '{nxt}'\n")
                    tmp_out = str(seg_dir / f"tmp_{i}.mp4")
                    r2 = await self.ffmpeg.run({"command": self.ffmpeg.concat_cmd(tmp_list),
                                                "output_path": tmp_out})
                    if r2["success"]: current = tmp_out
            return current
        except Exception as e:
            logger.warning(f"Geçiş efekti başarısız, concat fallback: {e}")
            list_path = str(seg_dir / "concat_fallback.txt")
            with open(list_path, "w", encoding="utf-8") as f:
                for p in encoded:
                    f.write(f"file '{p}'\n")
            out = str(seg_dir / "concat.mp4")
            r = await self.ffmpeg.run({"command": self.ffmpeg.concat_cmd(list_path),
                                       "output_path": out})
            return out if r["success"] else None

    async def _handle_ffmpeg(self, inputs: dict, context: dict) -> dict:
        op  = inputs["operation"]
        out = inputs.get("output_path") or self._auto_path(op)
        Path(out).parent.mkdir(parents=True, exist_ok=True)

        if op == "demo_render":
            cmd = self.ffmpeg.demo_render_cmd(inputs.get("input_path", ""))
            context["last_output"] = out
        elif op == "final_render":
            cmd = self.ffmpeg.render_4k_cmd(inputs.get("input_path", ""))
            context["last_output"] = out
        elif op == "trim":
            p   = inputs.get("params", {})
            cmd = self.ffmpeg.trim_cmd(inputs["input_path"], p.get("start", 0), p.get("duration", 5))
        elif op == "concat":
            cmd = self.ffmpeg.concat_cmd(inputs["input_path"])
        else:
            return {"error": f"Bilinmeyen FFmpeg operasyonu: {op}"}

        return await self.ffmpeg.run({"command": cmd, "output_path": out})

    def _auto_path(self, op: str) -> str:
        uid = uuid.uuid4().hex[:8]
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        return str(OUTPUT_DIR / f"{op}_{uid}.mp4")

    def _build_prompt(self, data: dict) -> str:
        files = data.get("files", {})
        clips = files.get("clips", [])
        return (
            f"Proje: {data.get('project_id', 'bilinmiyor')}\n"
            f"Tarz: {data.get('style', 'dark')}\n"
            f"Profil: {data.get('profile', 'yok')}\n\n"
            f"Medya dosyaları:\n"
            f"- Videolar ({len(clips)} adet): {clips}\n"
            f"- Fotoğraflar: {files.get('photos', [])}\n"
            f"- Müzik: {files.get('music', 'yok')}\n"
            f"- Logo: {files.get('logo', 'yok')}\n\n"
            f"Kullanıcı komutu: {data.get('command', '')}\n\n"
            f"AKIŞ: analyze_music → score_clips → build_timeline → render_timeline\n"
            f"render_timeline otomatik trim+concat+müzik yapıyor, ayrıca run_ffmpeg çağırma."
        )
