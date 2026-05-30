"""
QA Orkestratör — 3 Katmanı Birleştirir
Katman 1 (Metrik) × 0.35 + Katman 2 (Claude) × 0.35 + Katman 3 (Vision) × 0.30
"""
import asyncio
import logging

from agent.qa.layer1_metrics import MetricQA
from agent.qa.layer2_claude  import ClaudeQA
from agent.qa.layer3_vision  import VisionQA

logger = logging.getLogger(__name__)

GRADE_MAP = [
    (90, "A", "Profesyonel Kalite"),
    (75, "B", "İyi Kalite"),
    (60, "C", "Kabul Edilebilir"),
    (45, "D", "Revizyon Gerekli"),
    (0,  "F", "Yeniden Oluştur"),
]

# Katman ağırlıkları
W1, W2, W3 = 0.35, 0.35, 0.30


class QAOrchestrator:

    def __init__(self):
        self.layer1 = MetricQA()
        self.layer2 = ClaudeQA()
        self.layer3 = VisionQA()

    async def run(self, video_path: str, music_path: str,
                  timeline: list, style: str = "dark",
                  music_analysis: dict = None) -> dict:
        """
        3 katmanı sırayla çalıştırır ve birleşik rapor üretir.
        Kritik sorunlar varsa otomatik düzeltme önerileri sunar.
        """
        logger.info("QA başladı — Katman 1 (Metrik)")
        l1 = await self.layer1.run(video_path, music_path, timeline)

        logger.info("QA — Katman 2 (Claude Denetimi)")
        bpm = (music_analysis or {}).get("bpm", 0)
        l2 = await self.layer2.run(timeline, l1, style, bpm)

        logger.info("QA — Katman 3 (Vision Analizi)")
        l3 = await self.layer3.run(video_path, timeline, music_analysis)

        # Birleşik skor
        s1 = float(l1.get("overall_score", 50))
        s2 = float(l2.get("score",         50))
        s3 = float(l3.get("score",         50))

        final = round(s1 * W1 + s2 * W2 + s3 * W3, 1)
        grade, label = self._grade(final)

        # Otomatik düzeltilebilen sorunlar
        auto_fixes = self._collect_auto_fixes(l1, l2)

        report = {
            "final_score":   final,
            "grade":         grade,
            "grade_label":   label,
            "layer1":        {"score": s1, "details": l1},
            "layer2":        {"score": s2, "details": l2},
            "layer3":        {"score": s3, "details": l3},
            "issues":        l2.get("issues", []),
            "auto_fixes":    auto_fixes,
            "suggestions":   l2.get("suggestions", []),
            "pass":          final >= 60,
        }

        logger.info(f"QA tamamlandı: {final:.1f} — {grade} ({label})")
        return report

    # ── Otomatik Düzeltmeler ─────────────────────────────────────────────────

    def _collect_auto_fixes(self, l1: dict, l2: dict) -> list[str]:
        fixes = []

        # Siyah kare
        bf = l1.get("black_frames", {})
        if bf.get("black_events", 0) > 0:
            fixes.append("Siyah kareler komşu kareden dolgu ile kapatılacak")

        # Ses-video sync
        av = l1.get("av_sync", {})
        if av.get("diff_ms", 0) > 50:
            fixes.append(f"Ses-video sync düzeltilecek ({av['diff_ms']}ms)")

        # Süre uyumsuzluğu
        dur = l1.get("duration", {})
        if dur.get("diff_s", 0) > 2:
            fixes.append(f"Son sahne müzik süresine snap edilecek ({dur['diff_s']}s fark)")

        # Claude önerisi
        for fix in l2.get("auto_fixes", []):
            if fix not in fixes:
                fixes.append(fix)

        return fixes

    # ── Not Hesaplama ────────────────────────────────────────────────────────

    @staticmethod
    def _grade(score: float) -> tuple[str, str]:
        for threshold, grade, label in GRADE_MAP:
            if score >= threshold:
                return grade, label
        return "F", "Yeniden Oluştur"

    # ── Hızlı Metrik Raporu (Claude olmadan) ─────────────────────────────────

    async def quick_check(self, video_path: str, music_path: str,
                          timeline: list) -> dict:
        """
        Sadece Katman 1 çalıştırır — hızlı kontrol için.
        Süre: < 10 saniye
        """
        l1    = await self.layer1.run(video_path, music_path, timeline)
        score = float(l1.get("overall_score", 50))
        grade, label = self._grade(score)
        return {
            "score":       score,
            "grade":       grade,
            "grade_label": label,
            "details":     l1,
            "pass":        score >= 60,
        }
