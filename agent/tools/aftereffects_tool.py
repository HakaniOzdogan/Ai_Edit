"""
After Effects 2026 Tool
-----------------------
aerender.exe ile headless render.
AfterFX.exe -r ile JSX script calistirir.

Desteklenen islemler:
  - Logo reveal animasyonu
  - Alt yazı / metin overlay (lower third)
  - Flash/glitch gecis efekti
  - Mevcut kompozisyonu render et
"""
import asyncio
import logging
import os
import time
from pathlib import Path
from string import Template

logger = logging.getLogger(__name__)

AE_DIR      = r"C:\Program Files\Adobe\Adobe After Effects 2026\Support Files"
AFTERFX_EXE = os.path.join(AE_DIR, "AfterFX.exe")
AERENDER_EXE = os.path.join(AE_DIR, "aerender.exe")
TEMP_DIR    = Path(os.getenv("TEMP_DIR", "./temp")).resolve()


async def _run_jsx(jsx_code: str, timeout: int = 60) -> dict:
    """JSX scriptini AfterFX.exe ile çalıştırır (GUI gerektirir)."""
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    ts         = int(time.time() * 1000)
    jsx_path   = str(TEMP_DIR / f"ae_{ts}.jsx")
    result_path = str(TEMP_DIR / f"ae_result_{ts}.txt")

    # Sonucu dosyaya yaz
    full_jsx = jsx_code + f'\nvar _f=new File("{result_path.replace(chr(92),"/")}");_f.open("w");_f.write("ok");_f.close();'

    with open(jsx_path, "w", encoding="utf-8") as f:
        f.write(full_jsx)

    proc = await asyncio.create_subprocess_exec(
        AFTERFX_EXE, "-r", jsx_path,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    try:
        _, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        proc.kill()
        return {"ok": False, "error": f"AfterFX {timeout}s timeout"}

    err_msg = stderr.decode(errors="replace").strip()
    ok = Path(result_path).exists()

    for p in [jsx_path, result_path]:
        Path(p).unlink(missing_ok=True)

    if ok:
        return {"ok": True}
    return {"ok": False, "error": err_msg[-300:] or "JSX çalışırken hata oluştu"}


async def _aerender(project_path: str, comp_name: str, output_path: str,
                    timeout: int = 300) -> dict:
    """aerender.exe ile AEP projesini CLI'dan render eder."""
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        AERENDER_EXE,
        "-project",    project_path,
        "-comp",       comp_name,
        "-output",     output_path,
        "-OMtemplate", "H.264 — Match Render Settings — 15 Mbps",
    ]
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        proc.kill()
        return {"ok": False, "error": f"aerender {timeout}s timeout"}

    success = proc.returncode == 0 and Path(output_path).exists()
    return {
        "ok":          success,
        "output_path": output_path if success else None,
        "returncode":  proc.returncode,
        "stderr_tail": stderr.decode(errors="replace")[-300:],
    }


class AfterEffectsTool:

    # ── Logo Reveal ──────────────────────────────────────────────────────────

    async def logo_reveal(self, logo_path: str, duration: float = 3.0,
                          output_path: str = None, fps: int = 25) -> dict:
        """
        Logo fade-in + scale-up animasyonu oluşturur.
        output_path verilmezse temp/logo_reveal_{ts}.mp4 kullanılır.
        """
        if not output_path:
            ts = int(time.time())
            output_path = str(TEMP_DIR / "output" / f"logo_reveal_{ts}.mp4")

        logo_escaped = logo_path.replace("\\", "/")
        out_escaped  = output_path.replace("\\", "/")
        aep_path     = str(TEMP_DIR / f"logo_reveal_{int(time.time())}.aep")
        aep_escaped  = aep_path.replace("\\", "/")

        jsx = f"""
var comp = app.project.items.addComp(
    "logo_reveal", 1920, 1080, 1, {duration}, {fps}
);
var logoFile = new File("{logo_escaped}");
var importOpt = new ImportOptions(logoFile);
var logoItem = app.project.importFile(importOpt);
var logoLayer = comp.layers.add(logoItem);

logoLayer.property("ADBE Transform Group")
    .property("ADBE Opacity")
    .setValueAtTime(0, 0);
logoLayer.property("ADBE Transform Group")
    .property("ADBE Opacity")
    .setValueAtTime(0.8, 100);

logoLayer.property("ADBE Transform Group")
    .property("ADBE Scale")
    .setValueAtTime(0, [80, 80]);
logoLayer.property("ADBE Transform Group")
    .property("ADBE Scale")
    .setValueAtTime(0.8, [100, 100]);

app.project.save(new File("{aep_escaped}"));
"""
        jsx_result = await _run_jsx(jsx)
        if not jsx_result["ok"]:
            return jsx_result

        result = await _aerender(aep_path, "logo_reveal", output_path)
        Path(aep_path).unlink(missing_ok=True)
        return result

    # ── Metin Overlay (Lower Third) ──────────────────────────────────────────

    async def add_text_overlay(self, title: str, subtitle: str = "",
                                duration: float = 5.0, output_path: str = None,
                                fps: int = 25) -> dict:
        """
        Alt yazı / lower third kompozisyonu oluşturur.
        """
        if not output_path:
            ts = int(time.time())
            output_path = str(TEMP_DIR / "output" / f"text_overlay_{ts}.mp4")

        out_escaped = output_path.replace("\\", "/")
        aep_path    = str(TEMP_DIR / f"text_{int(time.time())}.aep")
        aep_escaped = aep_path.replace("\\", "/")

        title_esc    = title.replace('"', '\\"')
        subtitle_esc = subtitle.replace('"', '\\"')

        jsx = f"""
var comp = app.project.items.addComp(
    "text_overlay", 1920, 1080, 1, {duration}, {fps}
);

// Arka plan şeridi
var bgLayer = comp.layers.addSolid(
    [0.05, 0.05, 0.05], "bg", 1920, 160, 1, {duration}
);
bgLayer.property("ADBE Transform Group")
    .property("ADBE Position")
    .setValue([960, 950]);
bgLayer.property("ADBE Transform Group")
    .property("ADBE Opacity")
    .setValue(80);

// Başlık
var titleLayer = comp.layers.addText("{title_esc}");
var titleText = titleLayer.property("ADBE Text Document");
var td = titleText.value;
td.fontSize = 60;
td.fillColor = [1, 1, 1];
td.font = "Arial-BoldMT";
titleText.setValue(td);
titleLayer.property("ADBE Transform Group")
    .property("ADBE Position")
    .setValue([960, 920]);
titleLayer.property("ADBE Transform Group")
    .property("ADBE Opacity")
    .setValueAtTime(0.2, 0);
titleLayer.property("ADBE Transform Group")
    .property("ADBE Opacity")
    .setValueAtTime(0.5, 100);

// Alt başlık
var subtitleLayer = comp.layers.addText("{subtitle_esc}");
var subText = subtitleLayer.property("ADBE Text Document");
var sd = subText.value;
sd.fontSize = 36;
sd.fillColor = [0.8, 0.8, 0.8];
sd.font = "ArialMT";
subText.setValue(sd);
subtitleLayer.property("ADBE Transform Group")
    .property("ADBE Position")
    .setValue([960, 975]);

app.project.save(new File("{aep_escaped}"));
"""
        jsx_result = await _run_jsx(jsx)
        if not jsx_result["ok"]:
            return jsx_result

        result = await _aerender(aep_path, "text_overlay", output_path)
        Path(aep_path).unlink(missing_ok=True)
        return result

    # ── Flash Geçiş ──────────────────────────────────────────────────────────

    async def flash_transition(self, duration: float = 0.5,
                                output_path: str = None, fps: int = 25) -> dict:
        """Beyaz flash geçiş efekti oluşturur."""
        if not output_path:
            ts = int(time.time())
            output_path = str(TEMP_DIR / "output" / f"flash_{ts}.mp4")

        aep_path    = str(TEMP_DIR / f"flash_{int(time.time())}.aep")
        aep_escaped = aep_path.replace("\\", "/")
        half        = round(duration / 2, 2)

        jsx = f"""
var comp = app.project.items.addComp(
    "flash_transition", 1920, 1080, 1, {duration}, {fps}
);
var flashLayer = comp.layers.addSolid(
    [1, 1, 1], "flash", 1920, 1080, 1, {duration}
);
flashLayer.property("ADBE Transform Group")
    .property("ADBE Opacity")
    .setValueAtTime(0, 0);
flashLayer.property("ADBE Transform Group")
    .property("ADBE Opacity")
    .setValueAtTime({half}, 100);
flashLayer.property("ADBE Transform Group")
    .property("ADBE Opacity")
    .setValueAtTime({duration}, 0);

app.project.save(new File("{aep_escaped}"));
"""
        jsx_result = await _run_jsx(jsx)
        if not jsx_result["ok"]:
            return jsx_result

        result = await _aerender(aep_path, "flash_transition", output_path)
        Path(aep_path).unlink(missing_ok=True)
        return result

    # ── AE Açık mı Kontrol ───────────────────────────────────────────────────

    @staticmethod
    def is_ae_running() -> bool:
        import subprocess
        result = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq AfterFX.exe", "/NH"],
            capture_output=True, text=True
        )
        return "AfterFX.exe" in result.stdout

    @staticmethod
    def ae_path() -> str:
        return AFTERFX_EXE

    @staticmethod
    def aerender_path() -> str:
        return AERENDER_EXE
