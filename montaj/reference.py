"""Namuna (referens) videodan montaj uslubini o'rganish uchun tahlil.

Misol:
    python montaj/reference.py https://www.youtube.com/shorts/XXXX           # havola (YouTube, TikTok...)
    python montaj/reference.py input/reference/namuna.mp4 --name raqib1      # yuklab olingan fayl
    python montaj/reference.py URL1 URL2 URL3 --name blogger                 # bir nechta video - umumiy uslub
    python montaj/reference.py https://www.tiktok.com/@user --max 10         # profil (yt-dlp qo'llasa)

Natija: work/reference/<nom>/ ichida
    report.json   - kesimlar tezligi, o'rtacha kadr uzunligi, ovoz balandligi, nutq zichligi
    sheet_*.png   - butun video bo'yicha kadrlar jadvali
    cuts_*.png    - har kesimdan keyingi kadrlar (subtitr, matn, zoom, B-roll uslubini ko'rish uchun)
Claude rasmlarni ko'rib, styles/passports/ ga yangi uslub pasporti yozadi (SKILL.md ga qarang).

Instagram ko'pincha login talab qiladi: videoni o'zingiz yuklab, input/reference/ ga qo'ying.
"""
import argparse
import json
import math
import re
import subprocess
import sys
from pathlib import Path

from common import ROOT, TOOLS, ffmpeg_exe, probe, resolve, run_ffmpeg, save_json


def download(urls, out_dir, max_n):
    out_dir.mkdir(parents=True, exist_ok=True)
    cmd = [sys.executable, "-m", "yt_dlp", "-f", "bv*[height<=1080][ext=mp4]+ba[ext=m4a]/b[height<=1080]/b",
           "--merge-output-format", "mp4", "--ffmpeg-location", str(Path(ffmpeg_exe()).parent),
           "--js-runtimes", f"node:{TOOLS / 'node' / 'node.exe'}",
           "-o", str(out_dir / "%(extractor)s_%(id)s.%(ext)s"), "--no-playlist" if max_n <= 1 else "--yes-playlist",
           "--playlist-end", str(max(max_n, 1)), "--print", "after_move:filepath", "--quiet", "--no-warnings"] + urls
    res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    files = [Path(l.strip()) for l in res.stdout.splitlines() if l.strip().endswith(".mp4")]
    if res.returncode != 0 and not files:
        sys.exit(f"Yuklab bo'lmadi:\n{res.stderr[-1500:]}\n"
                 "Instagram/yopiq profil bo'lsa: videoni o'zingiz yuklab input/reference/ ga qo'ying.")
    return files


def scene_cuts(path, threshold):
    res = subprocess.run([ffmpeg_exe(), "-hide_banner", "-i", str(path), "-vf",
                          f"scale=320:-2,select='gt(scene,{threshold})',showinfo", "-an", "-f", "null", "-"],
                         capture_output=True, text=True, encoding="utf-8", errors="replace")
    return [round(float(m), 3) for m in re.findall(r"pts_time:([\d.]+)", res.stderr)]


def loudness(path):
    res = subprocess.run([ffmpeg_exe(), "-hide_banner", "-nostats", "-i", str(path), "-af", "ebur128", "-f", "null", "-"],
                         capture_output=True, text=True, encoding="utf-8", errors="replace")
    m = re.findall(r"I:\s+(-?[\d.]+) LUFS", res.stderr)
    return float(m[-1]) if m else None


def speech_ratio(path, dur):
    res = subprocess.run([ffmpeg_exe(), "-hide_banner", "-nostats", "-i", str(path), "-af",
                          "silencedetect=n=-32dB:d=0.35", "-f", "null", "-"],
                         capture_output=True, text=True, encoding="utf-8", errors="replace")
    silent = sum(float(x) for x in re.findall(r"silence_duration: ([\d.]+)", res.stderr))
    return round(max(0.0, 1 - silent / max(dur, 0.01)), 2)


def analyze(path, out_dir, idx, threshold):
    info = probe(path)
    dur = info["duration"]
    cuts = scene_cuts(path, threshold)
    shots = [b - a for a, b in zip([0.0] + cuts, cuts + [dur]) if b - a > 0.05]
    tag = f"{idx:02d}"
    # butun video bo'yicha 18 kadr
    n = 18
    run_ffmpeg(["-i", path, "-vf", f"fps={n}/{max(dur, 1):.3f},scale=200:-2,"
                f"drawtext=text='%{{pts\\:hms}}':x=4:y=4:fontsize=16:fontcolor=white:box=1:boxcolor=black@0.6,"
                f"tile=6x3:padding=3:margin=3", "-frames:v", "1", out_dir / f"sheet_{tag}.png"])
    # kesimdan 0.4 s keyingi kadrlar (12 tagacha)
    picks = cuts[:: max(1, math.ceil(len(cuts) / 12))][:12] or [dur * 0.25, dur * 0.5, dur * 0.75]
    sel = "+".join(f"between(t,{t + 0.4:.2f},{t + 0.45:.2f})" for t in picks)
    run_ffmpeg(["-i", path, "-vf", f"select='{sel}',scale=270:-2,tile=6x2:padding=3:margin=3",
                "-vsync", "vfr", "-frames:v", "1", out_dir / f"cuts_{tag}.png"])
    return {
        "file": str(path),
        "width": info["width"], "height": info["height"], "fps": info["fps"], "duration": round(dur, 2),
        "cuts": len(cuts),
        "cuts_per_10s": round(len(cuts) / max(dur, 0.01) * 10, 1),
        "avg_shot_s": round(sum(shots) / len(shots), 2) if shots else round(dur, 2),
        "shortest_shot_s": round(min(shots), 2) if shots else None,
        "longest_shot_s": round(max(shots), 2) if shots else None,
        "loudness_lufs": loudness(path),
        "speech_ratio": speech_ratio(path, dur),
        "cut_times": cuts,
        "sheet": f"sheet_{tag}.png", "cut_frames": f"cuts_{tag}.png",
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("inputs", nargs="+", help="Havola(lar) yoki fayl(lar)")
    ap.add_argument("--name", default=None, help="Natija papkasi nomi (standart: birinchi fayl nomi)")
    ap.add_argument("--max", type=int, default=1, help="Profil/playlist havolasidan nechta video olish")
    ap.add_argument("--threshold", type=float, default=0.32, help="Kesimni aniqlash sezgirligi (0.2-0.5)")
    args = ap.parse_args()

    urls = [i for i in args.inputs if re.match(r"https?://", i)]
    files = [resolve(i) for i in args.inputs if not re.match(r"https?://", i)]
    if urls:
        files += download(urls, ROOT / "input" / "reference", args.max)
    if not files:
        sys.exit("Video topilmadi.")
    name = args.name or files[0].stem
    out_dir = ROOT / "work" / "reference" / name
    out_dir.mkdir(parents=True, exist_ok=True)

    videos = []
    for i, f in enumerate(files, 1):
        print(f"Tahlil {i}/{len(files)}: {f.name}", flush=True)
        videos.append(analyze(f, out_dir, i, args.threshold))
    avg = lambda k: round(sum(v[k] for v in videos if v[k] is not None) / max(1, sum(v[k] is not None for v in videos)), 2)
    summary = {"name": name, "videos": len(videos), "avg_duration_s": avg("duration"), "avg_shot_s": avg("avg_shot_s"),
               "cuts_per_10s": avg("cuts_per_10s"), "loudness_lufs": avg("loudness_lufs"),
               "speech_ratio": avg("speech_ratio")}
    save_json({"summary": summary, "videos": videos}, out_dir / "report.json")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"\nRasmlar: {out_dir}  (sheet_*.png, cuts_*.png)")


if __name__ == "__main__":
    main()
