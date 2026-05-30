# DaVinci Resolve 20 Konsol Bridge
# Resolve konsol penceresinde (Workspace > Console > Py3) calistir:
# exec(open(r"D:\\Users\\Hakan\\Desktop\\Proje\\Ai_Edit\\agent\\tools\\resolve_bridge.py").read())
import json, time, os, traceback
from pathlib import Path

BASE    = Path(r"D:\Users\Hakan\Desktop\Proje\Ai_Edit\temp")
CMD_FILE = BASE / "resolve_cmd.json"
RES_FILE = BASE / "resolve_result.json"
BASE.mkdir(exist_ok=True)

resolve = fusion.GetResolve()
if not resolve:
    print("HATA: fusion.GetResolve() None dondu")
else:
    print(f"Bridge hazir — Resolve {resolve.GetVersionString()}")
    print(f"Komut dosyasi: {CMD_FILE}")

def _execute(resolve, cmd):
    op = cmd.get("op")
    pm = resolve.GetProjectManager()
    proj = pm.GetCurrentProject()

    if op == "check":
        tl = proj.GetCurrentTimeline() if proj else None
        return {
            "version":   resolve.GetVersionString(),
            "project":   proj.GetName()  if proj else None,
            "timeline":  tl.GetName()    if tl   else None,
            "tl_fps":    tl.GetSetting("timelineFrameRate") if tl else None,
        }

    elif op == "apply_lut":
        lut_path   = cmd["lut_path"]
        node_index = cmd.get("node_index", 1)
        tl = proj.GetCurrentTimeline()
        if not tl: return {"error": "Aktif timeline yok"}
        resolve.OpenPage("color")
        applied = failed = 0
        for track in range(1, tl.GetTrackCount("video") + 1):
            for item in (tl.GetItemListInTrack("video", track) or []):
                if item.SetLUT(node_index, lut_path): applied += 1
                else: failed += 1
        proj.SaveProject()
        return {"applied": applied, "failed": failed}

    elif op == "import_clips":
        pool  = proj.GetMediaPool()
        items = pool.ImportMedia(cmd["paths"])
        return {"imported": len(items) if items else 0}

    elif op == "create_timeline":
        pool  = proj.GetMediaPool()
        items = pool.ImportMedia(cmd["paths"])
        if not items: return {"error": "Import basarisiz"}
        tl = pool.CreateTimelineFromClips(cmd.get("name", "AI_Edit"), items)
        if not tl: return {"error": "Timeline olusturulamadi"}
        proj.SetCurrentTimeline(tl)
        proj.SaveProject()
        return {"timeline": tl.GetName(), "clips": len(items)}

    elif op == "render":
        out_dir  = str(Path(cmd["output_path"]).parent)
        out_name = Path(cmd["output_path"]).stem
        tl = proj.GetCurrentTimeline()
        if not tl: return {"error": "Aktif timeline yok"}
        resolve.OpenPage("deliver")
        proj.SetCurrentTimeline(tl)
        proj.SetRenderSettings({
            "SelectAllFrames": True,
            "TargetDir":       out_dir,
            "CustomName":      out_name,
            "ExportVideo":     True,
            "ExportAudio":     True,
        })
        proj.SetCurrentRenderFormatAndCodec(
            cmd.get("format", "mp4"), cmd.get("codec", "H264")
        )
        job = proj.AddRenderJob()
        if not job: return {"error": "Render job eklenemedi"}
        proj.StartRendering(job)
        elapsed = 0
        while proj.IsRenderingInProgress() and elapsed < 1800:
            time.sleep(2); elapsed += 2
        proj.DeleteAllRenderJobs()
        return {"output_path": cmd["output_path"], "elapsed_s": elapsed}

    elif op == "get_info":
        tl      = proj.GetCurrentTimeline() if proj else None
        presets = list((proj.GetRenderPresets() or {}).keys()) if proj else []
        return {
            "project":        proj.GetName()           if proj else None,
            "timeline_count": proj.GetTimelineCount()  if proj else 0,
            "render_presets": presets,
            "timeline": {
                "name":   tl.GetName() if tl else None,
                "fps":    tl.GetSetting("timelineFrameRate") if tl else None,
                "tracks": tl.GetTrackCount("video") if tl else 0,
            } if tl else None,
        }

    return {"error": f"Bilinmeyen op: {op}"}


print("Dinleniyor... (durdurmak icin Cls'e bas veya Resolve'u kapat)")
while True:
    if CMD_FILE.exists():
        try:
            cmd = json.loads(CMD_FILE.read_text(encoding="utf-8"))
            CMD_FILE.unlink()
            result = {"ok": True, **_execute(resolve, cmd)}
        except Exception as e:
            result = {"ok": False, "error": str(e), "trace": traceback.format_exc()[-400:]}
        RES_FILE.write_text(json.dumps(result), encoding="utf-8")
    time.sleep(0.3)
