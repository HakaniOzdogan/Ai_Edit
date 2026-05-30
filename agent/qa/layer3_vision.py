"""
QA Katman 3 — Claude Vision Frame Analizi
Demo video'dan kareler çekilir, görsel kalite analiz edilir.
Süre: 30–90 saniye
"""
import asyncio
import base64
import json
import logging
import os
import subprocess
from pathlib import Path

import anthropic

logger = logging.getLogger(__name__)

VISION_PROMPT = """
Bu video kurgunun karelerini inceliyorsun.
Her kareyi profesyonel bir video editör gözüyle değerlendir.

Şu kriterleri 0–10 arasında puanla:
1. composition: Çerçeveleme ve kompozisyon kalitesi
2. lighting: Işık kalitesi ve exposure
3. color_grade: Renk gradyanı uyumu ve estetik
4. product_focus: Ürün/konu odak netliği
5. motion_blur: Hareket bulanıklığı (düşük puan = sorunlu)
6. professional: Genel profesyonellik izlenimi

SADECE JSON FORMAT'ta yanıt ver:
{
  "composition": <int>,
  "lighting": <int>,
  "color_grade": <int>,
  "product_focus": <int>,
  "motion_blur": <int>,
  "professional": <int>,
  "overall": <int 0-100>,
  "notes": "<kısa gözlem>"
}
"""


class VisionQA:

    def __init__(self):
        self.client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    async def run(self, video_path: str, timeline: list,
                  music_analysis: dict = None) -> dict:
        """
        Video'dan kilit kareler çeker, Claude Vision ile analiz eder.
        """
        if not Path(video_path).exists():
            return {"score": 50, "error": "Video dosyası yok"}

        timestamps = self._select_timestamps(timeline, music_analysis)
        frame_paths = await self._extract_frames(video_path, timestamps)

        if not frame_paths:
            return {"score": 50, "error": "Kare çıkarılamadı"}

        try:
            results  = await self._analyze_frames(frame_paths)
            score    = self._compute_score(results)
            return {"score": score, "frame_results": results,
                    "frames_analyzed": len(frame_paths)}
        finally:
            for p in frame_paths:
                Path(p).unlink(missing_ok=True)

    def _select_timestamps(self, timeline: list, music_analysis: dict) -> list[float]:
        """Analiz edilecek zaman damgalarını seç."""
        timestamps = [0.0]  # açılış

        # İlk 5 sahnenin başlangıçları
        for seg in timeline[:5]:
            t = seg.get("start_time", 0)
            if t > 0:
                timestamps.append(round(t, 2))

        # Drop noktası (en yüksek enerji)
        if music_analysis:
            drops = music_analysis.get("drop_times", [])
            if drops:
                timestamps.append(round(drops[0], 2))

        # Son sahne
        if timeline:
            last = timeline[-1]
            t = last.get("start_time", 0)
            if t not in timestamps:
                timestamps.append(round(t, 2))

        # Tekrarları kaldır, sırala, max 7 kare
        return sorted(list(set(timestamps)))[:7]

    async def _extract_frames(self, video_path: str,
                               timestamps: list[float]) -> list[str]:
        """FFmpeg ile belirtilen zamanlardaki kareleri JPG olarak çıkarır."""
        from agent.tools.ffmpeg_tool import FFPROBE_BIN
        temp_dir = Path(os.getenv("TEMP_DIR", "./temp")) / "qa_frames"
        temp_dir.mkdir(parents=True, exist_ok=True)

        extracted = []
        for i, ts in enumerate(timestamps):
            out = str(temp_dir / f"frame_{i:04d}.jpg")
            cmd = [
                "ffmpeg", "-y",
                "-ss", str(ts),
                "-i", video_path,
                "-frames:v", "1",
                "-q:v", "3",
                "-vf", "scale=960:540",
                out
            ]
            result = await asyncio.to_thread(
                subprocess.run, cmd, capture_output=True
            )
            if result.returncode == 0 and Path(out).exists():
                extracted.append(out)
            else:
                logger.warning(f"Kare çıkarılamadı @ {ts}s")

        return extracted

    async def _analyze_frames(self, frame_paths: list[str]) -> list[dict]:
        """Her kareyi Claude Vision ile analiz eder."""
        results = []
        for path in frame_paths:
            result = await self._analyze_single_frame(path)
            results.append(result)
        return results

    async def _analyze_single_frame(self, frame_path: str) -> dict:
        """Tek bir kareyi Claude Vision'a gönderir."""
        try:
            with open(frame_path, "rb") as f:
                img_data = base64.standard_b64encode(f.read()).decode("utf-8")

            response = await asyncio.to_thread(
                self.client.messages.create,
                model="claude-sonnet-4-6",
                max_tokens=512,
                messages=[{
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type":       "base64",
                                "media_type": "image/jpeg",
                                "data":       img_data,
                            }
                        },
                        {
                            "type": "text",
                            "text": VISION_PROMPT
                        }
                    ]
                }]
            )

            raw = response.content[0].text.strip()
            if "```" in raw:
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
                raw = raw.strip()

            result = json.loads(raw)
            result["frame"] = Path(frame_path).name
            return result

        except json.JSONDecodeError as e:
            logger.warning(f"Vision JSON parse hatası: {e}")
            return {"overall": 50, "frame": Path(frame_path).name,
                    "notes": f"Parse hatası: {e}"}
        except Exception as e:
            logger.warning(f"Vision analiz hatası: {e}")
            return {"overall": 50, "frame": Path(frame_path).name,
                    "notes": str(e)}

    def _compute_score(self, results: list[dict]) -> float:
        """Tüm kare sonuçlarını birleştirerek tek skor üretir."""
        if not results:
            return 50.0
        scores = [r.get("overall", 50) for r in results]
        return round(sum(scores) / len(scores), 1)
