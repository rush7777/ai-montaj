"""Musiqaning tempi va bitlarini aniqlaydi (librosa). Natija musiqa yonida <nom>.beats.json bo'lib saqlanadi.

Misol:
    python montaj/beats.py assets/music/trek.mp3

render.py uni avtomatik ishlatadi: edit.json da "music": {"sync": true} bo'lsa, musiqa shunday
siljitiladiki, bo'laklar orasidagi kesimlar bitga tushadi; "snap_sfx": true SFX'larni eng yaqin bitga suradi.
"""
import argparse
import os
from pathlib import Path

from common import load_json, resolve, save_json


def cache_path(music: Path) -> Path:
    return music.with_name(music.name + ".beats.json")


def analyze(music: Path) -> dict:
    cache = cache_path(music)
    if cache.exists() and cache.stat().st_mtime >= music.stat().st_mtime:
        return load_json(cache)
    import librosa
    import numpy as np

    y, sr = librosa.load(str(music), sr=22050, mono=True)
    tempo, frames = librosa.beat.beat_track(y=y, sr=sr, units="frames")
    beats = librosa.frames_to_time(frames, sr=sr)
    onset = librosa.onset.onset_strength(y=y, sr=sr)
    strength = onset[np.clip(frames, 0, len(onset) - 1)] if len(frames) else np.array([])
    # kuchli bit (taktning birinchisi): 4 ta fazadan eng kuchlisi
    phase = int(np.argmax([strength[i::4].mean() if len(strength[i::4]) else 0 for i in range(4)])) if len(strength) else 0
    data = {
        "file": music.name,
        "duration": round(float(len(y) / sr), 3),
        "tempo": round(float(np.atleast_1d(tempo)[0]), 1),
        "beats": [round(float(b), 3) for b in beats],
        "downbeats": [round(float(b), 3) for b in beats[phase::4]],
    }
    save_json(data, cache)
    return data


def best_offset(beats, cuts, music_dur, video_dur, tol=0.06):
    """Musiqa qaysi joyidan boshlansa, ko'proq kesim bitga tushadi."""
    if not beats or not cuts:
        return 0.0, 0
    best = (0.0, -1)
    for b in beats:
        for c in cuts[:3]:
            off = round(b - c, 3)
            if off < 0 or off + video_dur > music_dur:
                continue
            hits = sum(any(abs(x + off - bb) <= tol for bb in beats) for x in cuts)
            if hits > best[1] or (hits == best[1] and off < best[0]):
                best = (off, hits)
    return best if best[1] >= 0 else (0.0, 0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("music")
    args = ap.parse_args()
    os.environ.setdefault("NUMBA_CACHE_DIR", str(Path.home() / ".ai-montaj" / "numba"))
    d = analyze(resolve(args.music))
    print(f"{d['file']}: {d['tempo']} BPM, {len(d['beats'])} bit, {d['duration']} s")
    print("Birinchi kuchli bitlar:", ", ".join(f"{b:.2f}" for b in d["downbeats"][:12]))


if __name__ == "__main__":
    main()
