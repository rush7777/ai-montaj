"""Umumiy yordamchi funksiyalar: FFmpeg topish, video ma'lumotlarini o'qish, JSON."""
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")


TOOLS = Path.home() / ".ai-montaj"


def ffmpeg_exe() -> str:
    """setup.ps1 o'rnatgan to'liq FFmpeg, PATH dagisi, bo'lmasa imageio-ffmpeg bilan kelgan binar fayl."""
    local = TOOLS / "ffmpeg" / "bin" / "ffmpeg.exe"
    if local.exists():
        return str(local)
    found = shutil.which("ffmpeg")
    if found:
        return found
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        sys.exit("FFmpeg topilmadi. setup.ps1 ni ishga tushiring.")


def run_ffmpeg(args, cwd=None, quiet=True):
    cmd = [ffmpeg_exe(), "-hide_banner", "-y"] + [str(a) for a in args]
    if quiet:
        cmd[3:3] = ["-loglevel", "error"]
    res = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if res.returncode != 0:
        sys.exit(f"FFmpeg xatosi:\n{' '.join(cmd)}\n\n{res.stderr[-3000:]}")
    return res


def probe(path) -> dict:
    """ffprobe'siz video ma'lumotlari: o'lcham (aylanish hisobga olingan), fps, davomiylik, ovoz bormi."""
    res = subprocess.run([ffmpeg_exe(), "-hide_banner", "-i", str(path)],
                         capture_output=True, text=True, encoding="utf-8", errors="replace")
    err = res.stderr
    info = {"width": 0, "height": 0, "fps": 30.0, "duration": 0.0, "has_audio": " Audio:" in err}
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", err)
    if m:
        h, mi, s = m.groups()
        info["duration"] = int(h) * 3600 + int(mi) * 60 + float(s)
    vline = next((l for l in err.splitlines() if " Video:" in l), "")
    m = re.search(r", (\d{2,5})x(\d{2,5})", vline)
    if m:
        info["width"], info["height"] = int(m.group(1)), int(m.group(2))
    m = re.search(r"([\d.]+) fps", vline)
    if m:
        info["fps"] = float(m.group(1))
    m = re.search(r"rotation of (-?[\d.]+) degrees", err)
    if m and abs(round(float(m.group(1)))) % 180 == 90:
        info["width"], info["height"] = info["height"], info["width"]
    if not info["width"]:
        sys.exit(f"Video o'qilmadi: {path}")
    return info


def load_json(path):
    with open(path, encoding="utf-8-sig") as f:  # Bloknot/PowerShell qo'shadigan BOM ham qabul qilinadi
        return json.load(f)


def save_json(data, path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def resolve(path) -> Path:
    """Nisbiy yo'llar loyiha ildiziga nisbatan."""
    p = Path(path)
    return p if p.is_absolute() else ROOT / p


def edit_files(edit_path: Path) -> dict:
    """Bitta papkada bir nechta reja (edit.json, pro.edit.json, reel1.edit.json...) bo'lsa,
    ularning oraliq fayllari bir-birini ustidan yozmasligi uchun alohida nomlar."""
    work = edit_path.parent
    tag = edit_path.name[:-len(".json")]
    tag = "" if tag == "edit" else tag.replace(".edit", "") + "."
    return {"work": work, "tag": tag,
            "timeline_json": work / f"{tag}timeline.json", "timeline_txt": work / f"{tag}timeline.txt",
            "segments": work / f"{tag}segments", "concat": f"{tag}concat.txt", "subs": f"{tag}subs.ass"}


def all_words(transcript: dict) -> list:
    return [w for seg in transcript["segments"] for w in seg["words"]]


def fmt_time(t: float) -> str:
    return f"{int(t // 60)}:{t % 60:05.2f}"


os.environ.setdefault("PYTHONIOENCODING", "utf-8")
