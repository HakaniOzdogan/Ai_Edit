# PHASE 4 — Claude API Entegrasyonu + Tool Döngüsü

Önceki adım: PHASE_3_TOOLS.md (tüm araçlar import testi geçildi)
Sonraki adım: PHASE_5_ELECTRON.md

---

## Amaç

Claude'u sistemin karar motoru olarak entegre et.
Kullanıcı komutunu al → Claude'a ilet → tool_use döngüsünü yönet → sonucu Electron'a gönder.

---

## 4.1 — System Prompt

`agent/claude_client.py` başına ekle:

```python
SYSTEM_PROMPT = """
Sen AI Video Editor sisteminin karar motorusun.
Kullanıcı sana ham video/fotoğraf ve müzik atar;
sen analiz ederek profesyonel bir kurgu oluşturursun.

ARAÇLARIN:
- analyze_music  : Müzik BPM, beat ve drop tespiti
- score_clips    : Video klip kalite skorlaması
- run_ffmpeg     : Video kesme, birleştirme, render
- build_timeline : Beat-sync otomatik kurgu oluşturma

KURGU KURALLARI:
- Her zaman önce müziği analiz et (analyze_music)
- Ardından klipleri skorla (score_clips)
- Timeline'ı kurgula (build_timeline)
- Demo render al (run_ffmpeg — demo_render)
- Final render 4K H.265 olsun

TARZ TANIMLARI:
- dark_cinematic : 4 beat/sahne, desature, cool ton
- fast_cut       : 1 beat/sahne, high contrast, warm
- corporate      : 2 beat/sahne, clean, neutral
- warm_lifestyle : 3 beat/sahne, warm LUT, soft geçiş

YANIT KURALLARI:
- Her tool çağrısından önce kısaca ne yapacağını söyle
- İşlem sonucunu her zaman özetle
- Hata varsa açıkça belirt ve alternatif öner
- Türkçe yanıt ver
"""
```

---

## 4.2 — Tool Tanımları

```python
TOOLS = [
    {
        "name": "analyze_music",
        "description": "Müzik dosyasını analiz eder. BPM, beat zamanları, drop noktaları döner.",
        "input_schema": {
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "Müzik dosyasının tam yolu"}
            },
            "required": ["file_path"]
        }
    },
    {
        "name": "score_clips",
        "description": "Video kliplerini kalite açısından puanlar. Parlaklık, keskinlik, hareket analizi yapar.",
        "input_schema": {
            "type": "object",
            "properties": {
                "clip_paths": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Video dosyalarının tam yolları"
                }
            },
            "required": ["clip_paths"]
        }
    },
    {
        "name": "build_timeline",
        "description": "Beat analizine göre otomatik kurgu timeline oluşturur.",
        "input_schema": {
            "type": "object",
            "properties": {
                "beat_times":      {"type": "array", "items": {"type": "number"}},
                "scored_clips":    {"type": "array"},
                "music_duration":  {"type": "number"},
                "style":           {"type": "string", "enum": ["dark","fast","warm","corp"]}
            },
            "required": ["beat_times", "scored_clips", "music_duration"]
        }
    },
    {
        "name": "run_ffmpeg",
        "description": "FFmpeg ile video işlemi yapar. Trim, concat, render.",
        "input_schema": {
            "type": "object",
            "properties": {
                "operation":   {"type": "string", "enum": ["trim","concat","demo_render","final_render"]},
                "input_path":  {"type": "string"},
                "output_path": {"type": "string"},
                "params":      {"type": "object"}
            },
            "required": ["operation", "output_path"]
        }
    }
]
```

---

## 4.3 — Claude Client

`agent/claude_client.py`:

```python
import anthropic
import logging
import os
from pathlib import Path
from agent.tools.music_analyzer import MusicAnalyzer
from agent.tools.clip_scorer import ClipScorer
from agent.tools.ffmpeg_tool import FFmpegTool
from agent.tools.auto_editor import build_timeline

logger = logging.getLogger(__name__)

class ClaudeClient:

    def __init__(self):
        self.client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self.music  = MusicAnalyzer()
        self.scorer = ClipScorer()
        self.ffmpeg = FFmpegTool()

    async def process(self, data: dict):
        """
        Kullanıcı komutunu işler.
        Her adımda WebSocket'e progress veya result gönderir (generator).
        """
        messages = [{"role": "user", "content": self._build_prompt(data)}]
        context  = {"files": data.get("files", {}), "style": data.get("style", "dark")}

        yield {"type": "progress", "step": "claude_thinking", "status": "running"}

        while True:
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4096,
                system=SYSTEM_PROMPT,
                tools=TOOLS,
                messages=messages
            )

            if response.stop_reason == "end_turn":
                text = next(
                    (b.text for b in response.content if hasattr(b, "text")), ""
                )
                yield {"type": "result", "text": text}
                break

            if response.stop_reason == "tool_use":
                messages.append({"role": "assistant", "content": response.content})
                tool_results = []

                for block in response.content:
                    if block.type != "tool_use":
                        continue

                    yield {"type": "progress", "tool": block.name, "status": "running",
                           "message": f"{block.name} çalışıyor..."}

                    result = await self._run_tool(block.name, block.input, context)

                    yield {"type": "progress", "tool": block.name, "status": "done",
                           "result_summary": str(result)[:200]}

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": str(result)
                    })

                messages.append({"role": "user", "content": tool_results})

    async def _run_tool(self, name: str, inputs: dict, context: dict) -> dict:
        try:
            if name == "analyze_music":
                return await self.music.analyze(inputs["file_path"])

            if name == "score_clips":
                return await self.scorer.score(inputs["clip_paths"])

            if name == "build_timeline":
                tl = build_timeline(
                    inputs["beat_times"],
                    inputs["scored_clips"],
                    inputs["music_duration"],
                    inputs.get("style", context.get("style", "dark"))
                )
                context["timeline"] = tl
                return {"timeline": tl, "segment_count": len(tl)}

            if name == "run_ffmpeg":
                return await self._handle_ffmpeg(inputs, context)

            return {"error": f"Bilinmeyen araç: {name}"}

        except Exception as e:
            logger.error(f"Tool hatası [{name}]: {e}", exc_info=True)
            return {"error": str(e)}

    async def _handle_ffmpeg(self, inputs: dict, context: dict) -> dict:
        op = inputs["operation"]
        out = inputs["output_path"]
        Path(out).parent.mkdir(parents=True, exist_ok=True)

        if op == "demo_render":
            cmd = self.ffmpeg.demo_render_cmd(inputs.get("input_path", ""))
        elif op == "final_render":
            cmd = self.ffmpeg.render_4k_cmd(inputs.get("input_path", ""))
        elif op == "trim":
            p = inputs.get("params", {})
            cmd = self.ffmpeg.trim_cmd(inputs["input_path"], p.get("start", 0), p.get("duration", 5))
        elif op == "concat":
            cmd = self.ffmpeg.concat_cmd(inputs["input_path"])
        else:
            return {"error": f"Bilinmeyen FFmpeg operasyonu: {op}"}

        return await self.ffmpeg.run({"command": cmd, "output_path": out})

    def _build_prompt(self, data: dict) -> str:
        files = data.get("files", {})
        return f"""
Proje: {data.get('project_id', 'bilinmiyor')}
Tarz: {data.get('style', 'dark')}
Profil: {data.get('profile', 'yok')}

Medya dosyaları:
- Videolar: {files.get('clips', [])}
- Fotoğraflar: {files.get('photos', [])}
- Müzik: {files.get('music', 'yok')}
- Logo: {files.get('logo', 'yok')}

Kullanıcı komutu: {data.get('command', '')}

Yukarıdaki medyaları kullanarak profesyonel bir kurgu oluştur.
Önce müziği analiz et, sonra klipleri skorla, timeline kurgula ve demo render al.
"""
```

---

## 4.4 — Agent main.py Güncelleme

`agent/main.py` içindeki `handle_command` fonksiyonunu güncelle:

```python
from agent.claude_client import ClaudeClient

claude = ClaudeClient()

async def handle_command(ws: WebSocket, data: dict):
    try:
        async for chunk in claude.process(data):
            await ws.send_json(chunk)
    except Exception as e:
        logger.error(f"Komut işleme hatası: {e}", exc_info=True)
        await ws.send_json({"type": "error", "message": str(e)})
```

---

## Doğrulama Kontrolleri

### Test 1 — API bağlantısı:
```bash
python -c "
import anthropic, os
from dotenv import load_dotenv
load_dotenv()
client = anthropic.Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
r = client.messages.create(
    model='claude-sonnet-4-20250514',
    max_tokens=50,
    messages=[{'role':'user','content':'Merhaba, çalışıyor musun? Tek kelime yanıt ver.'}]
)
print('API yanıtı:', r.content[0].text)
print('API TEST PASSED')
"
```

### Test 2 — Tool döngüsü (mock dosyalarla):
```bash
python -c "
import asyncio
from agent.claude_client import ClaudeClient
async def test():
    c = ClaudeClient()
    data = {
        'command': 'Bana kısa bir özet ver, araç kullanma.',
        'project_id': 'test',
        'style': 'dark',
        'files': {}
    }
    async for chunk in c.process(data):
        print(chunk.get('type'), '-', chunk.get('message','')[:60] or chunk.get('text','')[:60])
asyncio.run(test())
"
```

### Test 3 — Agent tam çalışma:
Terminal 1'de agent'ı başlat, Terminal 2'de:
```bash
python -c "
import asyncio, websockets, json
async def test():
    async with websockets.connect('ws://localhost:8765/ws') as ws:
        msg = {
            'type': 'command',
            'command': 'Merhaba, bu bir test. Araç kullanmadan kısa yanıt ver.',
            'project_id': 'test_001',
            'style': 'dark',
            'files': {}
        }
        await ws.send(json.dumps(msg))
        for _ in range(5):
            try:
                r = await asyncio.wait_for(ws.recv(), timeout=30)
                data = json.loads(r)
                print(data.get('type'), data.get('text','')[:80] or data.get('message','')[:80])
                if data.get('type') == 'result':
                    break
            except asyncio.TimeoutError:
                break
asyncio.run(test())
"
```

---

## Geçiş Kriteri

- API bağlantısı başarılı
- Claude yanıt veriyor
- Tool döngüsü progress mesajları gönderiyor
- `result` tipi mesaj geliyor
- Log'larda `ANTHROPIC_API_KEY` ile ilgili hata yok

Geçildiyse PHASE_5_ELECTRON.md'ye geç.

---

## Sık Karşılaşılan Hatalar

| Hata | Sebep | Çözüm |
|------|-------|-------|
| `AuthenticationError` | API key yanlış | `.env` dosyasındaki key'i kontrol et |
| `RateLimitError` | Çok fazla istek | 60 saniye bekle |
| `Tool use` döngüsü bitmez | Sonsuz döngü | System prompt'a "maksimum 3 tool çağrısı" ekle |
| `ImportError: claude_client` | Venv aktif değil | `venv\Scripts\activate` |
