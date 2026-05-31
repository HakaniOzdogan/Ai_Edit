"""
Remotion Tool — React tabanlı motion graphics renderer.
After Effects gerekmez. Node.js ile headless render.

Desteklenen:
  - logo_reveal   : Logo fade-in + scale animasyonu
  - text_overlay  : Başlık + alt başlık lower third
  - transition    : flash | glitch | fade geçiş efekti
"""
import asyncio
import json
import logging
import os
import uuid
from pathlib import Path

logger = logging.getLogger(__name__)

PROJECT_DIR  = Path(__file__).parent.parent.parent
REMOTION_DIR = PROJECT_DIR / "remotion"
TEMP_DIR     = Path(os.getenv("TEMP_DIR", "./temp")).resolve()
OUTPUT_DIR   = Path(os.getenv("OUTPUT_DIR", "./temp/output")).resolve()


async def _render(composition: str, props: dict, output_path: str,
                  duration_frames: int = 75, fps: int = 25,
                  timeout: int = 120) -> dict:
    """npx remotion render ile kompozisyon render eder."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    props_json = json.dumps(props)

    npx = "npx.cmd" if os.name == "nt" else "npx"
    cmd = [
        npx, "remotion", "render",
        str(REMOTION_DIR / "src" / "index.ts"),
        composition,
        output_path,
        f"--props={props_json}",
        f"--frames=0-{duration_frames - 1}",
        f"--fps={fps}",
        "--overwrite",
        "--log=verbose",
    ]
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        cwd=str(PROJECT_DIR),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        proc.kill()
        return {"ok": False, "error": f"Remotion {timeout}s timeout"}

    success = proc.returncode == 0 and Path(output_path).exists()
    if not success:
        err = stderr.decode(errors="replace")[-400:]
        logger.error(f"Remotion hata [{composition}]: {err}")
    return {
        "ok":          success,
        "output_path": output_path if success else None,
        "engine":      "remotion",
        "stderr_tail": stderr.decode(errors="replace")[-200:] if not success else "",
    }


class RemotionTool:

    async def logo_reveal(self, logo_path: str, style: str = "dark",
                           duration: float = 3.0, output_path: str = None) -> dict:
        """Logo reveal animasyonu — React/Remotion ile render."""
        if not output_path:
            OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
            output_path = str(OUTPUT_DIR / f"logo_reveal_{uuid.uuid4().hex[:8]}.mp4")

        # Logo yolunu forward slash'e çevir (JSX için)
        logo_fwd = str(Path(logo_path).resolve()).replace("\\", "/")
        fps      = 25
        frames   = int(duration * fps)

        return await _render(
            "LogoReveal",
            {"logoSrc": logo_fwd, "style": style},
            output_path,
            duration_frames=frames,
            fps=fps,
        )

    async def text_overlay(self, title: str, subtitle: str = "",
                            style: str = "dark", duration: float = 5.0,
                            output_path: str = None) -> dict:
        """Başlık + alt başlık lower third animasyonu."""
        if not output_path:
            OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
            output_path = str(OUTPUT_DIR / f"text_overlay_{uuid.uuid4().hex[:8]}.mp4")

        fps    = 25
        frames = int(duration * fps)

        return await _render(
            "TextOverlay",
            {"title": title, "subtitle": subtitle, "style": style, "duration": duration},
            output_path,
            duration_frames=frames,
            fps=fps,
        )

    async def transition(self, trans_type: str = "flash",
                          style: str = "dark", duration: float = 0.5,
                          output_path: str = None) -> dict:
        """Geçiş efekti: flash | glitch | fade"""
        if not output_path:
            OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
            output_path = str(OUTPUT_DIR / f"transition_{uuid.uuid4().hex[:8]}.mp4")

        fps    = 25
        frames = int(duration * fps)

        return await _render(
            "Transition",
            {"type": trans_type, "style": style},
            output_path,
            duration_frames=frames,
            fps=fps,
        )

    async def check_remotion(self) -> dict:
        """Remotion kurulu ve çalışıyor mu kontrol et."""
        try:
            npx = "npx.cmd" if os.name == "nt" else "npx"
            proc = await asyncio.create_subprocess_exec(
                npx, "remotion", "--version",
                cwd=str(PROJECT_DIR),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=15)
            version = stdout.decode().strip()
            return {"ok": True, "version": version}
        except Exception as e:
            return {"ok": False, "error": str(e)}
