"""
Fotoğrafları video kliplere dönüştürür.
FFmpeg -loop 1 ile still görüntü → kısa MP4 (ken burns efekti opsiyonel).
"""
import asyncio
import logging
import uuid
import os
from pathlib import Path

logger = logging.getLogger(__name__)
TEMP_DIR = Path(os.getenv("TEMP_DIR", "./temp")).resolve()


async def photos_to_clips(photo_paths: list[str], duration: float = 3.0,
                           style: str = "dark") -> list[dict]:
    """
    Fotoğraf listesini video kliplere çevirir.
    Döner: scored_clips formatına uygun liste (path, total_score, best_offset, duration)
    """
    from agent.tools.photo_scorer import PhotoScorer
    from agent.tools.ffmpeg_tool import FFMPEG_BIN

    scorer  = PhotoScorer()
    scores  = await scorer.score(photo_paths)
    results = []

    out_dir = TEMP_DIR / "photo_clips"
    out_dir.mkdir(parents=True, exist_ok=True)

    for item in scores:
        path = item["path"]
        out  = str(out_dir / f"photo_{uuid.uuid4().hex[:8]}.mp4")
        ok   = await asyncio.to_thread(_convert, FFMPEG_BIN, path, out, duration, style)
        if ok:
            results.append({
                "path":        out,
                "source":      path,
                "total_score": item.get("total_score", 0.5),
                "best_offset": 0.0,
                "duration":    duration,
                "is_photo":    True,
            })
            logger.info(f"Fotoğraf → video: {Path(path).name} ({duration}s)")
        else:
            logger.warning(f"Fotoğraf dönüşümü başarısız: {path}")

    return results


def _convert(ffmpeg_bin: str, photo_path: str, out: str,
             duration: float, style: str) -> bool:
    import subprocess
    # Ken Burns efekti: yavaş zoom-in (dark/warm için daha dramatik)
    zoom_factor = "1.05" if style in ("dark", "warm") else "1.02"
    vf = (
        f"zoompan=z='min(zoom+0.0002,{zoom_factor})':d={int(duration*25)}:s=1920x1080:fps=25,"
        f"scale=1920:1080:force_original_aspect_ratio=decrease,"
        f"pad=1920:1080:(ow-iw)/2:(oh-ih)/2:black"
    )
    cmd = [
        ffmpeg_bin, "-y",
        "-loop", "1",
        "-i", photo_path,
        "-vf", vf,
        "-t", str(duration),
        "-c:v", "libx264", "-crf", "18", "-preset", "fast",
        "-pix_fmt", "yuv420p",
        "-an",
        out
    ]
    r = subprocess.run(cmd, capture_output=True, timeout=60)
    return r.returncode == 0 and Path(out).exists()
