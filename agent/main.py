import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import asyncio
import json
import uvicorn
import logging
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

PROJECTS_DIR = Path(os.getenv("PROJECTS_DIR", "./projects"))
PROFILES_DIR = Path(os.getenv("PROFILES_DIR", "./profiles"))
TEMP_DIR     = Path(os.getenv("TEMP_DIR",     "./temp"))

for d in (PROJECTS_DIR, PROFILES_DIR, TEMP_DIR, TEMP_DIR / "output"):
    d.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="AI Video Editor Agent", version="1.0.0")
app.add_middleware(CORSMiddleware,
    allow_origins=["http://localhost:8765", "http://127.0.0.1:8765", "*"],
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"]
)

connected_clients: list[WebSocket] = []

try:
    from agent.claude_client import ClaudeClient
    claude = ClaudeClient()
except RuntimeError as _api_err:
    logger.critical(f"Agent başlatılamadı: {_api_err}")
    claude = None

# ── WebSocket ─────────────────────────────────────────────────────────────────

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
        if ws in connected_clients:
            connected_clients.remove(ws)
        logger.info("Electron bağlantısı kesildi")
    except Exception as e:
        logger.error(f"WebSocket hatası: {e}")
        if ws in connected_clients:
            connected_clients.remove(ws)


async def handle_command(ws: WebSocket, data: dict):
    if claude is None:
        await ws.send_json({"type": "error",
                            "message": "ANTHROPIC_API_KEY eksik — .env dosyasını kontrol et"})
        return
    try:
        async for chunk in claude.process(data):
            await ws.send_json(chunk)
    except Exception as e:
        logger.error(f"Komut işleme hatası: {e}", exc_info=True)
        await ws.send_json({"type": "error", "message": str(e)})

# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok", "connected_clients": len(connected_clients),
            "version": "1.0.0"}

# ── Müzik İndirme ────────────────────────────────────────────────────────────

@app.post("/music/info")
async def music_info(data: dict):
    """URL'den parça bilgisi al (başlık, süre) — indirme yapmaz."""
    url = data.get("url", "").strip()
    if not url:
        raise HTTPException(status_code=400, detail="url gerekli")
    from agent.tools.music_downloader import get_info
    return await get_info(url)


@app.post("/music/download")
async def music_download(data: dict):
    """YouTube veya Spotify URL'sinden müzik indir."""
    url = data.get("url", "").strip()
    if not url:
        raise HTTPException(status_code=400, detail="url gerekli")
    from agent.tools.music_downloader import download_music
    result = await download_music(url)
    return result


# ── DaVinci Status ───────────────────────────────────────────────────────────

@app.post("/davinci/autostart")
async def davinci_autostart():
    """DaVinci Resolve'u otomatik başlatır ve bridge'i kurar."""
    from agent.tools.resolve_launcher import ResolveLauncher
    launcher = ResolveLauncher()

    # Zaten hazır mı?
    if await launcher._ping_bridge(timeout_s=2):
        return {"ok": True, "message": "Bridge zaten hazır"}

    # Resolve'u başlat ve bridge'i kur
    ok = await launcher.ensure_ready(timeout=45)
    if ok:
        return {"ok": True, "message": "DaVinci Resolve başlatıldı ve bridge kuruldu"}
    return {"ok": False, "message": "Otomatik başlatma başarısız — lütfen Resolve'u elle açın"}


@app.get("/davinci/status")
async def davinci_status():
    """DaVinci Resolve açık mı ve bridge bağlı mı kontrol eder."""
    import psutil, json as _json, time as _time

    # 1. Resolve.exe çalışıyor mu?
    resolve_running = any(
        "Resolve" in (p.name() or "")
        for p in psutil.process_iter(["name"])
    )

    # 2. Bridge bağlı mı? (hızlı ping: 2s timeout)
    bridge_active = False
    if resolve_running:
        cmd_f = TEMP_DIR / "resolve_cmd.json"
        res_f = TEMP_DIR / "resolve_result.json"
        try:
            res_f.unlink(missing_ok=True)
            cmd_f.write_text(_json.dumps({"op": "check"}), encoding="utf-8")
            deadline = _time.time() + 2
            while _time.time() < deadline:
                await asyncio.sleep(0.2)
                if res_f.exists():
                    result = _json.loads(res_f.read_text(encoding="utf-8"))
                    bridge_active = result.get("ok", False)
                    res_f.unlink(missing_ok=True)
                    break
        except Exception:
            pass
        finally:
            cmd_f.unlink(missing_ok=True)

    bridge_script = r"D:\Users\Hakan\Desktop\Proje\Ai_Edit\agent\tools\resolve_bridge.py"
    console_cmd   = f'exec(open(r"{bridge_script}").read())'

    return {
        "resolve_running": resolve_running,
        "bridge_active":   bridge_active,
        "console_cmd":     console_cmd,
    }

# ── Projects ──────────────────────────────────────────────────────────────────

@app.get("/projects")
async def list_projects():
    files = list(PROJECTS_DIR.glob("*.json"))
    return {"projects": [f.stem for f in files]}


@app.get("/projects/{project_id}")
async def get_project(project_id: str):
    path = PROJECTS_DIR / f"{project_id}.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Proje bulunamadı")
    return json.loads(path.read_text(encoding="utf-8"))


@app.post("/projects")
async def save_project(data: dict):
    project_id = data.get("project_id") or f"proj_{int(datetime.now().timestamp())}"
    data["project_id"] = project_id
    data["saved_at"]   = datetime.now().isoformat()
    path = PROJECTS_DIR / f"{project_id}.json"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"ok": True, "project_id": project_id}


@app.delete("/projects/{project_id}")
async def delete_project(project_id: str):
    path = PROJECTS_DIR / f"{project_id}.json"
    if path.exists():
        path.unlink()
    return {"ok": True}

# ── Profiles ──────────────────────────────────────────────────────────────────

@app.get("/profiles")
async def list_profiles():
    files = list(PROFILES_DIR.glob("*.json"))
    return {"profiles": [f.stem for f in files]}


@app.get("/profiles/{name}")
async def get_profile(name: str):
    path = PROFILES_DIR / f"{name}.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="Profil bulunamadı")
    return json.loads(path.read_text(encoding="utf-8"))


@app.post("/profiles/analyze")
async def analyze_profile(data: dict):
    """
    Referans video URL veya lokal yoldan marka profili oluşturur.
    reference_analyzer.py (Faz 5) implementasyonu bekleniyor.
    """
    source = data.get("source")
    name   = data.get("name", f"profile_{int(datetime.now().timestamp())}")
    if not source:
        raise HTTPException(status_code=400, detail="source alanı gerekli")
    # Stub — Faz 5'te ReferenceAnalyzer entegrasyonu gelecek
    return {"ok": False, "message": "Referans analizi henüz implement edilmedi (Faz 5)"}

# ── LUTs ─────────────────────────────────────────────────────────────────────

@app.get("/luts")
async def list_luts():
    luts_dir = Path(os.getenv("LUTS_DIR", "./luts"))
    files    = list(luts_dir.glob("*.cube"))
    return {"luts": [f.name for f in files]}

# ── Render ────────────────────────────────────────────────────────────────────

_render_jobs: dict = {}


@app.post("/render/demo")
async def start_demo_render(data: dict):
    """Demo render başlatır (WebSocket kullanmadan REST üzerinden)."""
    job_id = f"render_{int(datetime.now().timestamp())}"
    _render_jobs[job_id] = {"status": "running", "started_at": datetime.now().isoformat()}

    async def _run():
        data["render_type"] = "demo"
        results = []
        async for chunk in claude.process(data):
            results.append(chunk)
        _render_jobs[job_id]["status"] = "done"
        result_chunks = [c for c in results if c.get("type") == "result"]
        _render_jobs[job_id]["result"] = result_chunks[-1] if result_chunks else {}

    asyncio.create_task(_run())
    return {"ok": True, "job_id": job_id}


@app.post("/render/final")
async def start_final_render(data: dict):
    """Final 4K H.265 render başlatır."""
    job_id = f"render_{int(datetime.now().timestamp())}"
    _render_jobs[job_id] = {"status": "running", "started_at": datetime.now().isoformat()}

    async def _run():
        data["render_type"] = "final"
        results = []
        async for chunk in claude.process(data):
            results.append(chunk)
        _render_jobs[job_id]["status"] = "done"
        result_chunks = [c for c in results if c.get("type") == "result"]
        _render_jobs[job_id]["result"] = result_chunks[-1] if result_chunks else {}

    asyncio.create_task(_run())
    return {"ok": True, "job_id": job_id}


@app.get("/render/status/{job_id}")
async def render_status(job_id: str):
    if job_id not in _render_jobs:
        raise HTTPException(status_code=404, detail="Job bulunamadı")
    return _render_jobs[job_id]


if __name__ == "__main__":
    logger.info("Agent başlatılıyor — ws://localhost:8765")
    uvicorn.run(app, host="localhost", port=8765, log_level="info")
