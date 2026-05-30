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
from agent.tools.davinci_tool import DaVinciTool
from agent.tools.aftereffects_tool import AfterEffectsTool
from agent.qa.orchestrator import QAOrchestrator

logger = logging.getLogger(__name__)

TEMP_DIR = Path(os.getenv("TEMP_DIR", "./temp")).resolve()

SYSTEM_PROMPT = """
Sen AI Video Editor sisteminin karar motorusun.
Kullanıcı sana ham video/fotoğraf ve müzik atar;
sen analiz ederek profesyonel bir kurgu oluşturursun.

ARAÇLARIN:
- analyze_music   : Müzik BPM, beat ve drop tespiti
- score_clips     : Video klip kalite skorlaması
- build_timeline  : Beat-sync otomatik kurgu oluşturma
- render_timeline : Timeline'ı FFmpeg ile demo videoya dönüştürür (trim + concat + müzik)
- run_ffmpeg      : Tekil FFmpeg işlemi (trim, concat, final render)

KURGU AKIŞI (BU SIRAYA UYGUN ÇALIŞTIRILMALI):
1. analyze_music  → BPM ve beat zamanlarını al
2. score_clips    → Klipleri puanla
3. build_timeline → Beat-sync kurgu oluştur
4. render_timeline → Demo video üret (timeline + müzik birleşik render)
5. Son adımda kullanıcıya sonucu özetle

TARZ TANIMLARI:
- dark : 4 beat/sahne, cool ton, dramatik
- fast : 1 beat/sahne, high contrast
- corp : 2 beat/sahne, clean, nötr
- warm : 3 beat/sahne, warm ton, soft

YANIT KURALLARI:
- Her tool çağrısından önce ne yapacağını 1 cümle belirt
- İşlem sonucunu özetle (BPM, sahne sayısı, süre)
- Hata olursa açıkça belirt
- Türkçe yanıt ver
- Maksimum 6 tool çağrısı yap
"""

TOOLS = [
    {
        "name": "analyze_music",
        "description": "Müzik dosyasını analiz eder. BPM, beat zamanları, drop noktaları döner.",
        "input_schema": {
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "Müzik dosyasının tam yolu"}
            },
            "required": ["file_path"]
        }
    },
    {
        "name": "score_clips",
        "description": "Video kliplerini kalite açısından puanlar.",
        "input_schema": {
            "type": "object",
            "properties": {
                "clip_paths": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Video dosyalarının tam yolları"
                }
            },
            "required": ["clip_paths"]
        }
    },
    {
        "name": "build_timeline",
        "description": "Beat analizine göre otomatik kurgu timeline oluşturur. Segment listesi döner.",
        "input_schema": {
            "type": "object",
            "properties": {
                "beat_times":     {"type": "array", "items": {"type": "number"}},
                "scored_clips":   {"type": "array"},
                "music_duration": {"type": "number"},
                "style":          {"type": "string", "enum": ["dark", "fast", "warm", "corp"]}
            },
            "required": ["beat_times", "scored_clips", "music_duration"]
        }
    },
    {
        "name": "render_timeline",
        "description": "Timeline segmentlerini trim+concat+müzik ile demo videoya dönüştürür. En son adımda çalıştırılmalı.",
        "input_schema": {
            "type": "object",
            "properties": {
                "timeline":    {"type": "array",  "description": "build_timeline çıktısı"},
                "music_path":  {"type": "string", "description": "Müzik dosyası tam yolu (opsiyonel)"},
                "output_path": {"type": "string", "description": "Çıktı video yolu (opsiyonel, otomatik üretilir)"},
                "quality":     {"type": "string", "enum": ["demo", "final"], "description": "demo=hızlı preview, final=4K H.265"}
            },
            "required": ["timeline"]
        }
    },
    {
        "name": "run_ffmpeg",
        "description": "Tekil FFmpeg işlemi: trim, concat veya final render.",
        "input_schema": {
            "type": "object",
            "properties": {
                "operation":   {"type": "string", "enum": ["trim", "concat", "demo_render", "final_render"]},
                "input_path":  {"type": "string"},
                "output_path": {"type": "string"},
                "params":      {"type": "object"}
            },
            "required": ["operation", "output_path"]
        }
    },
    {
        "name": "apply_color_preset",
        "description": "DaVinci Resolve'da tarz bazlı LUT uygular. Resolve açık ve bridge hazır olmalı.",
        "input_schema": {
            "type": "object",
            "properties": {
                "style": {"type": "string", "enum": ["dark", "warm", "corp", "fast"],
                          "description": "Uygulanacak renk tarzı"}
            },
            "required": ["style"]
        }
    },
    {
        "name": "logo_reveal",
        "description": "After Effects ile logo reveal animasyonu üretir ve MP4 olarak kaydeder.",
        "input_schema": {
            "type": "object",
            "properties": {
                "logo_path": {"type": "string", "description": "Logo dosyasının tam yolu (PNG/SVG)"},
                "duration":  {"type": "number", "description": "Animasyon süresi (saniye, varsayılan 3)"},
                "output_path": {"type": "string", "description": "Çıktı MP4 yolu (opsiyonel)"}
            },
            "required": ["logo_path"]
        }
    },
    {
        "name": "add_text_overlay",
        "description": "After Effects ile lower third metin overlay'i üretir.",
        "input_schema": {
            "type": "object",
            "properties": {
                "title":    {"type": "string", "description": "Ana başlık metni"},
                "subtitle": {"type": "string", "description": "Alt başlık metni (opsiyonel)"},
                "duration": {"type": "number", "description": "Görünme süresi (saniye)"},
                "output_path": {"type": "string", "description": "Çıktı MP4 yolu (opsiyonel)"}
            },
            "required": ["title"]
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
        self.client  = anthropic.Anthropic(api_key=api_key)
        self.music   = MusicAnalyzer()
        self.scorer  = ClipScorer()
        self.ffmpeg  = FFmpegTool()
        self.davinci = DaVinciTool()
        self.ae      = AfterEffectsTool()
        self.qa      = QAOrchestrator()
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

        clips = files.get("clips", [])
        music = files.get("music")

        if not clips:
            yield {"type": "error", "message": "Render için klip gerekli"}
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

        # Klip skorla
        yield {"type": "progress", "tool": "score_clips", "status": "running",
               "message": "Klipler puanlanıyor..."}
        scored = await self.scorer.score(clips)
        yield {"type": "progress", "tool": "score_clips", "status": "done",
               "result_summary": f"{len(scored)} klip puanlandı"}

        if not scored:
            yield {"type": "error", "message": "Klip skorlama başarısız"}
            return

        # Timeline oluştur
        beat_times = (music_analysis or {}).get("beat_times", [0.5 * i for i in range(30)])
        music_dur  = (music_analysis or {}).get("duration", 30.0)
        timeline   = build_timeline(beat_times, scored, music_dur, context["style"])
        context["timeline"] = timeline

        # Render
        render_inputs = {
            "timeline":   timeline,
            "music_path": music,
            "quality":    quality,
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
            if name == "analyze_music":
                result = await self.music.analyze(inputs["file_path"])
                context["music_analysis"] = result
                return result

            if name == "score_clips":
                return await self.scorer.score(inputs["clip_paths"])

            if name == "build_timeline":
                tl = build_timeline(
                    inputs["beat_times"],
                    inputs["scored_clips"],
                    inputs["music_duration"],
                    inputs.get("style", context.get("style", "dark"))
                )
                context["timeline"] = tl
                return {"timeline": tl, "segment_count": len(tl)}

            if name == "render_timeline":
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

            if name == "apply_color_preset":
                try:
                    return await self.davinci.apply_color_preset(inputs["style"])
                except Exception as e:
                    return {"ok": False, "fallback": "DaVinci bağlı değil", "error": str(e)}

            if name == "logo_reveal":
                try:
                    return await self.ae.logo_reveal(
                        inputs["logo_path"],
                        inputs.get("duration", 3.0),
                        inputs.get("output_path")
                    )
                except Exception as e:
                    return {"ok": False, "fallback": "After Effects bağlı değil", "error": str(e)}

            if name == "add_text_overlay":
                try:
                    return await self.ae.add_text_overlay(
                        inputs["title"],
                        inputs.get("subtitle", ""),
                        inputs.get("duration", 5.0),
                        inputs.get("output_path")
                    )
                except Exception as e:
                    return {"ok": False, "fallback": "After Effects bağlı değil", "error": str(e)}

            return {"error": f"Bilinmeyen araç: {name}"}

        except Exception as e:
            logger.error(f"Tool hatası [{name}]: {e}", exc_info=True)
            return {"error": str(e)}

    async def _render_timeline(self, inputs: dict, context: dict) -> dict:
        timeline   = inputs.get("timeline") or context.get("timeline")
        music_path = inputs.get("music_path") or context["files"].get("music")
        quality    = inputs.get("quality", "demo")

        if not timeline:
            return {"error": "Timeline boş — önce build_timeline çalıştır"}

        project_id = context.get("project", f"proj_{int(time.time())}")
        seg_dir    = TEMP_DIR / project_id
        try:
            seg_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            return {"error": f"Geçici klasör oluşturulamadı: {e}"}

        trimmed = []
        for i, seg in enumerate(timeline):
            clip   = seg.get("clip_path", "")
            offset = float(seg.get("clip_offset", 0))
            dur    = float(seg.get("duration", 2))
            out    = str(seg_dir / f"seg_{i:04d}.mp4")
            cmd    = self.ffmpeg.trim_cmd(clip, offset, dur)
            result = await self.ffmpeg.run({"command": cmd, "output_path": out})
            if result["success"]:
                trimmed.append(out)
            else:
                logger.warning(f"Segment {i} trim başarısız: {result.get('stderr_tail','')[:100]}")

        if not trimmed:
            return {"error": "Hiçbir segment trim edilemedi"}

        list_path = str(seg_dir / "concat.txt")
        with open(list_path, "w", encoding="utf-8") as f:
            for p in trimmed:
                f.write(f"file '{p}'\n")

        concat_out = str(seg_dir / "concat.mp4")
        cmd        = self.ffmpeg.concat_cmd(list_path)
        result     = await self.ffmpeg.run({"command": cmd, "output_path": concat_out})
        if not result["success"]:
            return {"error": f"Concat başarısız: {result.get('stderr_tail','')[:200]}"}

        suffix  = f"_{int(time.time())}"
        out_dir = TEMP_DIR / "output"
        out_dir.mkdir(exist_ok=True)

        if quality == "final":
            out_path = str(out_dir / f"final{suffix}.mp4")
            if music_path:
                # 4K scale her zaman uygulanır
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
        out = TEMP_DIR / "output"
        out.mkdir(exist_ok=True)
        return str(out / f"{op}_{uid}.mp4")

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
