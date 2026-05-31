import asyncio
import subprocess
import json
import logging
import shutil
import os
import time
import uuid
from pathlib import Path

logger = logging.getLogger(__name__)


def find_ffmpeg() -> tuple[str, str]:
    ffmpeg  = shutil.which("ffmpeg")
    ffprobe = shutil.which("ffprobe")
    if ffmpeg and ffprobe:
        return ffmpeg, ffprobe
    candidates = [
        r"C:\ffmpeg\bin\ffmpeg.exe",
        r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "ffmpeg", "bin", "ffmpeg.exe"),
    ]
    for c in candidates:
        if os.path.isfile(c):
            return c, c.replace("ffmpeg.exe", "ffprobe.exe")
    raise FileNotFoundError("ffmpeg bulunamadı — PATH'e ekle: https://ffmpeg.org")


try:
    FFMPEG_BIN, FFPROBE_BIN = find_ffmpeg()
except FileNotFoundError as _e:
    logger.warning(f"FFmpeg bulunamadı: {_e}")
    FFMPEG_BIN, FFPROBE_BIN = "ffmpeg", "ffprobe"

TEMP_DIR = Path(os.getenv("TEMP_DIR", "./temp")).resolve()

# Tarz bazlı renk profilleri — FFmpeg eq + colorbalance filtreleri
STYLE_COLOR = {
    "dark": "eq=contrast=1.25:brightness=-0.05:saturation=0.75,colorbalance=rs=-0.05:gs=-0.03:bs=0.08",
    "warm": "eq=contrast=1.1:brightness=0.04:saturation=1.15,colorbalance=rs=0.12:gs=0.04:bs=-0.08",
    "corp": "eq=contrast=1.05:brightness=0.02:saturation=0.95",
    "fast": "eq=contrast=1.3:brightness=0.03:saturation=1.2,colorbalance=rs=0.05:gs=0.02:bs=-0.05",
    "natural": "eq=contrast=1.0:brightness=0.0:saturation=1.0",
}


class FFmpegTool:

    # ── Temel Çalıştırıcı ─────────────────────────────────────────────────────

    async def run(self, inputs: dict) -> dict:
        cmd_str = f'"{FFMPEG_BIN}" -y {inputs["command"]} "{inputs["output_path"]}"'
        logger.info(f"FFmpeg: {cmd_str[:140]}")
        proc = await asyncio.create_subprocess_shell(
            cmd_str,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        success = proc.returncode == 0
        if not success:
            logger.error(f"FFmpeg hata: {stderr.decode(errors='replace')[-300:]}")
        return {
            "success":      success,
            "output_path":  inputs["output_path"],
            "returncode":   proc.returncode,
            "stderr_tail":  stderr.decode(errors="replace")[-300:]
        }

    # ── Temel Komut Şablonları ────────────────────────────────────────────────

    def trim_cmd(self, input_path: str, start: float, duration: float) -> str:
        start    = max(0.0, float(start))
        duration = max(0.1, float(duration))
        return f'-i "{input_path}" -ss {start:.3f} -t {duration:.3f} -c copy'

    def concat_cmd(self, filelist_path: str) -> str:
        return f'-f concat -safe 0 -i "{filelist_path}" -c copy'

    def render_cmd(self, input_path: str, resolution: str = "1920x1080",
                   crf: int = 23, preset: str = "medium") -> str:
        return (f'-i "{input_path}" -vf scale={resolution} '
                f'-c:v libx264 -crf {crf} -preset {preset} -c:a aac -b:a 192k')

    def render_4k_cmd(self, input_path: str) -> str:
        return (f'-i "{input_path}" -vf scale=3840:2160 '
                f'-c:v libx265 -crf 18 -preset slow -c:a aac -b:a 320k')

    def demo_render_cmd(self, input_path: str) -> str:
        return (f'-i "{input_path}" -vf scale=960:540 '
                f'-c:v libx264 -crf 28 -preset ultrafast -c:a aac -b:a 128k')

    # ── Renk Grading (FFmpeg natif) ───────────────────────────────────────────

    async def apply_color_grade(self, input_path: str, style: str = "dark",
                                 output_path: str = None) -> dict:
        """
        Tarz bazlı renk düzeltmesi — FFmpeg eq + colorbalance ile.
        DaVinci gerekmez, her zaman çalışır.
        style: dark | warm | corp | fast | natural
        """
        if not output_path:
            output_path = self._auto_path("grade")
        filter_str = STYLE_COLOR.get(style, STYLE_COLOR["corp"])
        cmd = f'-i "{input_path}" -vf "{filter_str}" -c:v libx264 -crf 20 -preset medium -c:a copy'
        result = await self.run({"command": cmd, "output_path": output_path})
        result["style"] = style
        return result

    async def apply_lut(self, input_path: str, lut_path: str,
                        output_path: str = None) -> dict:
        """
        .cube LUT dosyasını FFmpeg lut3d filtresi ile uygular.
        DaVinci gerekmez.
        """
        if not output_path:
            output_path = self._auto_path("lut")
        lut_escaped = lut_path.replace("\\", "/").replace(":", "\\:")
        cmd = f'-i "{input_path}" -vf "lut3d={lut_escaped}" -c:v libx264 -crf 20 -preset medium -c:a copy'
        return await self.run({"command": cmd, "output_path": output_path})

    # ── Logo Overlay ──────────────────────────────────────────────────────────

    async def add_logo(self, input_path: str, logo_path: str,
                       position: str = "bottom-right", fade_in: float = 0.8,
                       output_path: str = None) -> dict:
        """
        Video üzerine logo overlay + fade-in animasyonu ekler.
        After Effects gerekmez — FFmpeg overlay + fade filtresi.
        position: bottom-right | bottom-left | top-right | top-left | center
        """
        if not output_path:
            output_path = self._auto_path("logo")

        pos_map = {
            "bottom-right": "W-w-20:H-h-20",
            "bottom-left":  "20:H-h-20",
            "top-right":    "W-w-20:20",
            "top-left":     "20:20",
            "center":       "(W-w)/2:(H-h)/2",
        }
        pos = pos_map.get(position, pos_map["bottom-right"])

        filter_complex = (
            f"[1:v]scale=iw*0.15:-1,"
            f"fade=t=in:st=0:d={fade_in}:alpha=1[logo];"
            f"[0:v][logo]overlay={pos}"
        )
        cmd = (f'-i "{input_path}" -i "{logo_path}" '
               f'-filter_complex "{filter_complex}" '
               f'-c:v libx264 -crf 20 -preset medium -c:a copy')
        result = await self.run({"command": cmd, "output_path": output_path})
        result["position"] = position
        return result

    # ── Metin Overlay (Lower Third) ───────────────────────────────────────────

    async def add_text(self, input_path: str, title: str, subtitle: str = "",
                       position: str = "bottom", fade_in: float = 0.5,
                       duration: float = None, output_path: str = None) -> dict:
        """
        Video üzerine metin overlay ekler — FFmpeg drawtext.
        After Effects gerekmez.
        Özel karakterler otomatik escape edilir.
        """
        if not output_path:
            output_path = self._auto_path("text")

        def _esc(s: str) -> str:
            return s.replace("'", "\\'").replace(":", "\\:").replace(",", "\\,")

        total_dur   = self.get_duration(input_path) or 30
        show_dur    = duration or total_dur
        fade_end    = min(fade_in + show_dur, total_dur)

        y_title    = "h-100" if position == "bottom" else "30"
        y_subtitle = "h-60"  if position == "bottom" else "70"

        # Alpha: fade-in + fade-out
        alpha_expr = (
            f"if(lt(t,{fade_in}),t/{fade_in},"
            f"if(lt(t,{fade_end - 0.5}),1,"
            f"max(0,({fade_end}-t)/0.5)))"
        )

        filters = [
            f"drawtext=text='{_esc(title)}':"
            f"fontsize=56:fontcolor=white:x=(w-tw)/2:y={y_title}:"
            f"shadowcolor=black:shadowx=2:shadowy=2:"
            f"alpha='{alpha_expr}'"
        ]
        if subtitle:
            filters.append(
                f"drawtext=text='{_esc(subtitle)}':"
                f"fontsize=34:fontcolor=#cccccc:x=(w-tw)/2:y={y_subtitle}:"
                f"shadowcolor=black:shadowx=1:shadowy=1:"
                f"alpha='{alpha_expr}'"
            )

        vf = ",".join(filters)
        cmd = f'-i "{input_path}" -vf "{vf}" -c:v libx264 -crf 20 -preset medium -c:a copy'
        result = await self.run({"command": cmd, "output_path": output_path})
        result.update({"title": title, "subtitle": subtitle})
        return result

    # ── Geçiş Efektleri ───────────────────────────────────────────────────────

    async def add_transition(self, clip1: str, clip2: str,
                              transition: str = "fade", duration: float = 0.5,
                              output_path: str = None) -> dict:
        """
        İki klip arasına geçiş efekti ekler — FFmpeg xfade.
        Desteklenen: fade | dissolve | wipeleft | wiperight | slideleft | slideright
                     circleclose | radial | distance | pixelize
        """
        if not output_path:
            output_path = self._auto_path("transition")

        dur1 = self.get_duration(clip1)
        if dur1 <= 0:
            return {"success": False, "error": "clip1 süresi alınamadı"}

        offset = max(0.0, dur1 - duration)
        cmd = (f'-i "{clip1}" -i "{clip2}" '
               f'-filter_complex "xfade=transition={transition}:duration={duration:.2f}:offset={offset:.3f}" '
               f'-c:v libx264 -crf 20 -preset medium')
        result = await self.run({"command": cmd, "output_path": output_path})
        result["transition"] = transition
        return result

    async def flash_transition(self, input_path: str, flash_at: float = 0.0,
                                duration: float = 0.4, output_path: str = None) -> dict:
        """Beyaz flash geçiş efekti."""
        if not output_path:
            output_path = self._auto_path("flash")
        half = duration / 2
        vf = (
            f"geq=r='if(between(t,{flash_at},{flash_at+half}),(t-{flash_at})/{half}*255,255)':"
            f"g='if(between(t,{flash_at},{flash_at+half}),(t-{flash_at})/{half}*255,255)':"
            f"b='if(between(t,{flash_at},{flash_at+half}),(t-{flash_at})/{half}*255,255)'"
        )
        cmd = f'-i "{input_path}" -vf "{vf}" -c:v libx264 -crf 20 -preset medium -c:a copy'
        return await self.run({"command": cmd, "output_path": output_path})

    # ── Ses İşlemleri ─────────────────────────────────────────────────────────

    async def normalize_audio(self, input_path: str, output_path: str = None) -> dict:
        """Ses seviyesini EBU R128 standardına göre normalize eder."""
        if not output_path:
            output_path = self._auto_path("normalized")
        cmd = (f'-i "{input_path}" '
               f'-af "loudnorm=I=-23:LRA=7:TP=-2" '
               f'-c:v copy -c:a aac -b:a 192k')
        return await self.run({"command": cmd, "output_path": output_path})

    async def add_music(self, video_path: str, music_path: str,
                        output_path: str = None, video_vol: float = 0.3,
                        music_vol: float = 1.0) -> dict:
        """Video sesini kısıp müzik ekler — video sesi arka planda kalır."""
        if not output_path:
            output_path = self._auto_path("music_mix")
        cmd = (f'-i "{video_path}" -i "{music_path}" '
               f'-filter_complex "[0:a]volume={video_vol}[va];[1:a]volume={music_vol}[ma];[va][ma]amix=inputs=2[a]" '
               f'-map 0:v -map "[a]" -c:v copy -c:a aac -b:a 192k -shortest')
        return await self.run({"command": cmd, "output_path": output_path})

    # ── Yardımcı Metodlar ─────────────────────────────────────────────────────

    def get_duration(self, file_path: str) -> float:
        result = subprocess.run(
            [FFPROBE_BIN, "-v", "quiet", "-show_entries",
             "format=duration", "-of", "csv=p=0", file_path],
            capture_output=True, text=True
        )
        try:
            return float(result.stdout.strip())
        except ValueError:
            return 0.0

    def get_video_info(self, file_path: str) -> dict:
        result = subprocess.run(
            [FFPROBE_BIN, "-v", "quiet", "-print_format", "json",
             "-show_streams", "-show_format", file_path],
            capture_output=True, text=True
        )
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError:
            return {}

    def _auto_path(self, prefix: str) -> str:
        out = TEMP_DIR / "output"
        out.mkdir(parents=True, exist_ok=True)
        return str(out / f"{prefix}_{uuid.uuid4().hex[:8]}.mp4")
