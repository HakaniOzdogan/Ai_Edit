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
        """
        Klipleri puan sırasıyla döner.
        Her klip için: total_score, best_offset, shot_type, color_profile
        """
        results = []
        for path in clip_paths:
            if not Path(path).exists():
                logger.warning(f"Dosya bulunamadı: {path}")
                continue
            logger.info(f"Klip analiz ediliyor: {path}")
            score_data = await asyncio.to_thread(self._score_clip_full, path)
            score_data["path"] = path
            results.append(score_data)

        results.sort(key=lambda x: x.get("total_score", 0), reverse=True)
        logger.info(f"{len(results)} klip puanlandı")
        return results

    def _score_clip_full(self, path: str) -> dict:
        """
        Tam analiz:
        - total_score, best_offset (klibin en iyi bölümü)
        - shot_type: "action" | "medium" | "static"
          action: yüksek hareket (spor, dans, aksiyon)
          medium: orta hareket (yürüyüş, ürün gösterimi)
          static: düşük hareket (portre, manzara, ürün close-up)
        - color_profile: [h_mean, s_mean, v_mean] — renk sürekliliği için
        """
        _load_libs()
        cv2, np = _cv2, _np
        cap = cv2.VideoCapture(path)
        if not cap.isOpened():
            return {"total_score": 0, "best_offset": 0.0,
                    "shot_type": "medium", "color_profile": [90, 80, 128], "error": "Açılamadı"}

        fps          = cap.get(cv2.CAP_PROP_FPS) or 25.0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration     = total_frames / fps

        # Kısa klip (5sn altı)
        if duration < 5.0 or total_frames < 30:
            cap.release()
            result = self._score_clip(path)
            result["best_offset"]   = 0.0
            result["duration"]      = round(duration, 2)
            result["shot_type"]     = "medium"
            result["color_profile"] = [90, 80, 128]
            return result

        sample_step  = max(1, total_frames // 60)
        frame_scores = []
        color_samples = []
        prev_gray    = None
        motion_vals  = []
        frame_idx    = 0

        while True:
            ret, frame = cap.read()
            if not ret:
                break
            if frame_idx % sample_step == 0:
                gray       = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                sharpness  = float(cv2.Laplacian(gray, cv2.CV_64F).var()) / 1000.0
                brightness = float(np.mean(gray)) / 255.0
                b_score    = 1.0 - abs(brightness - 0.5) * 2

                # Hareket skoru
                motion = 0.0
                if prev_gray is not None:
                    flow   = cv2.calcOpticalFlowFarneback(prev_gray, gray, None, 0.5, 3, 15, 3, 5, 1.2, 0)
                    mag    = float(np.mean(np.abs(flow)))
                    motion = min(mag * 10.0, 1.0)
                    motion_vals.append(mag)

                score = (min(sharpness, 1.0) * 0.5) + (b_score * 0.3) + (motion * 0.2)
                frame_scores.append((frame_idx, score))

                # Renk profili (HSV)
                hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
                color_samples.append([
                    float(np.mean(hsv[:,:,0])),  # hue
                    float(np.mean(hsv[:,:,1])),  # saturation
                    float(np.mean(hsv[:,:,2])),  # value
                ])

                prev_gray = gray
            frame_idx += 1

        cap.release()

        if not frame_scores:
            return {"total_score": 0, "best_offset": 0.0, "shot_type": "medium",
                    "color_profile": [90, 80, 128], "duration": round(duration, 2)}

        # En iyi pencere (kayan pencere)
        win_size   = max(1, int(3.0 * fps / sample_step))  # 3sn pencere
        scores_arr = np.array([s for _, s in frame_scores])

        if len(scores_arr) <= win_size:
            best_frame_idx = frame_scores[0][0]
        else:
            cumsum       = np.cumsum(scores_arr)
            cumsum       = np.insert(cumsum, 0, 0)
            win_sums     = cumsum[win_size:] - cumsum[:-win_size]
            best_win     = int(np.argmax(win_sums))
            best_frame_idx = frame_scores[best_win][0]

        best_offset = min(round(best_frame_idx / fps, 2), duration * 0.85)

        # Shot type: hareket yoğunluğuna göre
        avg_motion = float(np.mean(motion_vals)) if motion_vals else 0.0
        if avg_motion > 3.0:
            shot_type = "action"    # Yüksek hareket: dans, spor, aksiyon
        elif avg_motion > 0.8:
            shot_type = "medium"    # Orta hareket: yürüyüş, ürün gösterimi
        else:
            shot_type = "static"    # Düşük: portre, manzara, close-up

        # Ortalama renk profili
        color_profile = list(np.mean(color_samples, axis=0).round(1)) if color_samples else [90.0, 80.0, 128.0]

        return {
            "total_score":   round(float(np.mean(scores_arr)), 3),
            "best_offset":   best_offset,
            "duration":      round(duration, 2),
            "shot_type":     shot_type,
            "color_profile": color_profile,
            "avg_motion":    round(avg_motion, 3),
        }

    def _score_clip(self, path: str) -> dict:
        _load_libs()
        cv2, np = _cv2, _np
        cap = cv2.VideoCapture(path)
        if not cap.isOpened():
            return {"total_score": 0}
        brightness_list, sharpness_list, motion_list = [], [], []
        prev_gray    = None
        frame_count  = 0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        sample_step  = max(1, total_frames // 30)
        while True:
            ret, frame = cap.read()
            if not ret: break
            frame_count += 1
            if frame_count % sample_step != 0: continue
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            brightness_list.append(float(np.mean(gray)))
            sharpness_list.append(float(cv2.Laplacian(gray, cv2.CV_64F).var()))
            if prev_gray is not None:
                flow = cv2.calcOpticalFlowFarneback(prev_gray, gray, None, 0.5, 3, 15, 3, 5, 1.2, 0)
                motion_list.append(float(np.mean(np.abs(flow))))
            prev_gray = gray
        cap.release()
        if not brightness_list:
            return {"total_score": 0}
        brightness = np.mean(brightness_list) / 255.0
        sharpness  = min(np.mean(sharpness_list) / 1000.0, 1.0)
        motion     = min(np.mean(motion_list) * 10.0, 1.0) if motion_list else 0.0
        b_score    = 1.0 - abs(brightness - 0.5) * 2
        total      = (sharpness * 0.5) + (b_score * 0.3) + (motion * 0.2)
        return {"total_score": round(total, 3), "sharpness": round(sharpness, 3)}
