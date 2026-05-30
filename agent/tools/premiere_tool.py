"""
Premiere Pro 2026 Tool
----------------------
PProHeadless.exe ve ExtendScript ile timeline yönetimi.

Desteklenen islemler:
  - Klipleri timeline'a ekle
  - Sekans export et
  - Renk gradyan uygula (Lumetri)
"""
import asyncio
import logging
import os
import time
from pathlib import Path

logger = logging.getLogger(__name__)

def _find_pp_dir() -> str:
    import glob, winreg
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                            r"SOFTWARE\Adobe\Premiere Pro") as k:
            ver = winreg.EnumKey(k, 0)
            with winreg.OpenKey(k, ver) as vk:
                return winreg.QueryValueEx(vk, "InstallPath")[0]
    except Exception:
        pass
    matches = sorted(glob.glob(r"C:\Program Files\Adobe\Adobe Premiere Pro *"))
    return matches[-1] if matches else r"C:\Program Files\Adobe\Adobe Premiere Pro 2026"

PP_DIR      = _find_pp_dir()
PP_EXE      = os.path.join(PP_DIR, "Adobe Premiere Pro.exe")
PP_HEADLESS = os.path.join(PP_DIR, "PProHeadless.exe")
TEMP_DIR  = Path(os.getenv("TEMP_DIR", "./temp")).resolve()


async def _run_jsx(jsx_code: str, timeout: int = 120) -> dict:
    """ExtendScript'i Premiere Pro'ya gönderir."""
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    ts          = int(time.time() * 1000)
    jsx_path    = str(TEMP_DIR / f"pp_{ts}.jsx")
    result_path = str(TEMP_DIR / f"pp_result_{ts}.txt")

    result_escaped = result_path.replace("\\", "/")
    full_jsx = jsx_code + f'\nvar _f=new File("{result_escaped}");_f.open("w");_f.write("ok");_f.close();'

    with open(jsx_path, "w", encoding="utf-8") as f:
        f.write(full_jsx)

    proc = await asyncio.create_subprocess_exec(
        PP_EXE, "-doScript", jsx_path,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    try:
        _, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        proc.kill()
        return {"ok": False, "error": f"Premiere Pro {timeout}s timeout"}

    ok = Path(result_path).exists()
    for p in [jsx_path, result_path]:
        Path(p).unlink(missing_ok=True)

    return {"ok": ok, "error": "" if ok else stderr.decode(errors="replace")[-300:]}


class PremiereTool:

    # ── Yeni Proje + Sekans ──────────────────────────────────────────────────

    async def create_sequence(self, clip_paths: list[str], sequence_name: str,
                               fps: int = 25, output_dir: str = None) -> dict:
        """
        Kliplerden yeni bir Premiere Pro sekansı oluşturur.
        PProHeadless.exe ile headless çalışır.
        """
        if not output_dir:
            output_dir = str(TEMP_DIR / "output")
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        prproj_path  = str(TEMP_DIR / f"{sequence_name}.prproj").replace("\\", "/")
        output_video = str(Path(output_dir) / f"{sequence_name}.mp4").replace("\\", "/")

        clips_jsx = "\n".join(
            f'app.project.importFiles(["{p.replace(chr(92), "/")}"], true, bin, false);'
            for p in clip_paths
        )

        jsx = f"""
app.enableQE();
var proj = app.project;
proj.save(new File("{prproj_path}"));

// Klipleri içe aktar
var bin = proj.rootItem.createBin("{sequence_name}");
{clips_jsx}

// Sekans oluştur
var presetPath = "";
var seqPresets = qe.project.getSequencePresets();
for (var i = 0; i < seqPresets.length; i++) {{
    if (seqPresets[i].name.indexOf("1080") >= 0) {{
        presetPath = seqPresets[i].path;
        break;
    }}
}}
qe.project.newSequence("{sequence_name}", presetPath);
"""
        return await _run_jsx(jsx)

    # ── Export (AME üzerinden) ───────────────────────────────────────────────

    async def export_sequence(self, prproj_path: str, sequence_name: str,
                               output_path: str, preset: str = "H.264") -> dict:
        """
        PProHeadless.exe ile sekansı export eder.
        """
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        prproj_esc  = prproj_path.replace("\\", "/")
        output_esc  = output_path.replace("\\", "/")

        cmd = [
            PP_HEADLESS,
            "-project",  prproj_path,
            "-sequence", sequence_name,
            "-output",   output_path,
            "-preset",   preset,
        ]
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=600)
        except asyncio.TimeoutError:
            proc.kill()
            return {"ok": False, "error": "PProHeadless 600s timeout"}

        success = proc.returncode == 0 and Path(output_path).exists()
        return {
            "ok":          success,
            "output_path": output_path if success else None,
            "returncode":  proc.returncode,
            "stderr_tail": stderr.decode(errors="replace")[-300:],
        }

    # ── Lumetri Renk Gradyanı ────────────────────────────────────────────────

    async def apply_lumetri(self, sequence_name: str, style: str = "dark") -> dict:
        """
        Aktif sekansa Lumetri renk efekti uygular.
        style: dark | warm | corp | fast
        """
        presets = {
            "dark": {"exposure": -0.5, "contrast": 20, "saturation": 80,  "temp": -10},
            "warm": {"exposure":  0.2, "contrast": 10, "saturation": 110, "temp":  15},
            "corp": {"exposure":  0.0, "contrast":  5, "saturation": 95,  "temp":   0},
            "fast": {"exposure":  0.3, "contrast": 25, "saturation": 115, "temp":   5},
        }
        p = presets.get(style, presets["corp"])

        jsx = f"""
var seq = app.project.activeSequence;
if (!seq) throw new Error("Aktif sekans yok");

for (var i = 0; i < seq.videoTracks.numTracks; i++) {{
    var track = seq.videoTracks[i];
    for (var j = 0; j < track.clips.numItems; j++) {{
        var clip = track.clips[j];
        var fx = clip.components;
        for (var k = 0; k < fx.numItems; k++) {{
            if (fx[k].displayName === "Lumetri Color") {{
                var lum = fx[k].properties;
                lum.getParamForDisplayName("Exposure").setValue({p["exposure"]}, true);
                lum.getParamForDisplayName("Contrast").setValue({p["contrast"]}, true);
                lum.getParamForDisplayName("Saturation").setValue({p["saturation"]}, true);
                lum.getParamForDisplayName("Color Temperature").setValue({p["temp"]}, true);
            }}
        }}
    }}
}}
"""
        return await _run_jsx(jsx)

    # ── Premiere Pro Açık mı ─────────────────────────────────────────────────

    @staticmethod
    def is_pp_running() -> bool:
        import subprocess
        result = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq Adobe Premiere Pro.exe", "/NH"],
            capture_output=True, text=True
        )
        return "Adobe Premiere Pro.exe" in result.stdout

    @staticmethod
    def pp_path() -> str:
        return PP_EXE

    @staticmethod
    def headless_path() -> str:
        return PP_HEADLESS
