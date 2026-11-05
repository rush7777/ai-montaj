"""SFX kutubxonasi katalogi: assets/sfx/ ichidagi barcha ovozlar teglar, davomiylik va balandlik bilan.

Misol:
    python montaj/sfx_catalog.py --build            # katalogni qayta yig'ish (yangi fayl qo'shgandan keyin)
    python montaj/sfx_catalog.py --find money       # teg yoki nom bo'yicha qidirish
    python montaj/sfx_catalog.py --find impact heavy
    python montaj/sfx_catalog.py --tags             # barcha teglar va soni

O'z ovozlaringizni assets/sfx/custom/ ga qo'ying va --build qiling.
"""
import argparse
import re
import subprocess
from collections import Counter

from common import ROOT, ffmpeg_exe, load_json, save_json

SFX = ROOT / "assets" / "sfx"
CATALOG = SFX / "catalog.json"

TAG_RULES = [
    (r"whoosh|swoosh|swipe|card-slide|card-shove", ["transition", "whoosh"]),
    (r"rise|riser|swell|powerup|phaserup|highup|zapthreetoneup", ["riser", "build-up"]),
    (r"boom|sub_drop|bass_hit", ["impact", "boom", "deep"]),
    (r"punch|impactpunch", ["impact", "punch"]),
    (r"impact", ["impact"]),
    (r"heavy", ["heavy"]),
    (r"light", ["light"]),
    (r"pop|bubble|pepsound", ["pop", "emphasis"]),
    (r"click|tick|switch|select|toggle|mouse|rollover|typewriter", ["click", "ui"]),
    (r"ding|notification|success|confirmation|bong|twotone|threetone|^tone|pluck|glass_", ["ding", "positive"]),
    (r"notification", ["notification"]),
    (r"error|question|lowdown|phaserdown|zapthreetonedown|highdown", ["negative"]),
    (r"kaching|coin|chip", ["money"]),
    (r"card|cards", ["paper"]),
    (r"glitch|laser|spacetrash|zap|phasejump|lowrandom", ["glitch", "digital"]),
    (r"glass", ["glass"]),
    (r"dice", ["shake"]),
    (r"camera", ["camera"]),
    (r"heartbeat", ["tension"]),
    (r"tape_stop|scratch", ["stop"]),
    (r"footstep", ["footstep"]),
    (r"open|close|maximize|minimize|scroll|drop|back", ["ui"]),
    (r"typewriter|tick", ["typing"]),
]


def analyze(path):
    res = subprocess.run([ffmpeg_exe(), "-hide_banner", "-nostats", "-i", str(path), "-af", "volumedetect",
                          "-f", "null", "-"], capture_output=True, text=True, encoding="utf-8", errors="replace")
    dur = re.search(r"Duration: (\d+):(\d+):([\d.]+)", res.stderr)
    peak = re.search(r"max_volume: (-?[\d.]+) dB", res.stderr)
    seconds = int(dur.group(1)) * 3600 + int(dur.group(2)) * 60 + float(dur.group(3)) if dur else 0.0
    return round(seconds, 2), float(peak.group(1)) if peak else 0.0


def build():
    items = []
    files = sorted(p for p in SFX.rglob("*") if p.suffix.lower() in (".wav", ".ogg", ".mp3", ".flac"))
    for i, p in enumerate(files, 1):
        rel = p.relative_to(ROOT).as_posix()
        name = p.stem.lower()
        tags = {p.parent.name}
        for pattern, add in TAG_RULES:
            if re.search(pattern, name):
                tags.update(add)
        dur, peak = analyze(p)
        tags.add("short" if dur < 0.4 else "long" if dur > 1.2 else "medium")
        items.append({"file": rel, "name": p.stem, "tags": sorted(tags), "duration": dur, "peak_db": peak})
        if i % 50 == 0:
            print(f"  {i}/{len(files)}", flush=True)
    save_json({"count": len(items), "sounds": items}, CATALOG)
    print(f"Katalog: {len(items)} ta ovoz -> {CATALOG}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--build", action="store_true")
    ap.add_argument("--find", nargs="+")
    ap.add_argument("--tags", action="store_true")
    ap.add_argument("--limit", type=int, default=25)
    args = ap.parse_args()

    if args.build or not CATALOG.exists():
        build()
    cat = load_json(CATALOG)["sounds"]
    if args.tags:
        for tag, n in Counter(t for s in cat for t in s["tags"]).most_common():
            print(f"{n:4d}  {tag}")
    if args.find:
        terms = [t.lower() for t in args.find]
        hits = [s for s in cat if all(any(t in x for x in s["tags"] + [s["name"].lower()]) for t in terms)]
        for s in hits[:args.limit]:
            print(f"{s['file']:60s} {s['duration']:5.2f}s  {', '.join(s['tags'])}")
        print(f"({len(hits)} ta topildi)")


if __name__ == "__main__":
    main()
