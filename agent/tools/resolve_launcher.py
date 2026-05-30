"""
DaVinci Resolve 20 Otomatik Launcher
-------------------------------------
1. Resolve açık değilse başlatır
2. Workspace > Console penceresini açar
3. Py3 sekmesine geçer
4. resolve_bridge.py'yi inject eder
5. Bridge'in hazır olduğunu doğrular

Kullanim:
    from agent.tools.resolve_launcher import ResolveLauncher
    launcher = ResolveLauncher()
    ok = await launcher.ensure_ready()
"""
import asyncio
import logging
import os
import subprocess
import time
from pathlib import Path

logger = logging.getLogger(__name__)

RESOLVE_EXE  = r"C:\Program Files\Blackmagic Design\DaVinci Resolve\Resolve.exe"
BRIDGE_SCRIPT = str(Path(__file__).parent / "resolve_bridge.py")
CMD_FILE      = Path(os.getenv("TEMP_DIR", "./temp")).resolve() / "resolve_cmd.json"
RES_FILE      = Path(os.getenv("TEMP_DIR", "./temp")).resolve() / "resolve_result.json"


class ResolveLauncher:

    def __init__(self):
        self._bridge_ready = False

    async def ensure_ready(self, timeout: int = 60) -> bool:
        """
        Resolve + bridge'in hazır olduğunu garantiler.
        Zaten hazırsa hemen True döner.
        """
        # Bridge çalışıyor mu? (hızlı ping)
        if await self._ping_bridge(timeout_s=2):
            logger.info("Bridge zaten hazır")
            self._bridge_ready = True
            return True

        # Resolve başlat
        if not self._is_resolve_running():
            logger.info("Resolve başlatılıyor...")
            await self._launch_resolve()
            if not await self._wait_resolve_window(timeout):
                logger.error("Resolve penceresi açılmadı")
                return False

        # Console aç + bridge inject
        ok = await asyncio.to_thread(self._inject_bridge_via_ui)
        if not ok:
            logger.error("Bridge inject başarısız")
            return False

        # Bridge hazır olana kadar bekle
        if await self._ping_bridge(timeout_s=15):
            self._bridge_ready = True
            logger.info("Bridge hazır — Resolve bağlantısı kuruldu")
            return True

        logger.error("Bridge 15sn içinde yanıt vermedi")
        return False

    # ── Resolve Başlatma ──────────────────────────────────────────────────────

    def _is_resolve_running(self) -> bool:
        import psutil
        for p in psutil.process_iter(['name']):
            if p.info['name'] and 'Resolve' in p.info['name']:
                return True
        return False

    async def _launch_resolve(self):
        subprocess.Popen([RESOLVE_EXE], creationflags=subprocess.DETACHED_PROCESS)
        await asyncio.sleep(3)

    async def _wait_resolve_window(self, timeout: int) -> bool:
        """Resolve ana penceresi açılana kadar bekle."""
        try:
            from pywinauto import Desktop
        except ImportError:
            # pywinauto yoksa sadece zaman bekle
            await asyncio.sleep(15)
            return self._is_resolve_running()

        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                app = Desktop(backend="uia").window(title_re=".*DaVinci Resolve.*")
                if app.exists():
                    await asyncio.sleep(3)  # tam yüklensin
                    return True
            except Exception:
                pass
            await asyncio.sleep(1)
        return False

    # ── Bridge Inject ──────────────────────────────────────────────────────────

    def _inject_bridge_via_ui(self) -> bool:
        """
        pywinauto ile Resolve konsoluna bridge scriptini inject eder.
        Workspace → Console → Py3 → exec(...) → Enter
        """
        try:
            from pywinauto import Application, Desktop
            from pywinauto.keyboard import send_keys
            import pywinauto.mouse as mouse
        except ImportError:
            logger.warning("pywinauto yok — manuel bridge gerekiyor")
            return False

        bridge_path_escaped = BRIDGE_SCRIPT.replace("\\", "\\\\")
        bridge_cmd = f'exec(open(r"{bridge_path_escaped}").read())'

        try:
            # Resolve penceresini bul
            app = Application(backend="uia").connect(title_re=".*DaVinci Resolve.*", timeout=10)
            win = app.window(title_re=".*DaVinci Resolve.*")
            win.set_focus()
            time.sleep(0.5)

            # Workspace menüsünü aç
            win.menu_select("Workspace->Console")
            time.sleep(1.5)

            # Console penceresini bul
            console = Desktop(backend="uia").window(title_re=".*Console.*")
            if not console.exists(timeout=5):
                # Console ayrı pencere değil, ana pencere içinde
                console = win

            # Py3 butonuna tıkla
            py3 = None
            for ctrl in console.descendants(control_type="Button"):
                if ctrl.window_text() in ("Py3", "Python3", "Python 3"):
                    py3 = ctrl
                    break

            if py3:
                py3.click_input()
                time.sleep(0.5)
            else:
                logger.warning("Py3 butonu bulunamadı, devam ediliyor...")

            # Input alanını bul ve komutu yaz
            edit = None
            for ctrl in console.descendants(control_type="Edit"):
                edit = ctrl
                break

            if edit:
                edit.click_input()
                edit.type_keys(bridge_cmd, with_spaces=True)
                send_keys("{ENTER}")
                time.sleep(0.5)
                logger.info("Bridge komutu inject edildi")
                return True
            else:
                logger.warning("Console input alanı bulunamadı")
                return False

        except Exception as e:
            logger.error(f"UI inject hatası: {e}")
            return False

    # ── Bridge Ping ───────────────────────────────────────────────────────────

    async def _ping_bridge(self, timeout_s: int = 5) -> bool:
        """Bridge'in yanıt verip vermediğini kontrol eder."""
        import json
        base = Path(os.getenv("TEMP_DIR", "./temp")).resolve()
        cmd_f = base / "resolve_cmd.json"
        res_f = base / "resolve_result.json"

        base.mkdir(parents=True, exist_ok=True)
        res_f.unlink(missing_ok=True)
        cmd_f.write_text(json.dumps({"op": "check"}), encoding="utf-8")

        deadline = time.time() + timeout_s
        while time.time() < deadline:
            await asyncio.sleep(0.3)
            if res_f.exists():
                try:
                    result = json.loads(res_f.read_text(encoding="utf-8"))
                    res_f.unlink(missing_ok=True)
                    cmd_f.unlink(missing_ok=True)
                    return result.get("ok", False)
                except Exception:
                    pass

        cmd_f.unlink(missing_ok=True)
        return False

    @property
    def is_ready(self) -> bool:
        return self._bridge_ready
