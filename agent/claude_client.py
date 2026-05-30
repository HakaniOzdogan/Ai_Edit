import anthropic
import logging
import os
from pathlib import Path
from agent.tools.music_analyzer import MusicAnalyzer
from agent.tools.clip_scorer import ClipScorer
from agent.tools.ffmpeg_tool import FFmpegTool
from agent.tools.auto_editor import build_timeline

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """
Sen AI Video Editor sisteminin karar motorusun.
Kullanıcı sana ham video/fotoğraf ve müzik atar;
sen analiz ederek profesyonel bir kurgu oluşturursun.

ARAÇLARIN:
- analyze_music  : Müzik BPM, beat ve drop tespiti
- score_clips    : Video klip kalite skorlaması
- run_ffmpeg     : Video kesme, birleştirme, render
- build_timeline : Beat-sync otomatik kurgu oluşturma

KURGU KURALLARI:
- Her zaman önce müziği analiz et (analyze_music)
- Ardından klipleri skorla (score_clips)
- Timeline'ı kurgula (build_timeline)
- Demo render al (run_ffmpeg — demo_render)
- Final render 4K H.265 olsun

TARZ TANIMLARI:
- dark_cinematic : 4 beat/sahne, desature, cool ton
- fast_cut       : 1 beat/sahne, high contrast, warm
- corporate      : 2 beat/sahne, clean, neutral
- warm_lifestyle : 3 beat/sahne, warm LUT, soft geçiş

YANIT KURALLARI:
- Her tool çağrısından önce kısaca ne yapacağını söyle
- İşlem sonucunu her zaman özetle
- Hata varsa açıkça belirt ve alternatif öner
- Türkçe yanıt ver
- Maksimum 5 tool çağrısı yap, sonra end_turn yap
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
        "description": "Video kliplerini kalite açısından puanlar. Parlaklık, keskinlik, hareket analizi yapar.",
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
        "description": "Beat analizine göre otomatik kurgu timeline oluşturur.",
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
        "name": "run_ffmpeg",
        "description": "FFmpeg ile video işlemi yapar. Trim, concat, demo render veya final render.",
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
        self.client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self.music  = MusicAnalyzer()
        self.scorer = ClipScorer()
        self.ffmpeg = FFmpegTool()

    async def process(self, data: dict):
        messages = [{"role": "user", "content": self._build_prompt(data)}]
        context  = {"files": data.get("files", {}), "style": data.get("style", "dark")}

        yield {"type": "progress", "step": "claude_thinking", "status": "running",
               "message": "Claude düşünüyor..."}

        while True:
            response = self.client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=4096,
                system=SYSTEM_PROMPT,
                tools=TOOLS,
                messages=messages
            )

            if response.stop_reason == "end_turn":
                text = next(
                    (b.text for b in response.content if hasattr(b, "text")), ""
                )
                yield {"type": "result", "text": text}
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
                # Beklenmeyen stop_reason
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

            if name == "run_ffmpeg":
                return await self._handle_ffmpeg(inputs, context)

            return {"error": f"Bilinmeyen araç: {name}"}

        except Exception as e:
            logger.error(f"Tool hatası [{name}]: {e}", exc_info=True)
            return {"error": str(e)}

    async def _handle_ffmpeg(self, inputs: dict, context: dict) -> dict:
        op  = inputs["operation"]
        out = inputs["output_path"]
        Path(out).parent.mkdir(parents=True, exist_ok=True)

        if op == "demo_render":
            cmd = self.ffmpeg.demo_render_cmd(inputs.get("input_path", ""))
        elif op == "final_render":
            cmd = self.ffmpeg.render_4k_cmd(inputs.get("input_path", ""))
        elif op == "trim":
            p   = inputs.get("params", {})
            cmd = self.ffmpeg.trim_cmd(inputs["input_path"], p.get("start", 0), p.get("duration", 5))
        elif op == "concat":
            cmd = self.ffmpeg.concat_cmd(inputs["input_path"])
        else:
            return {"error": f"Bilinmeyen FFmpeg operasyonu: {op}"}

        return await self.ffmpeg.run({"command": cmd, "output_path": out})

    def _build_prompt(self, data: dict) -> str:
        files = data.get("files", {})
        return (
            f"Proje: {data.get('project_id', 'bilinmiyor')}\n"
            f"Tarz: {data.get('style', 'dark')}\n"
            f"Profil: {data.get('profile', 'yok')}\n\n"
            f"Medya dosyaları:\n"
            f"- Videolar: {files.get('clips', [])}\n"
            f"- Fotoğraflar: {files.get('photos', [])}\n"
            f"- Müzik: {files.get('music', 'yok')}\n"
            f"- Logo: {files.get('logo', 'yok')}\n\n"
            f"Kullanıcı komutu: {data.get('command', '')}\n\n"
            f"Yukarıdaki medyaları kullanarak profesyonel bir kurgu oluştur.\n"
            f"Önce müziği analiz et, sonra klipleri skorla, timeline kurgula ve demo render al."
        )
