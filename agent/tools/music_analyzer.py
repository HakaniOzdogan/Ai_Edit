import asyncio
import librosa
import numpy as np
import logging

logger = logging.getLogger(__name__)


class MusicAnalyzer:

    async def analyze(self, file_path: str) -> dict:
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
        onset_times = librosa.frames_to_time(onset_frames, sr=sr).tolist()

        duration = librosa.get_duration(y=y, sr=sr)
        bpm = float(tempo)

        result = {
            "bpm": round(bpm, 1),
            "beat_times": [round(t, 3) for t in beat_times],
            "beat_count": len(beat_times),
            "drop_times": [round(t, 3) for t in drop_times[:15]],
            "onset_times": [round(t, 3) for t in onset_times[:30]],
            "duration": round(duration, 2),
            "beat_interval": round(60.0 / bpm, 3) if bpm > 0 else 0.0,
            "sample_rate": sr
        }
        logger.info(f"Müzik analizi tamamlandı: {bpm:.1f} BPM, {len(beat_times)} beat, {duration:.1f}sn")
        return result
