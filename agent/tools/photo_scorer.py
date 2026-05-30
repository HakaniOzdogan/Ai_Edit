"""
Fotoğraf Kalite Skorlayıcı
Keskinlik (Laplacian), exposure ve boyut kriterleriyle skor üretir.
"""
import asyncio
import logging
from pathlib import Path

import cv2
import numpy as np

logger = logging.getLogger(__name__)


class PhotoScorer:

    async def score(self, photo_paths: list[str]) -> list[dict]:
        results = []
        for path in photo_paths:
            if not Path(path).exists():
                logger.warning(f"Fotoğraf bulunamadı: {path}")
                continue
            data = await asyncio.to_thread(self._score_photo, path)
            data["path"] = path
            results.append(data)

        results.sort(key=lambda x: x.get("total_score", 0), reverse=True)
        logger.info(f"{len(results)} fotoğraf puanlandı")
        return results

    def _score_photo(self, path: str) -> dict:
        img = cv2.imread(path)
        if img is None:
            return {"total_score": 0, "error": "Okunamadı"}

        h, w = img.shape[:2]
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Keskinlik (Laplacian varyansı)
        sharpness = float(cv2.Laplacian(gray, cv2.CV_64F).var())
        sharpness_score = min(sharpness / 800.0, 1.0)

        # Exposure (ortalama parlaklık — orta değer iyi)
        brightness = float(np.mean(gray)) / 255.0
        exposure_score = 1.0 - abs(brightness - 0.5) * 2

        # Boyut skoru (1920x1080 ve üzeri ideal)
        pixel_count = w * h
        size_score  = min(pixel_count / (1920 * 1080), 1.0)

        total = sharpness_score * 0.5 + exposure_score * 0.3 + size_score * 0.2

        return {
            "sharpness":      round(sharpness_score, 3),
            "exposure":       round(exposure_score, 3),
            "size_score":     round(size_score, 3),
            "total_score":    round(total, 3),
            "width":          w,
            "height":         h,
        }
