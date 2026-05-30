"""
QA Katman 2 — Claude Metin Denetimi
Timeline özeti ve metrik raporu Claude'a gönderilir.
Süre: 10–30 saniye
"""
import asyncio
import json
import logging
import os

import anthropic

logger = logging.getLogger(__name__)

REVIEW_PROMPT = """
Sen bir video editör uzmanısın. Aşağıdaki timeline ve metrik raporunu incele,
videonun kalitesini değerlendir.

DEĞERLENDIRME KRİTERLERİ:
1. opening_strength (0-10): Açılış sahnesi ne kadar güçlü ve ilgi çekici?
2. closing_strength (0-10): Kapanış sahnesi ne kadar etkili?
3. rhythm_consistency (0-10): Kesimler müzikle ritimde mi, akış var mı?
4. style_adherence (0-10): Seçilen tarz (dark/warm/fast/corp) tutarlı mı?
5. overall_score (0-100): Genel değerlendirme skoru

Ayrıca:
- issues: Kritik sorunları listele (max 5 madde)
- auto_fixes: Otomatik düzeltilebilecek sorunları listele
- suggestions: İyileştirme önerileri (max 3 madde)

SADECE JSON FORMAT'ta yanıt ver, başka açıklama ekleme:
{
  "opening_strength": <int>,
  "closing_strength": <int>,
  "rhythm_consistency": <int>,
  "style_adherence": <int>,
  "overall_score": <int 0-100>,
  "issues": [<string>, ...],
  "auto_fixes": [<string>, ...],
  "suggestions": [<string>, ...]
}
"""


class ClaudeQA:

    def __init__(self):
        self.client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    async def run(self, timeline: list, metrics: dict,
                  style: str = "dark", music_bpm: float = 0) -> dict:
        """Claude'a timeline + metrik raporu gönderir, JSON değerlendirme alır."""

        prompt = self._build_prompt(timeline, metrics, style, music_bpm)

        try:
            response = await asyncio.to_thread(
                self.client.messages.create,
                model="claude-sonnet-4-6",
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}]
            )
            raw = response.content[0].text.strip()

            # JSON bloğunu temizle
            if "```" in raw:
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
                raw = raw.strip()

            result = json.loads(raw)
            result["score"] = float(result.get("overall_score", 50))
            return result

        except json.JSONDecodeError as e:
            logger.error(f"Claude JSON parse hatası: {e}")
            return self._fallback_result(50, f"JSON parse hatası: {e}")
        except Exception as e:
            logger.error(f"Claude QA hatası: {e}")
            return self._fallback_result(50, str(e))

    def _build_prompt(self, timeline: list, metrics: dict,
                      style: str, music_bpm: float) -> str:
        total_dur  = sum(seg.get("duration", 0) for seg in timeline)
        seg_count  = len(timeline)
        avg_dur    = round(total_dur / seg_count, 2) if seg_count else 0

        # İlk ve son 2 sahne
        opening = timeline[:2]  if len(timeline) >= 2 else timeline
        closing = timeline[-2:] if len(timeline) >= 2 else timeline

        return f"""
{REVIEW_PROMPT}

---
PROJE BİLGİSİ:
- Tarz: {style}
- Müzik BPM: {music_bpm}
- Toplam süre: {round(total_dur, 1)} saniye
- Sahne sayısı: {seg_count}
- Ortalama sahne süresi: {avg_dur} saniye

AÇILIŞ SAHNELERİ:
{json.dumps(opening, indent=2)}

KAPANIŞ SAHNELERİ:
{json.dumps(closing, indent=2)}

METRİK RAPORU:
- Beat Sync Skoru: {metrics.get('beat_sync', {}).get('score', 'N/A')}
- Siyah Kare: {metrics.get('black_frames', {}).get('black_events', 0)} olay
- Ses-Video Senkron: {metrics.get('av_sync', {}).get('diff_ms', 'N/A')} ms
- Süre Farkı: {metrics.get('duration', {}).get('diff_s', 'N/A')} saniye
- Klip Tekrar Oranı: {metrics.get('clip_repeat', {}).get('repeat_ratio', 'N/A')}
- Genel Metrik Skoru: {metrics.get('overall_score', 'N/A')}
"""

    @staticmethod
    def _fallback_result(score: float, error: str) -> dict:
        return {
            "score":             score,
            "overall_score":     score,
            "opening_strength":  5,
            "closing_strength":  5,
            "rhythm_consistency": 5,
            "style_adherence":   5,
            "issues":            [error],
            "auto_fixes":        [],
            "suggestions":       ["Kurguyu yeniden oluşturmayı dene"],
        }
