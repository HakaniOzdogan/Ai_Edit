import asyncio
import logging
from pathlib import Path

_cv2 = None
_np  = None

def _load_libs():
    global _cv2, _np
    if _cv2 is None:
        import cv2 as cv2_lib
        import numpy as np_lib
        _cv2 = cv2_lib
        _np  = np_lib

logger = logging.getLogger(__name__)


class ClipScorer:

    async def score(self, clip_paths: list) -> list:
        results = []
        for path in clip_paths:
            if not Path(path).exists():
                logger.warning(f"Dosya bulunamadı: {path}")
                continue
            logger.info(f"Klip analiz ediliyor: {path}")
            score_data = await asyncio.to_thread(self._score_clip, path)
            score_data["path"] = path
            results.append(score_data)

        results.sort(key=lambda x: x.get("total_score", 0), reverse=True)
        logger.info(f"{len(results)} klip puanlandı")
        return results

    def _score_clip(self, path: str) -> dict:
        _load_libs()
        cv2, np = _cv2, _np
        cap = cv2.VideoCapture(path)
        if not cap.isOpened():
            return {"total_score": 0, "error": "Dosya açılamadı"}

        brightness_list, sharpness_list, motion_list = [], [], []
        prev_gray = None
        frame_count = 0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        sample_step = max(1, total_frames // 30)

        while True:
            ret, frame = cap.read()
            if not ret:
                break
            frame_count += 1
            if frame_count % sample_step != 0:
                continue

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            brightness_list.append(float(np.mean(gray)))
            sharpness_list.append(float(cv2.Laplacian(gray, cv2.CV_64F).var()))

            if prev_gray is not None:
                flow = cv2.calcOpticalFlowFarneback(
                    prev_gray, gray, None, 0.5, 3, 15, 3, 5, 1.2, 0
                )
                motion_list.append(float(np.mean(np.abs(flow))))
            prev_gray = gray

        cap.release()

        if not brightness_list:
            return {"total_score": 0, "error": "Kare okunamadı"}

        brightness = np.mean(brightness_list) / 255.0
        sharpness  = min(np.mean(sharpness_list) / 1000.0, 1.0)
        motion     = min(np.mean(motion_list) * 10.0, 1.0) if motion_list else 0.0
        brightness_score = 1.0 - abs(brightness - 0.5) * 2

        total = (sharpness * 0.5) + (brightness_score * 0.3) + (motion * 0.2)

        return {
            "brightness":  round(brightness, 3),
            "sharpness":   round(sharpness, 3),
            "motion":      round(motion, 3),
            "total_score": round(total, 3)
        }
