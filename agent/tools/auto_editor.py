import os
import logging

logger = logging.getLogger(__name__)


def build_timeline(beat_times: list, scored_clips: list,
                   music_duration: float, style: str = "dark") -> list:
    beat_skip = {"dark": 4, "fast": 1, "warm": 3, "corp": 2}.get(style, 2)
    cut_beats = [beat_times[i] for i in range(0, len(beat_times), beat_skip)]

    if not scored_clips:
        logger.error("scored_clips boş — klip listesi sağlanmalı")
        return []

    timeline = []
    clip_pool = scored_clips.copy()
    clip_index = 0

    for i, beat_time in enumerate(cut_beats):
        if beat_time >= music_duration:
            break

        next_beat = cut_beats[i + 1] if i + 1 < len(cut_beats) else music_duration
        segment_duration = round(next_beat - beat_time, 3)

        if segment_duration < 0.3:
            continue

        clip = clip_pool[clip_index % len(clip_pool)]
        clip_index += 1

        timeline.append({
            "clip_path":   clip["path"],
            "start_time":  round(beat_time, 3),
            "duration":    segment_duration,
            "clip_offset": 0.0,
            "score":       clip.get("total_score", 0)
        })

    logger.info(f"Timeline oluşturuldu: {len(timeline)} sahne, {style} tarzı")
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
