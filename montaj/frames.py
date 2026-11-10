"""Referens videoni kadrma-kadr tahlil qilish: har bir kadr uchun o'lchovlar, kesimlar ro'yxati, grafik va kadr jadvallari.

Misol:
    python montaj/frames.py input/reference/namuna.mp4
    python montaj/frames.py input/reference/namuna.mp4 --sheet-fps 5 --name namuna

Har bir kadr uchun (frames.csv):
    diff, hist     - oldingi kadrdan farq (kesim, o'tish)
    scale, tx, ty  - kadrlar orasidagi kamera harakati: zoom (1.0 dan katta = kattalashish), siljish
    face_x/y/h     - yuz markazi va balandligi (kadr ulushida) - plan o'lchami (yaqin/o'rta/umumiy)
    bright, sat, warm, contrast - rang
    text_*         - 12 gorizontal bo'lakda "grafik" piksellar (keskin oq/qora chegaralar: subtitr, sarlavha, stiker)
    audio_db       - ovoz balandligi
Natija: work/reference/<nom>/frames/ ichida frames.csv, shots.json, timeline.png, sheet_*.png, cut_*.png
"""
import argparse
import csv
import json
import subprocess
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, ffmpeg_exe, probe, resolve  # noqa: E402

W, H = 270, 480
BANDS = 12


def read_frames(path):
    cmd = [ffmpeg_exe(), "-nostdin", "-loglevel", "error", "-i", str(path), "-vf", f"scale={W}:{H}",
           "-f", "rawvideo", "-pix_fmt", "bgr24", "-"]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    size = W * H * 3
    while True:
        buf = p.stdout.read(size)
        if len(buf) < size:
            break
        yield np.frombuffer(buf, np.uint8).reshape(H, W, 3)
    p.wait()


def audio_db(path, fps, n):
    raw = subprocess.run([ffmpeg_exe(), "-nostdin", "-loglevel", "error", "-i", str(path), "-ac", "1", "-ar", "16000",
                          "-f", "s16le", "-"], capture_output=True).stdout
    a = np.frombuffer(raw, np.int16).astype(np.float32) / 32768
    hop = 16000 / fps
    out = []
    for i in range(n):
        seg = a[int(i * hop):int((i + 1) * hop)]
        rms = float(np.sqrt(np.mean(seg ** 2))) if len(seg) else 0.0
        out.append(round(20 * np.log10(max(rms, 1e-5)), 1))
    return out


def graphic_mask(img):
    """Keskin grafik chegaralar: matn, subtitr, stiker. Tabiiy kadrda bunday keskin oq-qora o'tish kam bo'ladi."""
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    k = np.ones((3, 3), np.uint8)
    grad = cv2.dilate(g, k).astype(np.int16) - cv2.erode(g, k).astype(np.int16)
    return grad > 150


def motion(prev_g, g):
    pts = cv2.goodFeaturesToTrack(prev_g, 200, 0.01, 8)
    if pts is None or len(pts) < 12:
        return 1.0, 0.0, 0.0
    nxt, st, _ = cv2.calcOpticalFlowPyrLK(prev_g, g, pts, None, winSize=(21, 21), maxLevel=3)
    ok = st.reshape(-1) == 1
    if ok.sum() < 12:
        return 1.0, 0.0, 0.0
    m, _ = cv2.estimateAffinePartial2D(pts[ok], nxt[ok], method=cv2.RANSAC, ransacReprojThreshold=2.0)
    if m is None:
        return 1.0, 0.0, 0.0
    s = float(np.hypot(m[0, 0], m[1, 0]))
    return s, float(m[0, 2]) / W, float(m[1, 2]) / H


def analyze(path, out_dir):
    info = probe(path)
    fps = info["fps"] or 30.0
    face_det = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    rows, prev_g, prev_h, last_face, hists = [], None, None, None, []
    for i, img in enumerate(read_frames(path)):
        g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        hist = cv2.calcHist([hsv], [0, 1], None, [30, 16], [0, 180, 0, 256])
        cv2.normalize(hist, hist)
        r = {"frame": i, "t": round(i / fps, 3)}
        if prev_g is None:
            r.update(diff=0.0, hist=0.0, scale=1.0, tx=0.0, ty=0.0)
        else:
            r["diff"] = round(float(np.mean(cv2.absdiff(g, prev_g))), 2)
            r["hist"] = round(float(cv2.compareHist(prev_h, hist, cv2.HISTCMP_BHATTACHARYYA)), 3)
            s, tx, ty = motion(prev_g, g) if r["hist"] < 0.35 else (1.0, 0.0, 0.0)
            r.update(scale=round(s, 4), tx=round(tx, 4), ty=round(ty, 4))
        faces = face_det.detectMultiScale(g, 1.1, 5, minSize=(28, 28))
        if len(faces):
            x, y, w, h = max(faces, key=lambda f: f[2] * f[3])
            last_face = (round((x + w / 2) / W, 3), round((y + h / 2) / H, 3), round(h / H, 3))
            r.update(face_x=last_face[0], face_y=last_face[1], face_h=last_face[2])
        else:
            r.update(face_x="", face_y="", face_h="")
        v = hsv[..., 2].astype(np.float32)
        b, gch, rch = [float(c.mean()) for c in cv2.split(img)]
        r.update(bright=round(float(v.mean()), 1), sat=round(float(hsv[..., 1].mean()), 1),
                 warm=round(rch - b, 1), contrast=round(float(v.std()), 1))
        gm = graphic_mask(img)
        for k in range(BANDS):
            r[f"text_{k:02d}"] = round(float(gm[k * H // BANDS:(k + 1) * H // BANDS].mean()) * 100, 2)
        rows.append(r)
        hists.append(hist)
        prev_g, prev_h = g, hist
    adb = audio_db(path, fps, len(rows)) if info["has_audio"] else [""] * len(rows)
    for r, a in zip(rows, adb):
        r["audio_db"] = a
    # oyna bo'yicha farq: 8 kadr oldingi va 8 kadr keyingi kadr orasida (sekin o'tish - dissolve - shunda ko'rinadi)
    for i, r in enumerate(rows):
        a, b = max(0, i - 8), min(len(rows) - 1, i + 8)
        r["win"] = round(float(cv2.compareHist(hists[a], hists[b], cv2.HISTCMP_BHATTACHARYYA)), 3)
    return rows, fps, info


def detect_cuts(rows, fps=30.0):
    """Kesimlar va o'tishlar turi:
    cut      - qattiq kesim (bitta kadrda gistogramma keskin o'zgaradi)
    dissolve - sekin o'tish (har kadrda farq kichik, lekin 16 kadrlik oynada katta)
    punch    - kadr o'xshash, yuz o'lchami sakraydi (zoom-kesim)
    flash    - kesimda kadr birdan yorqinlashadi
    """
    n, ev = len(rows), []
    for i in range(1, n):
        r, p = rows[i], rows[i - 1]
        if r["hist"] > 0.30 or r["diff"] > 38:
            # qo'shni kadrlar ham o'zgarayotgan bo'lsa - bu qattiq kesim emas, dissolve ichidagi eng keskin kadr
            blend = rows[max(0, i - 2)]["hist"] > 0.1 or rows[min(n - 1, i + 2)]["hist"] > 0.1
            if r["bright"] > p["bright"] + 40 and not blend:
                ev.append([i, "flash"])
            else:
                ev.append([i, "dissolve" if blend else "cut"])
        elif r["face_h"] != "" and p["face_h"] != "" and p["face_h"] > 0:
            ratio = r["face_h"] / p["face_h"]
            if (ratio > 1.10 or ratio < 0.91) and r["diff"] > 6:
                ev.append([i, "punch"])
    # dissolve: oyna farqining lokal cho'qqisi, atrofida qattiq kesim yo'q
    i = 1
    while i < n - 1:
        if rows[i]["win"] > 0.28:
            j = i
            while j < n - 1 and rows[j + 1]["win"] > 0.28:
                j += 1
            seg = range(max(1, i - 2), min(n, j + 3))
            peak_single = max(rows[k]["hist"] for k in seg)
            c = max(range(i, j + 1), key=lambda k: rows[k]["win"])
            if peak_single < 0.30:
                ev.append([c, "dissolve", round((j - i + 1) / fps, 2)])
            else:   # bu oynada qattiq kesim bor - u yerga yaqin kesimlarni dissolve deb belgilash shart emas
                pass
            i = j + 1
        else:
            i += 1
    ev.sort(key=lambda e: e[0])
    out = []
    min_gap = max(4, int(0.3 * fps))
    for e in ev:
        if out and e[0] - out[-1][0] < min_gap:
            # yaqin hodisalar: qattiq kesim > dissolve > punch
            rank = {"flash": 3, "cut": 3, "dissolve": 2, "punch": 1}
            if rank[e[1]] > rank[out[-1][1]]:
                out[-1] = e
            continue
        out.append(e)
    return [tuple(e[:2]) for e in out]


def shot_list(rows, cuts, fps):
    bounds = [0] + [c[0] for c in cuts] + [len(rows)]
    kinds = ["start"] + [c[1] for c in cuts]
    shots = []
    for k in range(len(bounds) - 1):
        a, b = bounds[k], bounds[k + 1]
        seg = rows[a:b]
        fh = [r["face_h"] for r in seg if r["face_h"] != ""]
        fx = [r["face_x"] for r in seg if r["face_x"] != ""]
        fy = [r["face_y"] for r in seg if r["face_y"] != ""]
        zoom = float(np.prod([r["scale"] for r in seg[1:]])) if len(seg) > 1 else 1.0
        pan_x = sum(r["tx"] for r in seg[1:])
        pan_y = sum(r["ty"] for r in seg[1:])
        text = [max(r[f"text_{j:02d}"] for j in range(BANDS)) for r in seg]
        bands = [round(float(np.mean([r[f"text_{j:02d}"] for r in seg])), 2) for j in range(BANDS)]
        shots.append({
            "n": k + 1, "in": kinds[k], "start": round(a / fps, 3), "end": round(b / fps, 3),
            "dur": round((b - a) / fps, 3), "frames": b - a,
            "face_h": round(float(np.median(fh)), 3) if fh else None,
            "face_x": round(float(np.median(fx)), 3) if fx else None,
            "face_y": round(float(np.median(fy)), 3) if fy else None,
            "face_share": round(len(fh) / len(seg), 2),
            "zoom": round(zoom, 3), "pan_x": round(pan_x, 3), "pan_y": round(pan_y, 3),
            "bright": round(float(np.mean([r["bright"] for r in seg])), 1),
            "sat": round(float(np.mean([r["sat"] for r in seg])), 1),
            "warm": round(float(np.mean([r["warm"] for r in seg])), 1),
            "text_peak": round(max(text), 2), "text_bands": bands,
        })
    return shots


def timeline_png(rows, cuts, fps, out):
    n = len(rows)
    px = max(2, 1800 // max(n, 1))
    w = min(n * px, 4000)
    xs = lambda i: int(i * w / n)
    lanes = [("hist", 0, 1.0), ("win", 0, 1.0), ("scale", 0.97, 1.03), ("face_h", 0, 0.6), ("bright", 0, 255),
             ("sat", 0, 255), ("audio_db", -60, 0)]
    lh, top = 90, 24
    img = np.full((top + lh * (len(lanes) + 1) + 20, w + 120, 3), 255, np.uint8)
    for li, (key, lo, hi) in enumerate(lanes):
        y0 = top + li * lh
        cv2.putText(img, key, (w + 6, y0 + 50), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
        cv2.line(img, (0, y0 + lh - 4), (w, y0 + lh - 4), (220, 220, 220), 1)
        pts = []
        for i, r in enumerate(rows):
            v = r.get(key)
            if v == "" or v is None:
                continue
            yy = y0 + lh - 4 - int((min(max(float(v), lo), hi) - lo) / (hi - lo) * (lh - 10))
            pts.append((xs(i), yy))
        for p1, p2 in zip(pts, pts[1:]):
            if p2[0] - p1[0] <= 3 * px:
                cv2.line(img, p1, p2, (40, 40, 200), 1)
    y0 = top + len(lanes) * lh
    cv2.putText(img, "text", (w + 6, y0 + 50), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
    for i, r in enumerate(rows):
        for j in range(BANDS):
            v = min(1.0, r[f"text_{j:02d}"] / 6)
            c = int(255 - 255 * v)
            cv2.rectangle(img, (xs(i), y0 + j * 7), (xs(i + 1), y0 + j * 7 + 6), (c, c, 255), -1)
    col = {"cut": (0, 0, 0), "punch": (0, 160, 0), "flash": (0, 200, 255), "dissolve": (200, 80, 0)}
    for i, k in cuts:
        cv2.line(img, (xs(i), top), (xs(i), img.shape[0] - 20), col[k], 1)
    for s in range(0, int(n / fps) + 1, 5):
        cv2.putText(img, f"{s}s", (xs(s * fps), 16), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 1)
    cv2.imencode(".png", img)[1].tofile(str(out))


def sheets(path, out_dir, fps, sheet_fps, cols=8, rows_n=5):
    """Har 1/sheet_fps s da bitta kadr, kadr raqami va vaqti bilan; 40 tadan jadval."""
    step = max(1, round(fps / sheet_fps))
    cmd = [ffmpeg_exe(), "-nostdin", "-loglevel", "error", "-i", str(path), "-vf",
           f"select='not(mod(n\\,{step}))',scale=180:320", "-vsync", "vfr", "-f", "rawvideo", "-pix_fmt", "bgr24", "-"]
    raw = subprocess.run(cmd, capture_output=True).stdout
    tw, th = 180, 320
    thumbs = [np.frombuffer(raw[k:k + tw * th * 3], np.uint8).reshape(th, tw, 3).copy()
              for k in range(0, len(raw) - tw * th * 3 + 1, tw * th * 3)]
    per = cols * rows_n
    files = []
    for s in range(0, len(thumbs), per):
        grid = np.full((rows_n * (th + 4) + 4, cols * (tw + 4) + 4, 3), 30, np.uint8)
        for k, t in enumerate(thumbs[s:s + per]):
            idx = (s + k) * step
            cv2.putText(t, f"{idx} {idx / fps:.1f}s", (3, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0, 0, 0), 3)
            cv2.putText(t, f"{idx} {idx / fps:.1f}s", (3, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (255, 255, 255), 1)
            y, x = divmod(k, cols)
            grid[4 + y * (th + 4):4 + y * (th + 4) + th, 4 + x * (tw + 4):4 + x * (tw + 4) + tw] = t
        f = out_dir / f"sheet_{s // per + 1:02d}.png"
        cv2.imencode(".png", grid)[1].tofile(str(f))
        files.append(f.name)
    return files


def cut_strips(path, out_dir, cuts, fps, per_sheet=8):
    """Har kesim atrofida 4 kadr (-2, -1, 0, +1): o'tish turini ko'rish uchun."""
    want = {}
    for i, _ in cuts:
        for d in (-2, -1, 0, 1):
            want[i + d] = True
    cmd = [ffmpeg_exe(), "-nostdin", "-loglevel", "error", "-i", str(path), "-vf", "scale=150:266",
           "-f", "rawvideo", "-pix_fmt", "bgr24", "-"]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    tw, th, got, k = 150, 266, {}, 0
    while True:
        buf = p.stdout.read(tw * th * 3)
        if len(buf) < tw * th * 3:
            break
        if k in want:
            got[k] = np.frombuffer(buf, np.uint8).reshape(th, tw, 3).copy()
        k += 1
    p.wait()
    files = []
    for s in range(0, len(cuts), per_sheet):
        chunk = cuts[s:s + per_sheet]
        grid = np.full((len(chunk) * (th + 4) + 4, 4 * (tw + 4) + 4, 3), 30, np.uint8)
        for ri, (i, kind) in enumerate(chunk):
            for ci, d in enumerate((-2, -1, 0, 1)):
                t = got.get(i + d)
                if t is None:
                    continue
                if d == 0:
                    cv2.putText(t, f"{kind} {i}", (3, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0, 0, 0), 3)
                    cv2.putText(t, f"{kind} {i}", (3, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0, 255, 255), 1)
                y, x = 4 + ri * (th + 4), 4 + ci * (tw + 4)
                grid[y:y + th, x:x + tw] = t
        f = out_dir / f"cuts_{s // per_sheet + 1:02d}.png"
        cv2.imencode(".png", grid)[1].tofile(str(f))
        files.append(f.name)
    return files


def summary(shots, rows, fps, info):
    durs = [s["dur"] for s in shots]
    fh = [s["face_h"] for s in shots if s["face_h"]]
    kinds = {}
    for s in shots[1:]:
        kinds[s["in"]] = kinds.get(s["in"], 0) + 1
    zooms = [s["zoom"] for s in shots if s["dur"] >= 0.8]
    adb = [r["audio_db"] for r in rows if r["audio_db"] != ""]
    return {
        "duration": round(info["duration"], 2), "fps": fps, "frames": len(rows), "shots": len(shots),
        "transitions": kinds,
        "shot_s": {"avg": round(float(np.mean(durs)), 2), "median": round(float(np.median(durs)), 2),
                   "min": round(min(durs), 2), "max": round(max(durs), 2)},
        "cuts_per_10s": round((len(shots) - 1) / info["duration"] * 10, 1),
        "face_h": {"min": min(fh), "median": round(float(np.median(fh)), 3), "max": max(fh)} if fh else None,
        "zoom_in_shots": sum(z > 1.03 for z in zooms), "zoom_out_shots": sum(z < 0.97 for z in zooms),
        "static_shots": sum(0.97 <= z <= 1.03 for z in zooms),
        "bright_avg": round(float(np.mean([r["bright"] for r in rows])), 1),
        "sat_avg": round(float(np.mean([r["sat"] for r in rows])), 1),
        "warm_avg": round(float(np.mean([r["warm"] for r in rows])), 1),
        "text_frames_share": round(float(np.mean([max(r[f"text_{j:02d}"] for j in range(BANDS)) > 1.5 for r in rows])), 2),
        "text_band_avg": [round(float(np.mean([r[f"text_{j:02d}"] for r in rows])), 2) for j in range(BANDS)],
        "audio_db_median": round(float(np.median(adb)), 1) if adb else None,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("--name", default=None)
    ap.add_argument("--sheet-fps", type=float, default=5.0, help="Jadvaldagi kadrlar soni soniyasiga")
    args = ap.parse_args()
    path = resolve(args.video)
    name = args.name or path.stem
    out_dir = ROOT / "work" / "reference" / name / "frames"
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"Kadrlar o'qilmoqda: {path.name}", flush=True)
    rows, fps, info = analyze(path, out_dir)
    with open(out_dir / "frames.csv", "w", newline="", encoding="utf-8") as f:
        wr = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        wr.writeheader()
        wr.writerows(rows)
    cuts = detect_cuts(rows, fps)
    shots = shot_list(rows, cuts, fps)
    timeline_png(rows, cuts, fps, out_dir / "timeline.png")
    sh = sheets(path, out_dir, fps, args.sheet_fps)
    cs = cut_strips(path, out_dir, cuts, fps)
    summ = summary(shots, rows, fps, info)
    json.dump({"summary": summ, "shots": shots, "sheets": sh, "cut_sheets": cs}, open(out_dir / "shots.json", "w",
              encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(summ, ensure_ascii=False, indent=1))
    print(f"\n{len(rows)} kadr, {len(shots)} plan. Natija: {out_dir}")


if __name__ == "__main__":
    main()
