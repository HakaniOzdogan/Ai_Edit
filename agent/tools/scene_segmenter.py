"""
Sahne Segmentleyici
OpenCV histogram farkı ile video içindeki sahne geçiş noktalarını bulur.
"""
import asyncio
import logging
from pathlib import Path

_cv2 = None
_np  = None

def _load_libs():
    global _cv2, _np
    if _cv2 is None:
        import cv2 as c; import numpy as n
        _cv2 = c; _np = n

logger = logging.getLogger(__name__)


class SceneSegmenter:

    async def segment(self, video_path: str, threshold: float = 30.0) -> list[dict]:
        """
        Video içindeki sahne sınırlarını tespit eder.
        threshold: histogram farkı eşiği (0-100). Düşük = daha hassas.
        """
        if not Path(video_path).exists():
            return []
        return await asyncio.to_thread(self._segment_sync, video_path, threshold)

    def _segment_sync(self, video_path: str, threshold: float) -> list[dict]:
        _load_libs()
        cv2 = _cv2
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return []

        fps         = cap.get(cv2.CAP_PROP_FPS) or 25.0
        total       = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        sample_step = max(1, int(fps / 2))  # 2 frame/sn örnekle

        scenes     = []
        prev_hist  = None
        scene_start = 0.0
        frame_idx   = 0

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            if frame_idx % sample_step == 0:
                ts   = frame_idx / fps
                hsv  = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
                hist = cv2.calcHist([hsv], [0, 1], None, [50, 60], [0, 180, 0, 256])
                cv2.normalize(hist, hist)

                if prev_hist is not None:
                    diff = cv2.compareHist(prev_hist, hist, cv2.HISTCMP_BHATTACHARYYA) * 100
                    if diff > threshold:
                        dur = ts - scene_start
                        if dur >= 0.5:  # 0.5sn'den kısa sahneleri atla
                            scenes.append({
                                "start":    round(scene_start, 3),
                                "end":      round(ts, 3),
                                "duration": round(dur, 3),
                            })
                        scene_start = ts

                prev_hist = hist
            frame_idx += 1

        # Son sahne
        total_dur = total / fps
        if total_dur - scene_start >= 0.5:
            scenes.append({
                "start":    round(scene_start, 3),
                "end":      round(total_dur, 3),
                "duration": round(total_dur - scene_start, 3),
            })

        cap.release()
        logger.info(f"{len(scenes)} sahne tespit edildi: {video_path}")
        return scenes

    async def best_segments(self, video_path: str, count: int = 5,
                             threshold: float = 30.0) -> list[dict]:
        """En uzun / en iyi sahneleri döner (count adet)."""
        scenes = await self.segment(video_path, threshold)
        scenes.sort(key=lambda s: s["duration"], reverse=True)
        return scenes[:count]
