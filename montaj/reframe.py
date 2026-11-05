"""Auto-reframe: har bo'lakda yuzni topib (OpenCV), kadrni (x, y) yuz tayyor kadrning
~35% balandligida va gorizontal markazda turadigan qilib sozlaydi. Zoom qancha katta bo'lsa, shuncha muhim.

Misol:
    python montaj/reframe.py work/video/edit.json            # barcha bo'laklar
    python montaj/reframe.py work/video/edit.json --eye 0.32 # yuz balandligi (0.25-0.45)
"""
import argparse
import subprocess

import numpy as np

from common import ffmpeg_exe, load_json, probe, resolve, save_json

OUT_ASPECT = {"9:16": 9 / 16, "16:9": 16 / 9, "1:1": 1.0, "4:5": 4 / 5}


def grab(src, t, w=480):
    raw = subprocess.run([ffmpeg_exe(), "-loglevel", "error", "-ss", f"{t:.3f}", "-i", str(src), "-frames:v", "1",
                          "-vf", f"scale={w}:-2", "-f", "rawvideo", "-pix_fmt", "bgr24", "-"],
                         capture_output=True).stdout
    return raw


def face_center(src, info, t0, t1):
    """Bo'lak ichidan 3 ta kadrda yuz qidiradi, eng kattasi markazini (0..1) qaytaradi."""
    import cv2
    det = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    w = 480
    h = int(round(info["height"] * w / info["width"] / 2)) * 2
    found = []
    for t in np.linspace(t0 + 0.15, max(t0 + 0.2, t1 - 0.15), 3):
        raw = grab(src, t, w)
        if len(raw) != w * h * 3:
            continue
        img = np.frombuffer(raw, np.uint8).reshape(h, w, 3)
        gray = cv2.equalizeHist(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY))
        faces = det.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=6, minSize=(w // 14, w // 14))
        if len(faces):
            x, y, fw, fh = max(faces, key=lambda f: f[2] * f[3])
            found.append(((x + fw / 2) / w, (y + fh / 2) / h, fw * fh))
    if not found:
        return None
    wsum = sum(a for *_, a in found)
    return sum(x * a for x, _, a in found) / wsum, sum(y * a for _, y, a in found) / wsum


def position(fx, fy, W, H, aspect, zoom, eye):
    cw, ch = (H * aspect, H) if W / H > aspect else (W, W / aspect)
    cw, ch = cw / zoom, ch / zoom
    clamp = lambda v: round(min(1.0, max(0.0, v)), 3)
    x = clamp((fx * W - 0.5 * cw) / (W - cw)) if W - cw > 1 else 0.5
    y = clamp((fy * H - eye * ch) / (H - ch)) if H - ch > 1 else 0.5
    return x, y


def reframe(edit, eye=0.35, verbose=True):
    src = resolve(edit["source"])
    info = probe(src)
    fmt = edit.get("format", "9:16")
    aspect = OUT_ASPECT.get(fmt, info["width"] / info["height"])
    for i, seg in enumerate(edit["segments"]):
        c = face_center(src, info, float(seg["start"]), float(seg["end"]))
        if not c:
            if verbose:
                print(f"  bo'lak {i}: yuz topilmadi - x/y o'zgarmadi")
            continue
        seg["x"], seg["y"] = position(c[0], c[1], info["width"], info["height"], aspect, float(seg.get("zoom", 1)), eye)
        if verbose:
            print(f"  bo'lak {i}: yuz ({c[0]:.2f}, {c[1]:.2f}) zoom {seg.get('zoom', 1)} -> x {seg['x']}, y {seg['y']}")
    return edit


def avatar(video, t, out, size=400):
    """Videodan yuz atrofini kvadrat qilib kesib, profil kartochka uchun avatar yasaydi."""
    from common import run_ffmpeg
    src = resolve(video)
    info = probe(src)
    c = face_center(src, info, t, t + 0.6)
    if not c:
        raise SystemExit(f"{t} s atrofida yuz topilmadi - boshqa vaqtni bering.")
    side = int(min(info["width"], info["height"]) * 0.42) // 2 * 2
    x = int(min(max(c[0] * info["width"] - side / 2, 0), info["width"] - side))
    y = int(min(max(c[1] * info["height"] - side * 0.45, 0), info["height"] - side))
    run_ffmpeg(["-ss", f"{t:.3f}", "-i", src, "-frames:v", "1",
                "-vf", f"crop={side}:{side}:{x}:{y},scale={size}:{size}:flags=lanczos", resolve(out)])
    print(f"Avatar: {resolve(out)}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("edit", nargs="?")
    ap.add_argument("--eye", type=float, default=0.35, help="Yuz markazi tayyor kadrning qaysi balandligida turadi")
    ap.add_argument("--avatar", nargs=3, metavar=("VIDEO", "SONIYA", "CHIQISH_PNG"),
                    help="Profil kartochka uchun videodan avatar kesib olish")
    args = ap.parse_args()
    if args.avatar:
        avatar(args.avatar[0], float(args.avatar[1]), args.avatar[2])
        return
    path = resolve(args.edit)
    save_json(reframe(load_json(path), args.eye), path)
    print(f"Saqlandi: {path}")


if __name__ == "__main__":
    main()
