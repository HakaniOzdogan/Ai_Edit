import asyncio
import subprocess
import json
import logging
import shutil
import os
from pathlib import Path

logger = logging.getLogger(__name__)


def find_ffmpeg() -> tuple[str, str]:
    ffmpeg = shutil.which("ffmpeg")
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
            ffmpeg = c
            ffprobe = c.replace("ffmpeg.exe", "ffprobe.exe")
            return ffmpeg, ffprobe
    raise FileNotFoundError("ffmpeg bulunamadı — PATH'e ekle: https://ffmpeg.org")


try:
    FFMPEG_BIN, FFPROBE_BIN = find_ffmpeg()
except FileNotFoundError as _e:
    logger.warning(f"FFmpeg bulunamadı — tool'lar devre dışı: {_e}")
    FFMPEG_BIN, FFPROBE_BIN = "ffmpeg", "ffprobe"


class FFmpegTool:

    async def run(self, inputs: dict) -> dict:
        cmd_str = f'"{FFMPEG_BIN}" -y {inputs["command"]} "{inputs["output_path"]}"'
        logger.info(f"FFmpeg: {cmd_str[:120]}")
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
            "success": success,
            "output_path": inputs["output_path"],
            "returncode": proc.returncode,
            "stderr_tail": stderr.decode(errors="replace")[-300:]
        }

    def trim_cmd(self, input_path: str, start: float, duration: float) -> str:
        return f'-i "{input_path}" -ss {start:.3f} -t {duration:.3f} -c copy'

    def concat_cmd(self, filelist_path: str) -> str:
        return f'-f concat -safe 0 -i "{filelist_path}" -c copy'

    def render_cmd(self, input_path: str, resolution: str = "1920x1080",
                   crf: int = 23, preset: str = "medium") -> str:
        return (
            f'-i "{input_path}" '
            f"-vf scale={resolution} "
            f"-c:v libx264 -crf {crf} -preset {preset} "
            f"-c:a aac -b:a 192k"
        )

    def render_4k_cmd(self, input_path: str) -> str:
        return (
            f'-i "{input_path}" '
            f"-vf scale=3840:2160 "
            f"-c:v libx265 -crf 18 -preset slow "
            f"-c:a aac -b:a 320k"
        )

    def demo_render_cmd(self, input_path: str) -> str:
        return (
            f'-i "{input_path}" '
            f"-vf scale=960:540 "
            f"-c:v libx264 -crf 28 -preset ultrafast "
            f"-c:a aac -b:a 128k"
        )

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
