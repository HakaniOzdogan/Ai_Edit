"""
Referans Video Analizörü
URL veya lokal dosyadan marka profili oluşturur.
- yt-dlp ile URL indirme
- FFprobe ile ortalama kesim hızı
- Librosa ile BPM
- OpenCV ile renk tonu
"""
import asyncio
import json
import logging
import os
import subprocess
import tempfile
from pathlib import Path

_cv2 = None
_np  = None

def _load_cv2():
    global _cv2, _np
    if _cv2 is None:
        import cv2 as c; import numpy as n
        _cv2 = c; _np = n

from agent.models.profile import BrandProfile

logger = logging.getLogger(__name__)

PROFILES_DIR = Path(os.getenv("PROFILES_DIR", "./profiles"))
TEMP_DIR     = Path(os.getenv("TEMP_DIR", "./temp"))


class ReferenceAnalyzer:

    async def analyze(self, source: str, name: str = None) -> dict:
        """
        URL veya lokal video yolundan BrandProfile üretir.
        Profili profiles/{name}.json'a kaydeder.
        """
        PROFILES_DIR.mkdir(exist_ok=True)
        TEMP_DIR.mkdir(exist_ok=True)

        local_path = source
        downloaded = False

        # URL ise yt-dlp ile indir
        if source.startswith("http://") or source.startswith("https://"):
            local_path, downloaded = await self._download(source)
            if not local_path:
                return {"ok": False, "error": "İndirme başarısız"}

        if not Path(local_path).exists():
            return {"ok": False, "error": f"Dosya bulunamadı: {local_path}"}

        try:
            profile_data = await self._extract_profile(local_path)
        finally:
            if downloaded and local_path:
                Path(local_path).unlink(missing_ok=True)

        profile_name = name or Path(source).stem[:30] or f"ref_{int(asyncio.get_event_loop().time())}"
        profile_data["name"] = profile_name

        profile = BrandProfile(**profile_data)
        out_path = PROFILES_DIR / f"{profile_name}.json"
        out_path.write_text(profile.model_dump_json(indent=2), encoding="utf-8")
        logger.info(f"Profil kaydedildi: {out_path}")

        return {"ok": True, "profile": profile.model_dump(), "path": str(out_path)}

    async def _download(self, url: str) -> tuple[str | None, bool]:
        """yt-dlp ile video indir."""
        out_path = str(TEMP_DIR / "ref_download.mp4")
        cmd = ["yt-dlp", "-f", "mp4/best[height<=720]",
               "-o", out_path, "--no-playlist", url]
        try:
            result = await asyncio.to_thread(
                subprocess.run, cmd, capture_output=True, timeout=120
            )
            if result.returncode == 0 and Path(out_path).exists():
                return out_path, True
            logger.error(f"yt-dlp hata: {result.stderr.decode(errors='replace')[:200]}")
            return None, False
        except Exception as e:
            logger.error(f"İndirme hatası: {e}")
            return None, False

    async def _extract_profile(self, video_path: str) -> dict:
        """Video'dan stil bilgilerini çıkarır."""
        duration, scene_cuts = await asyncio.to_thread(self._get_scene_info, video_path)
        avg_cut_duration = round(duration / max(scene_cuts, 1), 2)

        color_tone = await asyncio.to_thread(self._get_color_tone, video_path)
        bpm        = await self._estimate_bpm(video_path)

        # Kesim hızından geçiş tipi tahmini
        if avg_cut_duration < 1.5:
            transition_style = "hard_cut"
        elif avg_cut_duration < 3.0:
            transition_style = "dissolve"
        else:
            transition_style = "whip_pan"

        # Renk + BPM'den stil etiketi
        if color_tone == "cool" and bpm > 100:
            style_tag = "dark"
        elif color_tone == "warm":
            style_tag = "warm"
        elif bpm < 90:
            style_tag = "corp"
        else:
            style_tag = "fast"

        from datetime import datetime
        return {
            "bpm":              round(bpm, 1),
            "avg_cut_duration": avg_cut_duration,
            "color_tone":       color_tone,
            "transition_style": transition_style,
            "style_tag":        style_tag,
            "lut_file":         None,
            "created_at":       datetime.now().isoformat(),
        }

    def _get_scene_info(self, video_path: str) -> tuple[float, int]:
        """FFprobe ile video süresi, scene_detect ile kesim sayısı."""
        # Süre
        r = subprocess.run(
            ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
             "-of", "csv=p=0", video_path],
            capture_output=True, text=True
        )
        try:
            duration = float(r.stdout.strip())
        except ValueError:
            duration = 30.0

        # Sahne tespiti (histogram farkı)
        _load_cv2()
        cv2 = _cv2
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
        step = max(1, int(fps))
        prev_hist = None
        cuts = 0
        frame_idx = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            if frame_idx % step == 0:
                hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
                hist = cv2.calcHist([hsv], [0], None, [50], [0, 180])
                cv2.normalize(hist, hist)
                if prev_hist is not None:
                    diff = cv2.compareHist(prev_hist, hist, cv2.HISTCMP_BHATTACHARYYA)
                    if diff > 0.4:
                        cuts += 1
                prev_hist = hist
            frame_idx += 1
        cap.release()
        return duration, max(cuts, 1)

    def _get_color_tone(self, video_path: str) -> str:
        """Ortalama renk tonunu analiz eder: warm | cool | neutral."""
        _load_cv2()
        cv2, np = _cv2, _np
        cap = cv2.VideoCapture(video_path)
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        step  = max(1, total // 10)
        warm_sum = cool_sum = 0

        for i in range(0, total, step):
            cap.set(cv2.CAP_PROP_POS_FRAMES, i)
            ret, frame = cap.read()
            if not ret:
                break
            b, g, r = cv2.split(frame)
            warm_sum += float(np.mean(r)) - float(np.mean(b))

        cap.release()
        avg = warm_sum / max(total // step, 1)
        if avg > 8:
            return "warm"
        elif avg < -8:
            return "cool"
        return "neutral"

    async def _estimate_bpm(self, video_path: str) -> float:
        """Video'dan ses çıkarıp BPM tahmini yapar."""
        tmp_audio = str(TEMP_DIR / "ref_audio.wav")
        try:
            result = await asyncio.to_thread(
                subprocess.run,
                ["ffmpeg", "-y", "-i", video_path, "-vn", "-ar", "22050",
                 "-ac", "1", tmp_audio],
                capture_output=True, timeout=60
            )
            if result.returncode != 0:
                return 120.0

            import librosa
            y, sr = await asyncio.to_thread(librosa.load, tmp_audio, sr=None)
            tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
            return float(tempo)
        except Exception as e:
            logger.warning(f"BPM tahmini başarısız: {e}")
            return 120.0
        finally:
            Path(tmp_audio).unlink(missing_ok=True)
