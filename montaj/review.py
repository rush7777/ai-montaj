""""Tanqidchi ko'z": tayyor videodan kadrlar oladi va avtomatik sifat bahosini (0-100) chiqaradi.

Misol:
    python montaj/review.py output/video.mp4                       # butun video bo'yicha kadrlar jadvali
    python montaj/review.py output/video.mp4 --at 1.5 7 12         # aniq soniyalardagi to'liq kadrlar
    python montaj/review.py output/video.mp4 --score work/video/edit.json   # 0-100 ball + muammolar

Natija: work/review/<nom>/sheet.png, frame_<soniya>.png, score.json
Ball 85 dan past bo'lsa - muammolarni tuzatib, qayta render qiling.
"""
import argparse
import math
import re
import subprocess

import numpy as np

from common import ROOT, edit_files, ffmpeg_exe, load_json, probe, resolve, run_ffmpeg, save_json


def ffmpeg_stderr(args):
    return subprocess.run([ffmpeg_exe(), "-hide_banner", "-nostats"] + [str(a) for a in args],
                          capture_output=True, text=True, encoding="utf-8", errors="replace").stderr


def score(video, edit_path):
    info = probe(video)
    dur = info["duration"]
    issues, points = [], 100

    def penalty(n, msg):
        nonlocal points
        points -= n
        issues.append(f"-{n}: {msg}")

    # 1. ovoz
    err = ffmpeg_stderr(["-i", video, "-af", "ebur128=peak=true", "-f", "null", "-"])
    lufs = re.findall(r"I:\s+(-?[\d.]+) LUFS", err)
    peak = re.findall(r"Peak:\s+(-?[\d.]+) dBFS", err)
    lufs = float(lufs[-1]) if lufs else None
    peak = float(peak[-1]) if peak else None
    if lufs is not None and not -16.5 <= lufs <= -11.5:
        penalty(10, f"ovoz balandligi {lufs} LUFS (me'yor -14 atrofida)")
    if peak is not None and peak > -0.5:
        penalty(8, f"ovoz cho'qqisi {peak} dBFS - buzilish (clipping) xavfi")

    # 2. qora va qotgan kadrlar
    err = ffmpeg_stderr(["-i", video, "-vf", "scale=270:-2,blackdetect=d=0.15:pix_th=0.08,freezedetect=n=0.002:d=1.2",
                         "-an", "-f", "null", "-"])
    blacks = re.findall(r"black_start:([\d.]+)", err)
    freezes = re.findall(r"freeze_start: ([\d.]+)", err)
    if edit_path and blacks:
        # rejadagi fade va "dip" o'tishlari ataylab qilingan qora kadrlar - ularni hisoblamaymiz
        edit = load_json(edit_path)
        fade = edit.get("fade") or {}
        fade = {"out": float(fade)} if isinstance(fade, (int, float)) else fade
        ok = []
        if fade.get("in"):
            ok.append((0, float(fade["in"]) + 0.1))
        if fade.get("out"):
            ok.append((dur - float(fade["out"]) - 0.1, dur + 1))
        tlp = edit_files(edit_path)["timeline_json"]
        for s in (load_json(tlp)["segments"] if tlp.exists() else []):
            if s.get("_tr") and s["_tr"]["xfade"].startswith("fadeblack"):
                ok.append((s["offset"] - 0.1, s["offset"] + s["_tr"]["dur"] + 0.1))
        blacks = [b for b in blacks if not any(lo <= float(b) <= hi for lo, hi in ok)]
    if blacks:
        penalty(min(20, 10 * len(blacks)), f"qora kadr(lar): {', '.join(blacks[:5])} s")
    if freezes:
        penalty(min(15, 5 * len(freezes)), f"qotib qolgan kadr(lar): {', '.join(freezes[:5])} s")

    # 3. ritm, subtitr va yuz (reja bo'lsa)
    detail = {}
    if edit_path:
        edit = load_json(edit_path)
        F = edit_files(edit_path)
        tl = load_json(F["timeline_json"]) if F["timeline_json"].exists() else None
        if tl:
            shots = [s["dur"] for s in tl["segments"]]
            avg = sum(shots) / len(shots)
            detail["avg_shot_s"] = round(avg, 2)
            longest = max(shots)
            pp_name = edit.get("passport")
            max_shot = None
            if pp_name:
                import passport
                max_shot = passport.load_all().get(pp_name, {}).get("pacing", {}).get("max_shot_s")
            limit = (max_shot or 4.5) * 1.6
            if longest > limit:
                penalty(6, f"eng uzun kadr {longest:.1f} s - tomoshabin zerikishi mumkin (chegara {limit:.1f} s)")
            if dur > 3 and tl["words"] and tl["words"][0]["start"] > 1.2:
                penalty(8, f"birinchi so'z {tl['words'][0]['start']:.1f} s da - hook kechikmoqda")
        sub = edit.get("subtitles")
        if sub:
            styles = load_json(ROOT / "styles" / "subtitles.json")
            st = {**styles.get(sub.get("style", "pop"), {}), **sub}
            band = (st["position"] - st["size"] * 1.1 / info["height"], st["position"] + st["size"] * 1.1 / info["height"])
            hits = face_overlap(video, info, band)
            detail["subtitle_face_checks"] = hits
            if hits["overlap"]:
                penalty(min(20, 6 * hits["overlap"]),
                        f"subtitr {hits['overlap']} ta kadrda yuzni yopmoqda ({', '.join(hits['times'][:5])} s)"
                        f" - subtitles.position ni o'zgartiring")
        if not edit.get("animations") and not edit.get("title"):
            penalty(5, "hook uchun sarlavha yoki animatsiya yo'q")
        if not edit.get("sfx"):
            penalty(3, "SFX yo'q")

    points = max(0, points)
    result = {"score": points, "lufs": lufs, "peak_db": peak, "issues": issues, **detail}
    return result


def face_overlap(video, info, band):
    import cv2
    det = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    w = 360
    h = int(round(info["height"] * w / info["width"] / 2)) * 2
    raw = subprocess.run([ffmpeg_exe(), "-loglevel", "error", "-i", str(video), "-vf", f"fps=1,scale={w}:{h}",
                          "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], capture_output=True).stdout
    n = len(raw) // (w * h * 3)
    overlap, times, faces_seen = 0, [], 0
    for i in range(n):
        img = np.frombuffer(raw[i * w * h * 3:(i + 1) * w * h * 3], np.uint8).reshape(h, w, 3)
        faces = det.detectMultiScale(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), 1.1, 6, minSize=(w // 12, w // 12))
        if not len(faces):
            continue
        faces_seen += 1
        x, y, fw, fh = max(faces, key=lambda f: f[2] * f[3])
        # yuzning ko'z-og'iz qismi (ichki 70%) subtitr chizig'i bilan kesishadimi
        top, bottom = (y + fh * 0.15) / h, (y + fh * 0.85) / h
        if top < band[1] and bottom > band[0]:
            overlap += 1
            times.append(str(i))
    return {"frames": n, "faces": faces_seen, "overlap": overlap, "times": times}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("--at", nargs="*", type=float, default=[], help="Shu soniyalardagi kadrlarni olish")
    ap.add_argument("--count", type=int, default=24, help="Jadvaldagi kadrlar soni")
    ap.add_argument("--score", metavar="EDIT_JSON", nargs="?", const="", help="0-100 ball (reja berilsa batafsilroq)")
    args = ap.parse_args()

    video = resolve(args.video)
    info = probe(video)
    out_dir = ROOT / "work" / "review" / video.stem
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.score is not None:
        res = score(video, resolve(args.score) if args.score else None)
        save_json(res, out_dir / "score.json")
        print(f"BALL: {res['score']}/100   (ovoz {res['lufs']} LUFS, cho'qqi {res['peak_db']} dBFS)")
        for i in res["issues"]:
            print("  " + i)
        if not res["issues"]:
            print("  muammo topilmadi")
        return

    if args.at:
        for t in args.at:
            path = out_dir / f"frame_{t:06.2f}.png"
            run_ffmpeg(["-ss", f"{t:.3f}", "-i", video, "-frames:v", "1", "-vf", "scale=-2:960", path])
            print(path)
        return

    n = max(1, min(args.count, int(info["duration"] * 2)))
    cols = 6 if info["width"] < info["height"] else 4
    rows = math.ceil(n / cols)
    step = info["duration"] / n
    tile_w = 200 if cols == 6 else 320
    path = out_dir / "sheet.png"
    run_ffmpeg(["-i", video, "-vf",
                f"fps=1/{step:.4f},scale={tile_w}:-2,"
                f"drawtext=text='%{{pts\\:hms}}':x=6:y=6:fontsize=18:fontcolor=white:box=1:boxcolor=black@0.6,"
                f"tile={cols}x{rows}:padding=4:margin=4",
                "-frames:v", "1", path])
    print(f"{n} ta kadr, har {step:.1f} s da: {path}")


if __name__ == "__main__":
    main()
