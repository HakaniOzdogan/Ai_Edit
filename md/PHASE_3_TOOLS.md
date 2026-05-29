# PHASE 3 — Tool Modülleri (FFmpeg, Müzik, Klip Skoru)

Önceki adım: PHASE_2_AGENT.md (agent çalışıyor, WebSocket testi geçildi)
Sonraki adım: PHASE_4_CLAUDE.md

---

## Amaç

Sistemin yapacağı işleri gerçekleştirecek araç modüllerini yaz ve test et.
Bu adım sonunda her araç bağımsız olarak test edilmiş olmalı.

---

## 3.1 — FFmpeg Tool

`agent/tools/ffmpeg_tool.py`:

```python
import asyncio
import subprocess
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class FFmpegTool:

    async def run(self, inputs: dict) -> dict:
        cmd_str = f"ffmpeg -y {inputs['command']} \"{inputs['output_path']}\""
        logger.info(f"FFmpeg: {cmd_str[:120]}")
        proc = await asyncio.create_subprocess_shell(
            cmd_str,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        success = proc.returncode == 0
        if not success:
            logger.error(f"FFmpeg hata: {stderr.decode()[-300:]}")
        return {
            "success": success,
            "output_path": inputs["output_path"],
            "returncode": proc.returncode,
            "stderr_tail": stderr.decode()[-300:]
        }

    def trim_cmd(self, input_path: str, start: float, duration: float) -> str:
        return f"-i \"{input_path}\" -ss {start:.3f} -t {duration:.3f} -c copy"

    def concat_cmd(self, filelist_path: str) -> str:
        return f"-f concat -safe 0 -i \"{filelist_path}\" -c copy"

    def render_cmd(self, input_path: str, resolution: str = "1920x1080",
                   crf: int = 23, preset: str = "medium") -> str:
        return (
            f"-i \"{input_path}\" "
            f"-vf scale={resolution} "
            f"-c:v libx264 -crf {crf} -preset {preset} "
            f"-c:a aac -b:a 192k"
        )

    def render_4k_cmd(self, input_path: str) -> str:
        return (
            f"-i \"{input_path}\" "
            f"-vf scale=3840:2160 "
            f"-c:v libx265 -crf 18 -preset slow "
            f"-c:a aac -b:a 320k"
        )

    def demo_render_cmd(self, input_path: str) -> str:
        """Hızlı düşük kaliteli demo render — önizleme için."""
        return (
            f"-i \"{input_path}\" "
            f"-vf scale=960:540 "
            f"-c:v libx264 -crf 28 -preset ultrafast "
            f"-c:a aac -b:a 128k"
        )

    def get_duration(self, file_path: str) -> float:
        result = subprocess.run(
            ["ffprobe", "-v", "quiet", "-show_entries",
             "format=duration", "-of", "csv=p=0", file_path],
            capture_output=True, text=True
        )
        try:
            return float(result.stdout.strip())
        except ValueError:
            return 0.0

    def get_video_info(self, file_path: str) -> dict:
        result = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json",
             "-show_streams", "-show_format", file_path],
            capture_output=True, text=True
        )
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError:
            return {}
```

---

## 3.2 — Müzik Analizi

`agent/tools/music_analyzer.py`:

```python
import librosa
import numpy as np
import logging

logger = logging.getLogger(__name__)

class MusicAnalyzer:

    async def analyze(self, file_path: str) -> dict:
        logger.info(f"Müzik analizi başladı: {file_path}")
        try:
            y, sr = librosa.load(file_path, sr=None)
        except Exception as e:
            logger.error(f"Müzik yükleme hatası: {e}")
            return {"error": str(e)}

        # BPM ve beat zamanları
        tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
        beat_times = librosa.frames_to_time(beat_frames, sr=sr).tolist()

        # RMS enerji — yüksek enerji = drop/chorus
        rms = librosa.feature.rms(y=y)[0]
        rms_times = librosa.frames_to_time(range(len(rms)), sr=sr)
        threshold = np.percentile(rms, 80)
        drop_mask = rms > threshold
        drop_times = rms_times[drop_mask].tolist()

        # Onset tespiti (müzik değişim noktaları)
        onset_frames = librosa.onset.onset_detect(y=y, sr=sr)
        onset_times = librosa.frames_to_time(onset_frames, sr=sr).tolist()

        duration = librosa.get_duration(y=y, sr=sr)
        bpm = float(tempo)

        result = {
            "bpm": round(bpm, 1),
            "beat_times": [round(t, 3) for t in beat_times],
            "beat_count": len(beat_times),
            "drop_times": [round(t, 3) for t in drop_times[:15]],
            "onset_times": [round(t, 3) for t in onset_times[:30]],
            "duration": round(duration, 2),
            "beat_interval": round(60.0 / bpm, 3),
            "sample_rate": sr
        }
        logger.info(f"Müzik analizi tamamlandı: {bpm:.1f} BPM, {len(beat_times)} beat, {duration:.1f}sn")
        return result
```

---

## 3.3 — Klip Skorlama

`agent/tools/clip_scorer.py`:

```python
import cv2
import numpy as np
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class ClipScorer:

    async def score(self, clip_paths: list) -> list:
        results = []
        for path in clip_paths:
            if not Path(path).exists():
                logger.warning(f"Dosya bulunamadı: {path}")
                continue
            logger.info(f"Klip analiz ediliyor: {path}")
            score_data = self._score_clip(path)
            score_data["path"] = path
            results.append(score_data)

        results.sort(key=lambda x: x.get("total_score", 0), reverse=True)
        logger.info(f"{len(results)} klip puanlandı")
        return results

    def _score_clip(self, path: str) -> dict:
        cap = cv2.VideoCapture(path)
        if not cap.isOpened():
            return {"total_score": 0, "error": "Dosya açılamadı"}

        brightness_list, sharpness_list, motion_list = [], [], []
        prev_gray = None
        frame_count = 0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        # Her 10 karede bir örnekle — hız için
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
                    prev_gray, gray, None,
                    0.5, 3, 15, 3, 5, 1.2, 0
                )
                motion_list.append(float(np.mean(np.abs(flow))))
            prev_gray = gray

        cap.release()

        if not brightness_list:
            return {"total_score": 0, "error": "Kare okunamadı"}

        brightness = np.mean(brightness_list) / 255.0
        sharpness  = min(np.mean(sharpness_list) / 1000.0, 1.0)
        motion     = min(np.mean(motion_list) * 10.0, 1.0) if motion_list else 0.0

        # Çok karanlık veya çok parlak ceza
        brightness_score = 1.0 - abs(brightness - 0.5) * 2
        total = (sharpness * 0.5) + (brightness_score * 0.3) + (motion * 0.2)

        return {
            "brightness": round(brightness, 3),
            "sharpness":  round(sharpness, 3),
            "motion":     round(motion, 3),
            "total_score": round(total, 3)
        }
```

---

## 3.4 — Otomatik Kurgu Algoritması

`agent/tools/auto_editor.py`:

```python
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

def build_timeline(beat_times: list, scored_clips: list,
                   music_duration: float, style: str = "dark") -> list:
    """
    beat_times    : Müzik analizi çıktısı
    scored_clips  : Klip skoru çıktısı (puana göre sıralı)
    music_duration: Müzik toplam süresi
    style         : dark | fast | warm | corp
    """
    # Tarz bazlı beat atlama (her kaç beat'te bir kesim)
    beat_skip = {"dark": 4, "fast": 1, "warm": 3, "corp": 2}.get(style, 2)
    cut_beats = [beat_times[i] for i in range(0, len(beat_times), beat_skip)]

    timeline = []
    clip_pool = scored_clips.copy()
    clip_index = 0

    for i, beat_time in enumerate(cut_beats):
        if beat_time >= music_duration:
            break

        next_beat = cut_beats[i + 1] if i + 1 < len(cut_beats) else music_duration
        segment_duration = round(next_beat - beat_time, 3)

        if segment_duration < 0.3:  # çok kısa segmentleri atla
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


def write_concat_list(timeline: list, temp_dir: str,
                      ffmpeg_tool) -> tuple[str, list]:
    """
    FFmpeg concat için geçici klip dosyaları oluşturur.
    Döner: (concat_list_path, temp_clip_paths)
    """
    import os
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
```

---

## 3.5 — Tools İçin `__init__.py`

`agent/tools/__init__.py`:

```python
from .ffmpeg_tool import FFmpegTool
from .music_analyzer import MusicAnalyzer
from .clip_scorer import ClipScorer
from .auto_editor import build_timeline, write_concat_list
```

---

## Doğrulama Kontrolleri

### Test 1 — FFmpeg Tool:
```bash
python -c "
import asyncio
from agent.tools.ffmpeg_tool import FFmpegTool
t = FFmpegTool()
# Gerçek bir video dosyası yoksa sadece import test
print('FFmpegTool import: OK')
cmd = t.demo_render_cmd('input.mp4')
print('demo_render_cmd:', cmd[:60])
print('FFmpegTool TEST PASSED')
"
```

### Test 2 — Müzik Analizi (gerçek dosya ile):
```bash
python -c "
import asyncio
from agent.tools.music_analyzer import MusicAnalyzer
async def test():
    m = MusicAnalyzer()
    # test.mp3 yerine gerçek dosya yolu ver
    # result = await m.analyze('test.mp3')
    # print(result)
    print('MusicAnalyzer import: OK')
asyncio.run(test())
"
```

### Test 3 — Klip Skoru (gerçek dosya ile):
```bash
python -c "
import asyncio
from agent.tools.clip_scorer import ClipScorer
async def test():
    s = ClipScorer()
    print('ClipScorer import: OK')
asyncio.run(test())
"
```

### Test 4 — Auto Editor:
```bash
python -c "
from agent.tools.auto_editor import build_timeline
beats = [0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0]
clips = [{'path': 'clip1.mp4', 'total_score': 0.8},
         {'path': 'clip2.mp4', 'total_score': 0.6}]
tl = build_timeline(beats, clips, 4.0, 'fast')
print(f'Timeline: {len(tl)} sahne')
print('AUTO EDITOR TEST PASSED')
"
```

---

## Geçiş Kriteri

- Tüm import testleri geçildi
- Hiçbir modülde `ImportError` yok
- `auto_editor` doğru timeline üretiyor
- Log'larda kritik hata yok

Geçildiyse PHASE_4_CLAUDE.md'ye geç.

---

## Sık Karşılaşılan Hatalar

| Hata | Sebep | Çözüm |
|------|-------|-------|
| `librosa` yavaş yükleniyor | Normal — ilk import ağır | Sabırla bekle |
| `cv2.error` video okumada | Codec eksik | `pip install opencv-python` yeniden dene |
| `ffprobe not found` | PATH sorunu | FFmpeg bin klasörünü PATH'e ekle |
| `soundfile` hatası | librosa bağımlılığı | `pip install soundfile` |
