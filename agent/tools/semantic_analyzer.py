"""
Semantik Video Analizi — Claude Vision ile.

Teknik metrikler (keskinlik, parlaklık) yerine içeriği anlayan analiz:
- Videoda ne var?
- Proje tipiyle ne kadar alakalı?
- Hangi duyguyu veriyor?
- Ürün/konu görünür mü?
- Hangi amaçla kullanılmalı? (açılış/aksiyon/detay/kapanış)
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
TEMP_DIR = Path(os.getenv("TEMP_DIR", "./temp")).resolve()

VISION_PROMPT = """Bu video karesini bir video editör uzmanı olarak analiz et.
Proje tipi: {project_type}
Tarz: {style}

Şunları JSON formatında döndür:
{{
  "content":      "Karede ne görüyorsun? (1 cümle, Türkçe)",
  "relevance":    0-10,  // Bu proje için ne kadar alakalı?
  "emotion":      "energetic|calm|dramatic|joyful|professional|romantic|neutral",
  "subject_visible": true/false,  // Ana konu/ürün net görünüyor mu?
  "usage":        "opening|action|detail|closing|skip",
  // opening: güçlü açılış sahnesi
  // action: yüksek enerji, hareketi anlık
  // detail: yakın plan ürün/detay
  // closing: güçlü kapanış
  // skip: bu sahneyi kullanma (kötü kalite, alakasız)
  "camera_type":  "drone|handheld|tripod|pan|zoom|static",
  "lighting":     "golden_hour|studio|harsh|indoor|soft"
}}

SADECE JSON döndür, başka metin ekleme."""


class SemanticAnalyzer:

    def __init__(self):
        api_key = os.getenv("ANTHROPIC_API_KEY")
        self.client = anthropic.Anthropic(api_key=api_key) if api_key else None
        self._cache: dict = {}  # clip_path → sonuç cache (oturum boyunca)

    async def analyze_clip(self, clip_path: str, project_type: str = "product",
                            style: str = "dark", sample_count: int = 1) -> dict:
        """
        Klibin kilit karelerini Claude Vision ile analiz eder.
        project_type: product | event | social | travel
        """
        # Cache kontrolü — aynı klip tekrar analiz edilmesin
        cache_key = f"{clip_path}:{project_type}:{style}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        if not self.client:
            return self._fallback(clip_path)

        if not Path(clip_path).exists():
            return self._fallback(clip_path)

        # Kareler çıkar (başlangıç, orta, en iyi bölüm)
        frame_paths = await self._extract_frames(clip_path, sample_count)
        if not frame_paths:
            return self._fallback(clip_path)

        results = []
        for fp in frame_paths:
            r = await self._analyze_frame(fp, project_type, style)
            if r:
                results.append(r)
            Path(fp).unlink(missing_ok=True)

        if not results:
            return self._fallback(clip_path)

        result = self._merge_results(results, clip_path)
        self._cache[cache_key] = result  # Cache'le
        return result

    async def analyze_clips_batch(self, scored_clips: list, project_type: str = "product",
                                   style: str = "dark") -> list:
        """
        Tüm klipleri semantik olarak analiz eder.
        scored_clips listesine semantic alanları ekler.
        """
        logger.info(f"{len(scored_clips)} klip semantik analiz ediliyor...")
        tasks = [
            self.analyze_clip(c["path"], project_type, style)
            for c in scored_clips
        ]
        # Paralel çalıştır (rate limit için küçük gecikme)
        semaphore = asyncio.Semaphore(3)  # Max 3 paralel istek

        async def _analyze_with_limit(clip, sem):
            async with sem:
                result = await self.analyze_clip(clip["path"], project_type, style)
                await asyncio.sleep(0.3)  # Rate limit koruması
                return {**clip, **result}

        enhanced = await asyncio.gather(*[
            _analyze_with_limit(c, semaphore) for c in scored_clips
        ])

        # Semantic skoru total_score'a entegre et
        for item in enhanced:
            semantic_bonus = item.get("relevance", 5) / 10.0 * 0.3
            item["total_score"] = round(
                item.get("total_score", 0.5) * 0.7 + semantic_bonus, 3
            )
            # "skip" önerisindeki klipleri düşük skora çek
            if item.get("usage") == "skip":
                item["total_score"] = min(item["total_score"], 0.2)

        # Tekrar sırala
        return sorted(enhanced, key=lambda x: -x.get("total_score", 0))

    async def _extract_frames(self, clip_path: str, count: int = 3) -> list[str]:
        """Klipten eşit aralıklı kareler çıkarır."""
        from agent.tools.ffmpeg_tool import FFPROBE_BIN, FFMPEG_BIN
        TEMP_DIR.mkdir(parents=True, exist_ok=True)

        # Süreyi al
        r = await asyncio.to_thread(
            subprocess.run,
            [FFPROBE_BIN, "-v", "quiet", "-show_entries", "format=duration",
             "-of", "csv=p=0", clip_path],
            capture_output=True, text=True
        )
        try:
            duration = float(r.stdout.strip())
        except ValueError:
            duration = 5.0

        # Eşit aralıklı zaman noktaları
        step  = duration / (count + 1)
        times = [round(step * (i + 1), 2) for i in range(count)]

        frames = []
        for i, ts in enumerate(times):
            out = str(TEMP_DIR / f"semantic_{id(clip_path)}_{i}.jpg")
            cmd = [FFMPEG_BIN, "-y", "-ss", str(ts), "-i", clip_path,
                   "-frames:v", "1", "-q:v", "3", "-vf", "scale=640:360", out]
            await asyncio.to_thread(subprocess.run, cmd, capture_output=True)
            if Path(out).exists():
                frames.append(out)
        return frames

    async def _analyze_frame(self, frame_path: str, project_type: str, style: str) -> dict | None:
        """Tek kareyi Claude Vision ile analiz eder."""
        try:
            with open(frame_path, "rb") as f:
                img_b64 = base64.standard_b64encode(f.read()).decode()

            prompt = VISION_PROMPT.format(project_type=project_type, style=style)
            # Haiku kullan: Vision için yeterli, 4x daha ucuz
            response = await asyncio.to_thread(
                self.client.messages.create,
                model="claude-haiku-4-5-20251001",
                max_tokens=300,
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "image", "source": {"type": "base64",
                                                      "media_type": "image/jpeg",
                                                      "data": img_b64}},
                        {"type": "text", "text": prompt}
                    ]
                }]
            )
            raw = response.content[0].text.strip()
            if "```" in raw:
                raw = raw.split("```")[1]
                if raw.startswith("json"): raw = raw[4:]
            return json.loads(raw.strip())
        except Exception as e:
            logger.warning(f"Vision analiz hatası: {e}")
            return None

    def _merge_results(self, results: list[dict], clip_path: str) -> dict:
        """Birden fazla kare sonucunu birleştirir."""
        if not results:
            return self._fallback(clip_path)

        # Relevance ortalaması
        relevance = sum(r.get("relevance", 5) for r in results) / len(results)

        # En sık kullanım önerisi
        usages = [r.get("usage", "action") for r in results]
        usage  = max(set(usages), key=usages.count)

        # Subject visibility: herhangi birinde görünüyorsa True
        subject_visible = any(r.get("subject_visible", False) for r in results)

        # İlk karenin içerik açıklaması
        content = results[0].get("content", "")

        # En sık emotion
        emotions = [r.get("emotion", "neutral") for r in results]
        emotion  = max(set(emotions), key=emotions.count)

        return {
            "content":         content,
            "relevance":       round(relevance, 1),
            "emotion":         emotion,
            "subject_visible": subject_visible,
            "usage":           usage,
            "camera_type":     results[0].get("camera_type", "static"),
            "lighting":        results[0].get("lighting", "indoor"),
            "semantic_ok":     True,
        }

    @staticmethod
    def _fallback(clip_path: str) -> dict:
        return {
            "content":         "Analiz yapılamadı",
            "relevance":       5.0,
            "emotion":         "neutral",
            "subject_visible": True,
            "usage":           "action",
            "camera_type":     "static",
            "lighting":        "indoor",
            "semantic_ok":     False,
        }
