import anthropic
import asyncio
import logging
import os
import time
from pathlib import Path
from agent.tools.music_analyzer import MusicAnalyzer
from agent.tools.clip_scorer import ClipScorer
from agent.tools.ffmpeg_tool import FFmpegTool
from agent.tools.auto_editor import build_timeline, write_concat_list

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
    }
]


class ClaudeClient:

    def __init__(self):
        # Senkron client — asyncio.to_thread ile event loop bloklanmaz
        self.client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self.music  = MusicAnalyzer()
        self.scorer = ClipScorer()
        self.ffmpeg = FFmpegTool()
        TEMP_DIR.mkdir(parents=True, exist_ok=True)

    async def process(self, data: dict):
        command = data.get("command", "").strip()
        if not command:
            yield {"type": "error", "message": "Komut boş olamaz"}
            return

        messages = [{"role": "user", "content": self._build_prompt(data)}]
        context  = {
            "files":    data.get("files", {}),
            "style":    data.get("style", "dark"),
            "project":  data.get("project_id", f"proj_{int(time.time())}"),
            "timeline": None,
        }

        yield {"type": "progress", "step": "claude_thinking", "status": "running",
               "message": "Claude düşünüyor..."}

        while True:
            # Senkron API çağrısını thread'e taşı — event loop bloke olmaz
            response = await asyncio.to_thread(
                self.client.messages.create,
                model="claude-sonnet-4-6",
                max_tokens=4096,
                system=SYSTEM_PROMPT,
                tools=TOOLS,
                messages=messages
            )

            if response.stop_reason == "end_turn":
                text = next((b.text for b in response.content if hasattr(b, "text")), "")
                result = {"type": "result", "text": text}
                if context.get("last_output"):
                    result["output_path"] = context["last_output"]
                if context.get("timeline"):
                    result["timeline"] = context["timeline"]
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
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": str(result)
                    })

                messages.append({"role": "user", "content": tool_results})

            else:
                logger.warning(f"Beklenmeyen stop_reason: {response.stop_reason}")
                break

    async def _run_tool(self, name: str, inputs: dict, context: dict) -> dict:
        try:
            if name == "analyze_music":
                return await self.music.analyze(inputs["file_path"])

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
                return await self._render_timeline(inputs, context)

            if name == "run_ffmpeg":
                return await self._handle_ffmpeg(inputs, context)

            return {"error": f"Bilinmeyen araç: {name}"}

        except Exception as e:
            logger.error(f"Tool hatası [{name}]: {e}", exc_info=True)
            return {"error": str(e)}

    async def _render_timeline(self, inputs: dict, context: dict) -> dict:
        """Timeline segmentlerini trim+concat+müzik ile tek video'ya dönüştürür."""
        timeline   = inputs.get("timeline") or context.get("timeline")
        music_path = inputs.get("music_path") or context["files"].get("music")
        quality    = inputs.get("quality", "demo")

        if not timeline:
            return {"error": "Timeline boş — önce build_timeline çalıştır"}

        project_id = context.get("project", f"proj_{int(time.time())}")
        seg_dir    = TEMP_DIR / project_id
        seg_dir.mkdir(parents=True, exist_ok=True)

        # Adım 1: Her segmenti trim et
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

        # Adım 2: Concat
        list_path = str(seg_dir / "concat.txt")
        with open(list_path, "w", encoding="utf-8") as f:
            for p in trimmed:
                f.write(f"file '{p}'\n")

        concat_out = str(seg_dir / "concat.mp4")
        cmd        = self.ffmpeg.concat_cmd(list_path)
        result     = await self.ffmpeg.run({"command": cmd, "output_path": concat_out})
        if not result["success"]:
            return {"error": f"Concat başarısız: {result.get('stderr_tail','')[:200]}"}

        # Adım 3: Müzik ekle + render
        suffix  = f"_{int(time.time())}"
        out_dir = TEMP_DIR / "output"
        out_dir.mkdir(exist_ok=True)

        if quality == "final":
            out_path = str(out_dir / f"final{suffix}.mp4")
            if music_path:
                cmd = (f'-i "{concat_out}" -i "{music_path}" '
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
        ts  = int(time.time())
        out = TEMP_DIR / "output"
        out.mkdir(exist_ok=True)
        return str(out / f"{op}_{ts}.mp4")

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
