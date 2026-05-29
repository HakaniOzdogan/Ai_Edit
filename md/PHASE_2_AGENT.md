# PHASE 2 — Python FastAPI Agent + WebSocket Sunucusu

Önceki adım: PHASE_1_ENV.md (tüm doğrulamalar geçilmiş olmalı)
Sonraki adım: PHASE_3_TOOLS.md

---

## Amaç

Electron ile iletişim kuracak WebSocket sunucusunu ve HTTP API'yi yaz.
Bu adım sonunda agent başlatılabilir ve basit bir ping-pong testi geçilmiş olmalı.

---

## 2.1 — Pydantic Modelleri

`agent/models/project.py`:

```python
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class MediaFiles(BaseModel):
    clips: List[str] = []
    photos: List[str] = []
    music: Optional[str] = None
    logo: Optional[str] = None

class ProjectConfig(BaseModel):
    project_id: str
    name: str
    type: str        # product | event | social | travel
    style: str       # dark | fast | warm | corp
    music_choice: str
    reference: Optional[str] = None
    created_at: datetime = datetime.now()

class CommandMessage(BaseModel):
    type: str = "command"
    command: str
    project_id: str
    files: Optional[MediaFiles] = None
    profile: Optional[str] = None
```

`agent/models/profile.py`:

```python
from pydantic import BaseModel
from typing import Optional

class BrandProfile(BaseModel):
    name: str
    bpm: float
    avg_cut_duration: float
    color_tone: str       # warm | cool | neutral
    transition_style: str # hard_cut | dissolve | whip_pan
    style_tag: str
    lut_file: Optional[str] = None
    created_at: str
```

---

## 2.2 — Ana Agent Sunucusu

`agent/main.py`:

```python
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import json
import asyncio
import logging
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI(title="AI Video Editor Agent")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

connected_clients = []

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    connected_clients.append(ws)
    logger.info("Electron bağlandı")
    try:
        while True:
            data = await ws.receive_json()
            logger.info(f"Komut alındı: {data.get('command', '')[:80]}")
            await handle_command(ws, data)
    except WebSocketDisconnect:
        connected_clients.remove(ws)
        logger.info("Electron bağlantısı kesildi")
    except Exception as e:
        logger.error(f"WebSocket hatası: {e}")
        if ws in connected_clients:
            connected_clients.remove(ws)

async def handle_command(ws: WebSocket, data: dict):
    # Şimdilik echo — PHASE_4'te Claude entegrasyonu gelecek
    cmd = data.get("command", "")
    await ws.send_json({
        "type": "progress",
        "step": "received",
        "status": "ok",
        "message": f"Komut alındı: {cmd[:60]}"
    })
    # Placeholder yanıt
    await asyncio.sleep(0.5)
    await ws.send_json({
        "type": "result",
        "text": f"[PHASE_2 TEST] Komut işlendi: {cmd[:60]}"
    })

# HTTP Endpoints
@app.get("/health")
async def health():
    return {"status": "ok", "connected_clients": len(connected_clients)}

@app.get("/projects")
async def list_projects():
    projects_dir = Path("./projects")
    projects_dir.mkdir(exist_ok=True)
    files = list(projects_dir.glob("*.json"))
    return {"projects": [f.stem for f in files]}

@app.get("/profiles")
async def list_profiles():
    profiles_dir = Path("./profiles")
    profiles_dir.mkdir(exist_ok=True)
    files = list(profiles_dir.glob("*.json"))
    return {"profiles": [f.stem for f in files]}

@app.get("/luts")
async def list_luts():
    luts_dir = Path("./luts")
    files = list(luts_dir.glob("*.cube"))
    return {"luts": [f.name for f in files]}

if __name__ == "__main__":
    logger.info("Agent başlatılıyor — ws://localhost:8765")
    uvicorn.run(app, host="localhost", port=8765, log_level="info")
```

---

## 2.3 — Agent Başlatma Scripti

`agent/start.bat` (Windows için):

```bat
@echo off
cd /d %~dp0..
call venv\Scripts\activate
python agent/main.py
```

---

## 2.4 — WebSocket Test İstemcisi

`agent/test_ws.py` — agent'ı test etmek için:

```python
import asyncio
import websockets
import json

async def test():
    uri = "ws://localhost:8765/ws"
    print(f"Bağlanıyor: {uri}")
    async with websockets.connect(uri) as ws:
        print("Bağlandı!")

        # Ping gönder
        msg = {"type": "command", "command": "merhaba test", "project_id": "test_001"}
        await ws.send(json.dumps(msg))
        print(f"Gönderildi: {msg}")

        # Yanıtları oku
        for _ in range(2):
            response = await ws.recv()
            data = json.loads(response)
            print(f"Yanıt: {data}")

        print("Test PASSED")

asyncio.run(test())
```

---

## Doğrulama Kontrolleri

### Terminal 1 — Agent başlat:
```bash
cd ai-video-editor
venv\Scripts\activate
python agent/main.py
```

Beklenen çıktı:
```
INFO: Agent başlatılıyor — ws://localhost:8765
INFO: Uvicorn running on http://localhost:8765
```

### Terminal 2 — HTTP sağlık kontrolü:
```bash
curl http://localhost:8765/health
```
Beklenen: `{"status":"ok","connected_clients":0}`

### Terminal 2 — WebSocket testi:
```bash
python agent/test_ws.py
```
Beklenen son satır: `Test PASSED`

### Terminal 2 — Endpoint testleri:
```bash
curl http://localhost:8765/projects
curl http://localhost:8765/profiles
curl http://localhost:8765/luts
```

---

## Geçiş Kriteri

- Agent hatasız başlıyor
- `/health` 200 dönüyor
- WebSocket testi PASSED
- Log'larda ERROR yok

Hepsi geçildiyse PHASE_3_TOOLS.md'ye geç.

---

## Sık Karşılaşılan Hatalar

| Hata | Sebep | Çözüm |
|------|-------|-------|
| `Address already in use :8765` | Port dolu | `netstat -ano \| findstr :8765` ile PID bul, `taskkill /PID xxx /F` ile kapat |
| `ModuleNotFoundError: fastapi` | Venv aktif değil | `venv\Scripts\activate` çalıştır |
| `Connection refused` | Agent başlamadı | Terminal 1'deki log'u oku |
| `websockets` import hatası | Kurulmamış | `pip install websockets` |
