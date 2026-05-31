"""
QA Katman 1 — Metrik Kontrol
Kod tabanlı, FFmpeg + OpenCV + Librosa ile çalışır.
Süre: < 10 saniye
"""
import asyncio
import logging
import subprocess
import json
from pathlib import Path

_cv2 = None
_np  = None

def _load_libs():
    global _cv2, _np
    if _cv2 is None:
        import cv2 as c; import numpy as n
        _cv2 = c; _np = n

logger = logging.getLogger(__name__)

# Ağırlıklar (toplam = 1.0)
WEIGHTS = {
    "beat_sync":         0.35,
    "black_frames":      0.20,
    "av_sync":           0.20,
    "duration":          0.15,
    "clip_repeat":       0.05,
    "color_consistency": 0.05,
}


class MetricQA:

    async def run(self, video_path: str, music_path: str,
                  timeline: list) -> dict:
        """
        Tüm metrik kontrollerini çalıştırır.
        Her kontrol 0–100 arası skor döner.
        """
        results = {}

        checks = [
            ("beat_sync",         self._check_beat_sync(timeline, music_path)),
            ("black_frames",      self._check_black_frames(video_path)),
            ("av_sync",           self._check_av_sync(video_path)),
            ("duration",          self._check_duration(video_path, music_path)),
            ("clip_repeat",       self._check_clip_repeat(timeline)),
            ("color_consistency", self._check_color_consistency(video_path)),
        ]

        for name, coro in checks:
            try:
                results[name] = await coro
            except Exception as e:
                logger.warning(f"Metrik [{name}] başarısız: {e}")
                results[name] = {"score": 50, "error": str(e)}

        overall = sum(
            results[k]["score"] * WEIGHTS[k]
            for k in WEIGHTS if k in results
        )
        results["overall_score"] = round(overall, 1)
        return results

    # ── Beat Sync ─────────────────────────────────────────────────────────────

    async def _check_beat_sync(self, timeline: list, music_path: str) -> dict:
        """
        Timeline kesim noktalarını müzik beat zamanlarıyla karşılaştırır.
        Tolerans: ±100ms
        """
        if not timeline or not music_path or not Path(music_path).exists():
            return {"score": 50, "note": "Müzik veya timeline yok"}

        try:
            import librosa
            y, sr = await asyncio.to_thread(librosa.load, music_path, sr=None)
            _, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
            beat_times = set(round(t, 2) for t in
                             librosa.frames_to_time(beat_frames, sr=sr).tolist())
        except Exception as e:
            return {"score": 50, "note": f"Librosa hatası: {e}"}

        tolerance = 0.1  # 100ms
        synced = 0
        for seg in timeline:
            cut = seg.get("start_time", 0)
            if any(abs(cut - b) <= tolerance for b in beat_times):
                synced += 1

        total = len(timeline) or 1
        ratio = synced / total
        score = round(ratio * 100, 1)
        return {"score": score, "synced": synced, "total": total, "ratio": round(ratio, 3)}

    # ── Siyah Kare ───────────────────────────────────────────────────────────

    async def _check_black_frames(self, video_path: str) -> dict:
        """FFmpeg blackdetect filtresi ile siyah kareleri tespit eder."""
        if not Path(video_path).exists():
            return {"score": 50, "note": "Video yok", "black_events": 0}

        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-vf", "blackdetect=d=0.05:pix_th=0.1",
            "-an", "-f", "null", "-"
        ]
        result = await asyncio.to_thread(
            subprocess.run, cmd, capture_output=True, text=True
        )

        if result.returncode != 0 and "black_start" not in result.stderr:
            return {"score": 50, "note": f"FFmpeg hata kodu {result.returncode}",
                    "black_events": 0}

        black_events = result.stderr.count("black_start")

        if black_events == 0:
            score = 100.0
        elif black_events <= 2:
            score = 70.0
        else:
            score = max(0.0, 100.0 - black_events * 15)

        return {"score": score, "black_events": black_events}

    # ── Ses-Video Senkron ────────────────────────────────────────────────────

    async def _check_av_sync(self, video_path: str) -> dict:
        """
        ffprobe ile video ve ses stream zaman damgalarını karşılaştırır.
        """
        if not Path(video_path).exists():
            return {"score": 100, "note": "Video yok"}

        cmd = [
            "ffprobe", "-v", "quiet",
            "-print_format", "json",
            "-show_streams", video_path
        ]
        result = await asyncio.to_thread(
            subprocess.run, cmd, capture_output=True, text=True
        )
        try:
            data = json.loads(result.stdout)
        except Exception:
            return {"score": 75, "note": "ffprobe parse hatası"}

        streams  = data.get("streams", [])
        v_starts = [float(s.get("start_time", 0)) for s in streams if s.get("codec_type") == "video"]
        a_starts = [float(s.get("start_time", 0)) for s in streams if s.get("codec_type") == "audio"]

        if not v_starts or not a_starts:
            return {"score": 75, "note": "Ses veya video stream yok"}

        diff_ms = abs(v_starts[0] - a_starts[0]) * 1000

        if diff_ms < 20:
            score = 100.0
        elif diff_ms < 50:
            score = 85.0
        elif diff_ms < 100:
            score = 60.0
        else:
            score = max(0.0, 100.0 - diff_ms)

        return {"score": score, "diff_ms": round(diff_ms, 1)}

    # ── Süre Kontrolü ────────────────────────────────────────────────────────

    async def _check_duration(self, video_path: str, music_path: str) -> dict:
        """Video ve müzik sürelerini karşılaştırır (±2sn tolerans)."""
        if not Path(video_path).exists():
            return {"score": 50, "note": "Video yok"}

        def _get_dur(path):
            r = subprocess.run(
                ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
                 "-of", "csv=p=0", path],
                capture_output=True, text=True
            )
            try:
                return float(r.stdout.strip())
            except ValueError:
                return 0.0

        video_dur = await asyncio.to_thread(_get_dur, video_path)
        music_dur = await asyncio.to_thread(_get_dur, music_path) if (music_path and Path(music_path).exists()) else video_dur

        diff = abs(video_dur - music_dur)
        if diff <= 2:
            score = 100.0
        elif diff <= 5:
            score = 75.0
        elif diff <= 10:
            score = 50.0
        else:
            score = 25.0

        return {
            "score":     score,
            "video_dur": round(video_dur, 1),
            "music_dur": round(music_dur, 1),
            "diff_s":    round(diff, 1),
        }

    # ── Klip Tekrarı ─────────────────────────────────────────────────────────

    async def _check_clip_repeat(self, timeline: list) -> dict:
        """Aynı klibin kaç kez tekrar ettiğini ölçer. Max %30 tolerans."""
        if not timeline:
            return {"score": 100, "note": "Timeline boş"}

        from collections import Counter
        paths   = [seg.get("clip_path", "") for seg in timeline]
        counter = Counter(paths)
        total   = len(paths)
        max_rep = counter.most_common(1)[0][1] if counter else 0

        repeat_ratio = max_rep / total if total else 0

        if repeat_ratio <= 0.30:
            score = 100.0
        elif repeat_ratio <= 0.50:
            score = 70.0
        elif repeat_ratio <= 0.70:
            score = 40.0
        else:
            score = 10.0

        return {
            "score":        score,
            "repeat_ratio": round(repeat_ratio, 2),
            "max_repeats":  max_rep,
            "total_segs":   total,
        }

    # ── Renk Tutarlılığı ─────────────────────────────────────────────────────

    async def _check_color_consistency(self, video_path: str) -> dict:
        """
        OpenCV ile sahneler arası renk uyumunu ölçer.
        Histogram farkı < %40 → kabul edilebilir.
        """
        if not Path(video_path).exists():
            return {"score": 75, "note": "Video yok"}

        def _analyze():
            _load_libs()
            cv2, np = _cv2, _np
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                return {"score": 75, "note": "Video açılamadı"}

            total  = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            step   = max(1, total // 10)
            hists  = []

            for i in range(0, total, step):
                cap.set(cv2.CAP_PROP_POS_FRAMES, i)
                ret, frame = cap.read()
                if not ret:
                    break
                hsv  = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
                hist = cv2.calcHist([hsv], [0], None, [50], [0, 180])
                cv2.normalize(hist, hist)
                hists.append(hist)

            cap.release()

            if len(hists) < 2:
                return {"score": 75, "note": "Yeterli kare yok"}

            diffs = []
            for i in range(len(hists) - 1):
                d = cv2.compareHist(hists[i], hists[i+1], cv2.HISTCMP_BHATTACHARYYA)
                diffs.append(d)

            avg_diff = float(np.mean(diffs))
            if avg_diff < 0.2:
                score = 100.0
            elif avg_diff < 0.4:
                score = 75.0
            elif avg_diff < 0.6:
                score = 50.0
            else:
                score = 25.0

            return {"score": score, "avg_diff": round(avg_diff, 3)}

        return await asyncio.to_thread(_analyze)
