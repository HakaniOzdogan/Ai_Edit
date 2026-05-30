import os
import logging

logger = logging.getLogger(__name__)

# Tarz bazlı geçiş tercihleri
STYLE_TRANSITIONS = {
    "dark": "hard_cut",
    "corp": "hard_cut",
    "warm": "dissolve",
    "fast": "whip_pan",
}

# Klip offset stratejisi: klip içindeki en iyi başlangıç yüzdesi
STYLE_OFFSET_PCT = {
    "dark": 0.15,   # klibin %15'inden başla
    "fast": 0.0,    # en başından
    "warm": 0.10,
    "corp": 0.05,
}


def build_timeline(beat_times: list, scored_clips: list,
                   music_duration: float, style: str = "dark") -> list:
    beat_skip  = {"dark": 4, "fast": 1, "warm": 3, "corp": 2}.get(style, 2)
    cut_beats  = [beat_times[i] for i in range(0, len(beat_times), beat_skip)]
    transition = STYLE_TRANSITIONS.get(style, "hard_cut")
    offset_pct = STYLE_OFFSET_PCT.get(style, 0.0)

    if not scored_clips:
        logger.error("scored_clips boş — klip listesi sağlanmalı")
        return []

    timeline   = []
    clip_pool  = scored_clips.copy()
    used_count = {}  # klip başına kullanım sayısı — tekrar önleme

    for i, beat_time in enumerate(cut_beats):
        if beat_time >= music_duration:
            break

        next_beat        = cut_beats[i + 1] if i + 1 < len(cut_beats) else music_duration
        segment_duration = round(next_beat - beat_time, 3)

        if segment_duration < 0.3:
            continue

        # En az tekrarlanan, en yüksek skorlu klibi seç
        clip_pool_sorted = sorted(
            clip_pool,
            key=lambda c: (used_count.get(c["path"], 0), -c.get("total_score", 0))
        )
        clip = clip_pool_sorted[0]
        used_count[clip["path"]] = used_count.get(clip["path"], 0) + 1

        # Dinamik clip_offset: klibin toplam süresini bilmiyoruz,
        # ama relative pct ile makul bir başlangıç hesaplayabiliriz
        clip_offset = round(segment_duration * offset_pct, 3)

        timeline.append({
            "clip_path":  clip["path"],
            "start_time": round(beat_time, 3),
            "duration":   segment_duration,
            "clip_offset": clip_offset,
            "score":      clip.get("total_score", 0),
            "transition": transition,
        })

    repeat_max = max(used_count.values(), default=0)
    if repeat_max > 3:
        logger.warning(
            f"Klip tekrarı yüksek: en fazla kullanılan klip {repeat_max}x "
            f"— daha fazla klip eklenirse kalite artar"
        )
    logger.info(f"Timeline oluşturuldu: {len(timeline)} sahne, {style} tarzı, geçiş: {transition}")
    return timeline


def write_concat_list(timeline: list, temp_dir: str) -> tuple[str, list]:
    temp_clips = []
    list_lines = []

    for i, seg in enumerate(timeline):
        temp_path = os.path.join(temp_dir, f"seg_{i:04d}.mp4")
        temp_clips.append(temp_path)
        list_lines.append(f"file '{temp_path}'")

    list_path = os.path.join(temp_dir, "concat_list.txt")
    with open(list_path, "w") as f:
        f.write("\n".join(list_lines))

    return list_path, temp_clips
