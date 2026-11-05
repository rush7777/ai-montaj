"""Remotion qatlami: edit.json dagi {"type": "remotion"} animatsiya bloklarini shaffof klip (ProRes 4444) qilib render qiladi.

Blok: {"type": "remotion", "comp": "StepCard", "start": 15.2, "end": 19.4, "props": {...}}
Kompozitsiyalar loyihaning remotion/ papkasida (Root.jsx da ro'yxat). Render paytida ular
%USERPROFILE%\\.ai-montaj\\remotion\\src ga ko'chiriladi (node_modules o'sha yerda). Natija keshlanadi:
props va kompozitsiya kodi o'zgarmasa, qayta render qilinmaydi.

Misol (bitta blokni sinash):
    python montaj/remotion_layer.py work/video/edit.json
    python montaj/remotion_layer.py --still StepCard 1.5 '{"step": 2, "title": "Asboblar"}'   # bitta kadr PNG
"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

from common import ROOT, edit_files, load_json

TOOLS = Path.home() / ".ai-montaj"
RDIR = TOOLS / "remotion"
NODE_DIR = TOOLS / "node"
SRC = ROOT / "remotion"
FONTS = ROOT / "assets" / "fonts"


def blocks_of(edit):
    return [b for b in (edit.get("animations") or []) if b.get("type") == "remotion"]


def _sync():
    """Kompozitsiyalar va shriftlarni Remotion papkasiga ko'chiradi; kod xeshini qaytaradi."""
    cli = RDIR / "node_modules" / "@remotion" / "cli" / "remotion-cli.js"
    if not cli.exists() or not (NODE_DIR / "node.exe").exists():
        sys.exit("Remotion topilmadi. setup.ps1 ni ishga tushiring (yoki .ai-montaj\\remotion da npm install).")
    dst = RDIR / "src"
    shutil.rmtree(dst, ignore_errors=True)
    shutil.copytree(SRC, dst)
    pub = RDIR / "public" / "fonts"
    pub.mkdir(parents=True, exist_ok=True)
    for f in FONTS.glob("*.ttf"):
        if not (pub / f.name).exists():
            shutil.copy2(f, pub / f.name)
    h = hashlib.sha1()
    for f in sorted(SRC.rglob("*")):
        if f.is_file():
            h.update(f.name.encode() + f.read_bytes())
    return cli, h.hexdigest()


def _run(cli, args):
    env = dict(os.environ)
    env["PATH"] = f"{NODE_DIR};{TOOLS / 'ffmpeg' / 'bin'};" + env.get("PATH", "")
    return subprocess.run([str(NODE_DIR / "node.exe"), str(cli)] + [str(a) for a in args], cwd=RDIR, env=env,
                          capture_output=True, text=True, encoding="utf-8", errors="replace")


def build(edit_path):
    """Har bir remotion bloki uchun [(klip.mov, start, end)] qaytaradi."""
    edit = load_json(edit_path)
    blocks = blocks_of(edit)
    if not blocks:
        return []
    tl = load_json(edit_files(edit_path)["timeline_json"])
    fps, total = tl["fps"], tl["duration"]
    W, H = tl.get("width", 1080), tl.get("height", 1920)
    theme = edit.get("theme") or {}
    cli, code = _sync()
    out_dir = RDIR / "out"
    out_dir.mkdir(exist_ok=True)
    clips = []
    for b in blocks:
        start = float(b.get("start", 0))
        end = float(b.get("end", start + 3))
        end = min(end, total)
        props = {"theme": {k: v for k, v in theme.items() if k in ("accent", "text", "dark")},
                 **(b.get("props") or {}), "duration": round(end - start, 3), "fps": fps, "width": W, "height": H}
        key = hashlib.sha1((code + b["comp"] + json.dumps(props, sort_keys=True, ensure_ascii=False)).encode()).hexdigest()[:16]
        mov = out_dir / f"{b['comp']}-{key}.mov"
        if not mov.exists():
            pfile = out_dir / f"{key}.props.json"
            pfile.write_text(json.dumps(props, ensure_ascii=False), encoding="utf-8")
            t0 = time.time()
            print(f"Remotion render: {b['comp']} {start:.2f}-{end:.2f} s...", flush=True)
            res = _run(cli, ["render", "src/index.jsx", b["comp"], mov, f"--props={pfile}", "--codec=prores",
                             "--prores-profile=4444", "--pixel-format=yuva444p10le", "--image-format=png",
                             "--log=error", "--concurrency=4"])
            if res.returncode != 0 or not mov.exists():
                sys.exit(f"Remotion xatosi ({b['comp']}):\n{res.stdout[-3000:]}\n{res.stderr[-3000:]}")
            print(f"  tayyor ({time.time() - t0:.0f} s): {mov.name}", flush=True)
        clips.append((mov, start, end))
    return clips


def still(comp, at, props, out):
    """Bitta kadr (PNG, shaffof) - kompozitsiyani tez ko'rish uchun."""
    cli, _ = _sync()
    props = {"duration": 3, "fps": 30, "width": 1080, "height": 1920, **props}
    pfile = RDIR / "out" / "still.props.json"
    pfile.parent.mkdir(exist_ok=True)
    pfile.write_text(json.dumps(props, ensure_ascii=False), encoding="utf-8")
    res = _run(cli, ["still", "src/index.jsx", comp, Path(out).resolve(), f"--props={pfile}",
                     f"--frame={int(at * props['fps'])}", "--image-format=png", "--log=error"])
    if res.returncode != 0:
        sys.exit(f"Remotion xatosi:\n{res.stdout[-3000:]}\n{res.stderr[-3000:]}")
    print(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("edit", nargs="?")
    ap.add_argument("--still", nargs=3, metavar=("COMP", "SONIYA", "PROPS_JSON"))
    ap.add_argument("--out", default="work/remotion_still.png")
    args = ap.parse_args()
    if args.still:
        comp, at, props = args.still
        still(comp, float(at), json.loads(props), ROOT / args.out)
        return
    if not args.edit:
        ap.error("edit.json yoki --still kerak")
    for mov, s, e in build(Path(args.edit).resolve()):
        print(f"{s:.2f}-{e:.2f}  {mov}")


if __name__ == "__main__":
    main()
