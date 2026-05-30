"""
DaVinci Resolve 20 Tool — Dosya tabanlı IPC bridge.

Kullanim:
  1. DaVinci Resolve'u ac
  2. Workspace > Console > Py3
  3. Asagidaki kodu yapistir ve Enter'a bas:
     exec(open(r"D:\\Users\\Hakan\\Desktop\\Proje\\Ai_Edit\\agent\\tools\\resolve_bridge.py").read())
  4. "Bridge hazir" yazisi gozuktu mu? Artik bu tool kullanilabilir.
"""
import asyncio
import json
import logging
import time
import os
from pathlib import Path

logger = logging.getLogger(__name__)

_BASE     = Path(os.getenv("TEMP_DIR", "./temp")).resolve()
_CMD_FILE = _BASE / "resolve_cmd.json"
_RES_FILE = _BASE / "resolve_result.json"
_TIMEOUT  = 30  # saniye


async def _call(op: str, **kwargs) -> dict:
    """Bridge'e komut gönder, sonucu bekle."""
    _BASE.mkdir(parents=True, exist_ok=True)

    # Eski sonuç dosyası varsa temizle
    _RES_FILE.unlink(missing_ok=True)

    cmd = {"op": op, **kwargs}
    _CMD_FILE.write_text(json.dumps(cmd), encoding="utf-8")

    # Sonuç bekle
    deadline = time.time() + _TIMEOUT
    while time.time() < deadline:
        await asyncio.sleep(0.3)
        if _RES_FILE.exists():
            try:
                result = json.loads(_RES_FILE.read_text(encoding="utf-8"))
                _RES_FILE.unlink(missing_ok=True)
                return result
            except json.JSONDecodeError:
                await asyncio.sleep(0.1)  # yazım henüz tamamlanmamış
                continue

    _CMD_FILE.unlink(missing_ok=True)
    return {
        "ok": False,
        "error": (
            f"{_TIMEOUT}s içinde yanıt gelmedi. "
            "Resolve konsolu açık ve bridge çalışıyor mu?\n"
            "Workspace > Console > Py3 > "
            "exec(open(r'...\\resolve_bridge.py').read())"
        )
    }


class DaVinciTool:

    async def check_connection(self) -> dict:
        result = await _call("check")
        result["connected"]   = result.get("ok", False)
        result["resolve_ver"] = result.get("version")
        result["project_name"]  = result.get("project")
        result["timeline_name"] = result.get("timeline")
        return result

    async def apply_lut(self, lut_path: str, node_index: int = 1) -> dict:
        abs_path = str(Path(lut_path).resolve())
        return await _call("apply_lut", lut_path=abs_path, node_index=node_index)

    async def apply_color_preset(self, style: str) -> dict:
        lut_map = {
            "dark": "dark_dramatic.cube",
            "warm": "warm_cinema.cube",
            "corp": "cool_corporate.cube",
            "fast": "fast_vivid.cube",
        }
        lut_file = lut_map.get(style, "natural_soft.cube")
        lut_path = str((Path("luts") / lut_file).resolve())
        if not Path(lut_path).exists():
            return {"ok": False, "error": f"LUT bulunamadı: {lut_path}"}
        result = await self.apply_lut(lut_path)
        result["style"] = style
        return result

    async def import_clips(self, clip_paths: list[str]) -> dict:
        return await _call("import_clips", paths=clip_paths)

    async def create_timeline_from_clips(self, clip_paths: list[str],
                                          timeline_name: str = "AI_Edit") -> dict:
        return await _call("create_timeline", paths=clip_paths, name=timeline_name)

    async def render(self, output_path: str,
                     format_: str = "mp4", codec: str = "H264") -> dict:
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        return await _call("render", output_path=output_path,
                           format=format_, codec=codec)

    async def get_project_info(self) -> dict:
        return await _call("get_info")

    @staticmethod
    def bridge_command() -> str:
        """Resolve konsoluna yapıştırılacak komut."""
        bridge = str(Path(__file__).parent / "resolve_bridge.py")
        return f'exec(open(r"{bridge}").read())'
