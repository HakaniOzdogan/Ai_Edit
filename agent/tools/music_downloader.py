"""
Müzik İndirici — YouTube ve Spotify linklerinden müzik indirir.
yt-dlp: YouTube, SoundCloud, Dailymotion vb.
spotdl: Spotify (YouTube'dan aynı parçayı bulup indirir)
"""
import asyncio
import logging
import os
import re
import uuid
from pathlib import Path

logger = logging.getLogger(__name__)
MUSIC_DIR = Path(os.getenv("PROJECTS_DIR", "./projects")).parent / "music_cache"


def detect_source(url: str) -> str:
    """URL'nin kaynağını tespit et."""
    url = url.lower()
    if "spotify.com" in url:
        return "spotify"
    if any(d in url for d in ["youtube.com", "youtu.be", "music.youtube"]):
        return "youtube"
    if "soundcloud.com" in url:
        return "soundcloud"
    return "unknown"


async def download_music(url: str, output_dir: str = None) -> dict:
    """
    URL'den müzik indirir. MP3 döner.
    Desteklenen: YouTube, Spotify, SoundCloud
    """
    MUSIC_DIR.mkdir(parents=True, exist_ok=True)
    out_dir  = Path(output_dir) if output_dir else MUSIC_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    source = detect_source(url)
    uid    = uuid.uuid4().hex[:8]

    if source == "spotify":
        return await _download_spotify(url, out_dir, uid)
    elif source in ("youtube", "soundcloud"):
        return await _download_ytdlp(url, out_dir, uid)
    else:
        # Bilinmeyen URL — yt-dlp ile dene
        return await _download_ytdlp(url, out_dir, uid)


async def _download_ytdlp(url: str, out_dir: Path, uid: str) -> dict:
    """yt-dlp ile YouTube/SoundCloud/diğer indirme."""
    out_template = str(out_dir / f"music_{uid}.%(ext)s")

    cmd = [
        "venv/Scripts/python.exe" if Path("venv/Scripts/python.exe").exists() else "python",
        "-m", "yt_dlp",
        "--extract-audio",
        "--audio-format", "mp3",
        "--audio-quality", "0",          # En iyi kalite
        "--output", out_template,
        "--no-playlist",
        "--quiet",
        "--no-warnings",
        url
    ]

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        cwd=str(Path(__file__).parent.parent.parent),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)
    except asyncio.TimeoutError:
        proc.kill()
        return {"ok": False, "error": "İndirme 120 saniye içinde tamamlanamadı"}

    # Çıktı dosyasını bul
    mp3_files = list(out_dir.glob(f"music_{uid}*.mp3"))
    if mp3_files:
        out_path = str(mp3_files[0])
        size_mb  = round(mp3_files[0].stat().st_size / 1024 / 1024, 1)
        logger.info(f"İndirildi: {out_path} ({size_mb} MB)")
        return {"ok": True, "path": out_path, "source": "youtube", "size_mb": size_mb}

    err = stderr.decode(errors="replace")[-300:]
    logger.error(f"yt-dlp hata: {err}")
    return {"ok": False, "error": f"İndirme başarısız: {err[:150]}"}


async def _download_spotify(url: str, out_dir: Path, uid: str) -> dict:
    """
    Spotify: spotdl ile indir (YouTube'dan aynı parçayı bulur).
    spotdl kurulu değilse yt-dlp fallback yok — hata ver.
    """
    try:
        import spotdl  # noqa
    except ImportError:
        return {"ok": False, "error": "spotdl kurulu değil. pip install spotdl çalıştır."}

    cmd = [
        "venv/Scripts/python.exe" if Path("venv/Scripts/python.exe").exists() else "python",
        "-m", "spotdl",
        "--output", str(out_dir / f"music_{uid}.mp3"),
        "--format", "mp3",
        "--bitrate", "320k",
        url
    ]
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        cwd=str(Path(__file__).parent.parent.parent),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=180)
    except asyncio.TimeoutError:
        proc.kill()
        return {"ok": False, "error": "Spotify indirme 180sn içinde tamamlanamadı"}

    mp3_files = list(out_dir.glob(f"music_{uid}*.mp3"))
    if not mp3_files:
        # spotdl dosyayı farklı isimle kaydedebilir
        mp3_files = sorted(out_dir.glob("*.mp3"), key=lambda f: f.stat().st_mtime, reverse=True)

    if mp3_files:
        out_path = str(mp3_files[0])
        size_mb  = round(mp3_files[0].stat().st_size / 1024 / 1024, 1)
        return {"ok": True, "path": out_path, "source": "spotify", "size_mb": size_mb}

    err = (stdout.decode(errors="replace") + stderr.decode(errors="replace"))[-300:]
    return {"ok": False, "error": f"Spotify indirme başarısız: {err[:150]}"}


async def get_info(url: str) -> dict:
    """İndirmeden önce parça bilgisini al (başlık, süre)."""
    source = detect_source(url)

    try:
        cmd = [
            "venv/Scripts/python.exe" if Path("venv/Scripts/python.exe").exists() else "python",
            "-m", "yt_dlp",
            "--dump-json", "--no-playlist", "--quiet",
            url
        ]
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=str(Path(__file__).parent.parent.parent),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=15)

        import json
        data     = json.loads(stdout.decode(errors="replace"))
        duration = data.get("duration", 0)
        title    = data.get("title", "Bilinmeyen Parça")
        return {
            "ok":       True,
            "title":    title,
            "duration": duration,
            "source":   source,
            "uploader": data.get("uploader", ""),
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}
