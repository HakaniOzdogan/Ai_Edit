from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import asyncio
import logging
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI(title="AI Video Editor Agent")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

connected_clients: list[WebSocket] = []


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
    # PHASE_4'te Claude entegrasyonu gelecek
    cmd = data.get("command", "")
    await ws.send_json({
        "type": "progress",
        "step": "received",
        "status": "ok",
        "message": f"Komut alındı: {cmd[:60]}"
    })
    await asyncio.sleep(0.5)
    await ws.send_json({
        "type": "result",
        "text": f"[PHASE_2 TEST] Komut işlendi: {cmd[:60]}"
    })


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
