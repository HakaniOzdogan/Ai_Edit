import os
import logging
import math

logger = logging.getLogger(__name__)

STYLE_TRANSITIONS = {
    "dark": "hard_cut",
    "corp": "hard_cut",
    "warm": "dissolve",
    "fast": "wipeleft",
}

# Tarz → temel beat skip (enerji eğrisi bunu override eder)
STYLE_BEAT_SKIP = {
    "dark": 4,
    "warm": 3,
    "corp": 2,
    "fast": 1,
}

# Shot type döngüsü: izleyicinin gözü sıkılmasın
# Her stil için tercih edilen shot sıralaması
STYLE_SHOT_CYCLE = {
    "dark": ["action", "static", "medium", "action", "static"],
    "warm": ["static", "medium", "static", "action", "medium"],
    "corp": ["medium", "static", "medium", "action", "static"],
    "fast": ["action", "action", "medium", "action", "static"],
}


def _color_distance(profile_a: list, profile_b: list) -> float:
    """İki renk profili arasındaki mesafeyi döner. 0=aynı, 100=çok farklı."""
    if not profile_a or not profile_b:
        return 50.0
    h_diff = abs(profile_a[0] - profile_b[0])
    h_diff = min(h_diff, 180 - h_diff)  # Hue dairesel
    s_diff = abs(profile_a[1] - profile_b[1])
    v_diff = abs(profile_a[2] - profile_b[2])
    return round((h_diff * 0.5 + s_diff * 0.3 + v_diff * 0.2) / 1.8, 2)


def _build_rms_energy(beat_times: list, drop_times: list,
                       music_duration: float) -> list:
    """
    Her beat için 0-1 enerji değeri.
    - drop_times'a yakın → yüksek enerji (0.85-1.0)
    - Müzik ortasına doğru enerji artar (build-up)
    - Başı ve sonu daha yavaş (intro/outro)
    """
    if not beat_times:
        return []

    energies = []
    for i, bt in enumerate(beat_times):
        # Müzik boyunca temel enerji eğrisi (intro → climax → outro)
        progress = bt / max(music_duration, 1)
        # Gaus eğrisi: ortada tepe (0.25-0.75 arası yüksek)
        base_energy = math.exp(-8 * (progress - 0.5) ** 2) * 0.5 + 0.3

        # Drop/chorus yakınlığı
        drop_boost = 0.0
        for dt in drop_times:
            dist = abs(bt - dt)
            if dist < 4.0:
                drop_boost = max(drop_boost, (1 - dist / 4.0) * 0.5)

        energies.append(min(base_energy + drop_boost, 1.0))

    return energies


def build_timeline(beat_times: list, scored_clips: list,
                   music_duration: float, style: str = "dark",
                   drop_times: list = None) -> list:
    """
    Profesyonel kurgu kalitesi için:

    1. Gerçek enerji eğrisi — intro yavaş, climax hızlı, outro yavaş
    2. Shot type diversity — action/static/medium döngüsü
    3. Renk sürekliliği — jarring renk atlamaları minimize edilir
    4. best_offset — klibin en iyi bölümünden başla
    5. Minimum 0.8sn sahne süresi
    """
    if not scored_clips:
        logger.error("scored_clips boş")
        return []

    drop_times = drop_times or []
    base_skip  = STYLE_BEAT_SKIP.get(style, 2)
    transition = STYLE_TRANSITIONS.get(style, "hard_cut")

    # Enerji eğrisi
    energies = _build_rms_energy(beat_times, drop_times, music_duration)

    # Beat noktaları — enerji bazlı dinamik skip
    cut_beats = []
    i = 0
    while i < len(beat_times):
        bt = beat_times[i]
        if bt >= music_duration:
            break
        cut_beats.append((bt, energies[i] if i < len(energies) else 0.5))
        en = energies[i] if i < len(energies) else 0.5
        # Yüksek enerjide sık kesim, düşük enerjide seyrek
        if en > 0.75:
            skip = max(1, base_skip - 2)
        elif en > 0.5:
            skip = max(1, base_skip - 1)
        else:
            skip = base_skip
        i += skip

    if not cut_beats:
        return []

    # Klipler — skor, shot_type ve color_profile ile
    by_score = sorted(scored_clips, key=lambda c: -c.get("total_score", 0))

    # Shot type grupları
    shot_groups = {
        "action": [c for c in by_score if c.get("shot_type") == "action"],
        "medium": [c for c in by_score if c.get("shot_type") == "medium"],
        "static": [c for c in by_score if c.get("shot_type") == "static"],
    }
    # Boş grupları tüm kliplerle doldur
    for k in shot_groups:
        if not shot_groups[k]:
            shot_groups[k] = by_score.copy()

    # Açılış: en yüksek skorlu static (ürün/manzara iyi açılış yapar)
    # Kapanış: en yüksek skorlu action veya medium (güçlü bitiş)
    opening = (shot_groups["static"] or shot_groups["medium"] or by_score)[0]
    closing = (shot_groups["action"] or shot_groups["medium"] or by_score)[0]
    if closing == opening and len(by_score) > 1:
        closing = by_score[1]

    # Shot cycle (tarz bazlı)
    shot_cycle = STYLE_SHOT_CYCLE.get(style, ["medium", "action", "static", "medium", "action"])
    cycle_len  = len(shot_cycle)

    used_count     = {}
    timeline       = []
    prev_color     = None
    shot_cycle_idx = 0

    for idx, (beat_time, energy) in enumerate(cut_beats):
        if idx + 1 < len(cut_beats):
            next_bt, _ = cut_beats[idx + 1]
        else:
            next_bt = music_duration
        seg_dur = round(next_bt - beat_time, 3)

        if seg_dur < 0.8:
            continue

        is_first = (len(timeline) == 0)
        is_last  = (idx == len(cut_beats) - 1)

        if is_first:
            # Açılış: opening shot veya "opening" usage önerisindeki klip
            opening_candidates = [c for c in by_score if c.get("usage") == "opening"]
            clip = opening_candidates[0] if opening_candidates else opening
        elif is_last:
            # Kapanış: closing shot veya "closing" usage önerisindeki klip
            closing_candidates = [c for c in by_score if c.get("usage") == "closing"]
            clip = closing_candidates[0] if closing_candidates else closing
        else:
            # İstenen shot type
            wanted_type = shot_cycle[shot_cycle_idx % cycle_len]
            shot_cycle_idx += 1

            # "skip" önerisi olan klipleri çıkar
            valid_clips = [c for c in by_score if c.get("usage") != "skip"]
            if not valid_clips:
                valid_clips = by_score

            candidates = [c for c in valid_clips if c.get("shot_type") == wanted_type]
            if not candidates:
                candidates = valid_clips

            # Renk sürekliliği: önceki kliple renk mesafesini hesapla
            if prev_color:
                def _sort_key(c):
                    color_dist  = _color_distance(prev_color, c.get("color_profile", []))
                    color_score = 1.0 - min(color_dist / 50.0, 1.0)  # Yakın renk = iyi
                    repeat_pen  = used_count.get(c["path"], 0) * 0.3
                    quality     = c.get("total_score", 0)
                    # Kombine skor: kalite + renk uyumu - tekrar cezası
                    return -(quality * 0.5 + color_score * 0.4 - repeat_pen * 0.1)
                clip = sorted(candidates, key=_sort_key)[0]
            else:
                # İlk orta kare: en kaliteli
                clip = min(candidates, key=lambda c: (
                    used_count.get(c["path"], 0),
                    -c.get("total_score", 0)
                ))

        used_count[clip["path"]] = used_count.get(clip["path"], 0) + 1
        prev_color = clip.get("color_profile")

        # best_offset güvenlik kontrolü
        best_offset = float(clip.get("best_offset", 0.0))
        clip_dur    = float(clip.get("duration", 999))
        if best_offset + seg_dur > clip_dur:
            best_offset = max(0.0, clip_dur - seg_dur - 0.1)

        timeline.append({
            "clip_path":   clip["path"],
            "start_time":  round(beat_time, 3),
            "duration":    seg_dur,
            "clip_offset": round(best_offset, 3),
            "score":       clip.get("total_score", 0),
            "shot_type":   clip.get("shot_type", "medium"),
            "energy":      round(energy, 2),
            "transition":  transition,
        })

    # İstatistik
    types = [s["shot_type"] for s in timeline]
    type_dist = {t: types.count(t) for t in set(types)}
    logger.info(
        f"Timeline: {len(timeline)} sahne | {style} | "
        f"shot dağılımı: {type_dist} | "
        f"açılış={opening.get('shot_type','?')} kapanış={closing.get('shot_type','?')}"
    )
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
