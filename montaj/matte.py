"""Odam niqobi (matte): MediaPipe bilan har kadrda odamni (soch, yuz, tana, kiyim) fondan ajratadi.

render.py "layer": "behind" bloklari uchun ishlatadi: katta so'z fon ustiga, odam esa niqob orqali so'z ustiga
qo'yiladi - so'z odam ORQASIDA turgandek ko'rinadi (Azizon: "GO'SHT", "KO'CHADAN").

Misol (sinash):
    python montaj/matte.py input/video.mp4 --start 12 --dur 3 --out work/matte_test.mkv
Natija: kulrang (gray) FFV1 video, oq = odam. Model: %USERPROFILE%\\.ai-montaj\\models\\mediapipe\\
"""
import argparse
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import TOOLS, ffmpeg_exe  # noqa: E402

MODEL = TOOLS / "models" / "mediapipe" / "selfie_multiclass_256x256.tflite"
MODEL_URL = ("https://storage.googleapis.com/mediapipe-models/image_segmenter/selfie_multiclass_256x256/"
             "float32/1/selfie_multiclass_256x256.tflite")


def _segmenter():
    try:
        import mediapipe as mp
        from mediapipe.tasks import python as mpp
        from mediapipe.tasks.python import vision
    except ImportError:
        sys.exit("MediaPipe o'rnatilmagan: setup.ps1 ni qayta ishga tushiring (yoki venv da pip install mediapipe).")
    if not MODEL.exists():
        sys.exit(f"Niqob modeli yo'q: {MODEL}\nsetup.ps1 ni qayta ishga tushiring (manba: {MODEL_URL}).")
    opts = vision.ImageSegmenterOptions(base_options=mpp.BaseOptions(model_asset_path=str(MODEL)),
                                        running_mode=vision.RunningMode.VIDEO,
                                        output_confidence_masks=True, output_category_mask=False)
    return mp, vision.ImageSegmenter.create_from_options(opts)


def build(video, start, dur, out, W, H, fps=30, concat=False, cwd=None, feather=3, grow=0):
    """video ning [start, start+dur] oralig'i uchun niqob videosini yozadi (W x H, gray, FFV1)."""
    mp, seg = _segmenter()
    sw, sh = 540, int(540 * H / W) // 2 * 2
    src = ["-f", "concat", "-safe", "0"] if concat else []
    rd = subprocess.Popen([ffmpeg_exe(), "-nostdin", "-loglevel", "error", "-ss", f"{start:.3f}"] + src +
                          ["-i", str(video), "-t", f"{dur:.3f}", "-vf", f"fps={fps},scale={sw}:{sh}",
                           "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE, cwd=cwd)
    wr = subprocess.Popen([ffmpeg_exe(), "-nostdin", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "gray",
                           "-s", f"{W}x{H}", "-r", str(fps), "-i", "-", "-c:v", "ffv1", "-pix_fmt", "gray", str(out)],
                          stdin=subprocess.PIPE, cwd=cwd)
    size, prev, n = sw * sh * 3, None, 0
    while True:
        buf = rd.stdout.read(size)
        if len(buf) < size:
            break
        rgb = np.frombuffer(buf, np.uint8).reshape(sh, sw, 3)
        res = seg.segment_for_video(mp.Image(image_format=mp.ImageFormat.SRGB, data=np.ascontiguousarray(rgb)),
                                    int(n * 1000 / fps))
        m = 1.0 - res.confidence_masks[0].numpy_view().reshape(sh, sw)
        m = np.clip((m - 0.25) / 0.5, 0, 1)                      # fondagi kulrang qoldiqni olib tashlash
        prev = m if prev is None else 0.55 * m + 0.45 * prev     # kadrlar orasida titramasin
        big = cv2.resize(prev.astype(np.float32), (W, H), interpolation=cv2.INTER_LINEAR)
        if grow:
            big = cv2.dilate(big, np.ones((grow, grow), np.uint8))
        if feather:
            k = feather * 2 + 1
            big = cv2.GaussianBlur(big, (k, k), 0)
        wr.stdin.write((big * 255).astype(np.uint8).tobytes())
        n += 1
    rd.wait()
    wr.stdin.close()
    wr.wait()
    seg.close()
    if n == 0:
        sys.exit(f"Niqob: kadr o'qilmadi ({video}, {start:.2f} s)")
    return n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("--start", type=float, default=0)
    ap.add_argument("--dur", type=float, default=3)
    ap.add_argument("--out", default="work/matte_test.mkv")
    ap.add_argument("--size", default="1080x1920")
    args = ap.parse_args()
    W, H = map(int, args.size.split("x"))
    n = build(Path(args.video).resolve(), args.start, args.dur, Path(args.out).resolve(), W, H)
    print(f"{n} kadr: {args.out}")


if __name__ == "__main__":
    main()
