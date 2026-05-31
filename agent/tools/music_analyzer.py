import asyncio
import logging
import subprocess
import os
from pathlib import Path

# Ağır kütüphaneler lazy — ilk kullanımda yüklenir, agent başlatmayı yavaşlatmaz
_librosa = None
_np = None

def _load_libs():
    global _librosa, _np
    if _librosa is None:
        import librosa as _lib
        import numpy as np_lib
        _librosa = _lib
        _np = np_lib

logger = logging.getLogger(__name__)

TEMP_DIR = Path(os.getenv("TEMP_DIR", "./temp")).resolve()


class MusicAnalyzer:

    async def analyze(self, file_path: str) -> dict:
        _load_libs()  # ilk çağrıda librosa + numpy yüklenir
        librosa, np = _librosa, _np
        logger.info(f"Müzik analizi başladı: {file_path}")
        try:
            y, sr = await asyncio.to_thread(librosa.load, file_path, sr=None)
        except Exception as e:
            logger.error(f"Müzik yükleme hatası: {e}")
            return {"error": str(e)}

        tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
        beat_times = librosa.frames_to_time(beat_frames, sr=sr).tolist()

        rms = librosa.feature.rms(y=y)[0]
        rms_times = librosa.frames_to_time(range(len(rms)), sr=sr)
        threshold = np.percentile(rms, 80)
        drop_times = rms_times[rms > threshold].tolist()

        onset_frames = librosa.onset.onset_detect(y=y, sr=sr)
        onset_times  = librosa.frames_to_time(onset_frames, sr=sr).tolist()

        duration = librosa.get_duration(y=y, sr=sr)
        bpm      = float(tempo)

        # En iyi bölümü bul (en yüksek enerjili sürekli kesit)
        best_start = self._find_best_section(rms, rms_times, window_sec=30)

        result = {
            "bpm":          round(bpm, 1),
            "beat_times":   [round(t, 3) for t in beat_times],
            "beat_count":   len(beat_times),
            "drop_times":   [round(t, 3) for t in drop_times[:15]],
            "onset_times":  [round(t, 3) for t in onset_times[:30]],
            "duration":     round(duration, 2),
            "beat_interval": round(60.0 / bpm, 3) if bpm > 0 else 0.0,
            "sample_rate":  sr,
            "best_section_start": round(best_start, 2),
        }
        logger.info(
            f"Müzik analizi tamamlandı: {bpm:.1f} BPM, {len(beat_times)} beat, "
            f"{duration:.1f}sn, en iyi bölüm: {best_start:.1f}sn"
        )
        return result

    def _find_best_section(self, rms, rms_times,
                            window_sec: float = 30.0) -> float:
        """
        RMS enerji üzerinde kayan pencere ile en yüksek enerjili bölümün
        başlangıç zamanını döner. Chorus/drop tespiti için kullanılır.
        """
        if len(rms_times) < 2:
            return 0.0
        hop = float(rms_times[1] - rms_times[0]) if len(rms_times) > 1 else 0.02
        window_frames = max(1, int(window_sec / hop))

        if len(rms) <= window_frames:
            return 0.0

        # Kayan pencere RMS toplamı
        _load_libs()
        np = _np
        cumsum = np.cumsum(rms)
        cumsum = np.insert(cumsum, 0, 0)
        window_energy = cumsum[window_frames:] - cumsum[:-window_frames]
        best_idx = int(np.argmax(window_energy))
        return float(rms_times[best_idx]) if best_idx < len(rms_times) else 0.0

    async def extract_section(self, file_path: str, start: float,
                               duration: float, output_path: str = None) -> dict:
        """
        Müziğin belirli bir bölümünü keser ve yeni dosya üretir.
        Hedef video süresiyle eşleşen müzik kesiti için kullanılır.
        """
        from agent.tools.ffmpeg_tool import FFMPEG_BIN
        if not output_path:
            TEMP_DIR.mkdir(parents=True, exist_ok=True)
            import uuid
            output_path = str(TEMP_DIR / f"music_section_{uuid.uuid4().hex[:8]}.mp3")

        cmd = [
            FFMPEG_BIN, "-y",
            "-i", file_path,
            "-ss", str(round(start, 3)),
            "-t",  str(round(duration, 3)),
            "-c:a", "libmp3lame", "-q:a", "2",
            output_path
        ]
        result = await asyncio.to_thread(
            subprocess.run, cmd, capture_output=True
        )
        success = result.returncode == 0 and Path(output_path).exists()
        return {
            "success":     success,
            "output_path": output_path if success else None,
            "start":       start,
            "duration":    duration,
        }
