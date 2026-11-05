"""Transkript asosida boshlang'ich montaj rejasini (edit.json) tuzadi:
jimliklar va "ee/mm" kabi parazit so'zlar kesiladi, har bir bo'lakka navbatma-navbat zoom beriladi.

Misol:
    python montaj/autocut.py work/video/transcript.json --format 9:16 --style pop

Natija: work/<video_nomi>/edit.json - uni Claude yoki siz qo'lda tahrirlashingiz mumkin.
"""
import argparse
import re

from common import ROOT, all_words, fmt_time, load_json, resolve, save_json

FILLERS = {"e", "ee", "eee", "eeee", "a", "aa", "aaa", "m", "mm", "mmm", "hmm", "xmm", "ım", "uh", "um"}


def norm(word: str) -> str:
    return re.sub(r"[^\w']", "", word.lower())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("transcript")
    ap.add_argument("--format", default="9:16", choices=["9:16", "16:9", "1:1", "4:5", "original"])
    ap.add_argument("--style", default="pop", help="styles/subtitles.json dagi uslub nomi yoki 'none'")
    ap.add_argument("--max-gap", type=float, default=0.35, help="Shundan uzun jimlik kesiladi (s)")
    ap.add_argument("--pad", type=float, default=0.08, help="Har bo'lak atrofida qoldiriladigan zaxira (s)")
    ap.add_argument("--keep-fillers", action="store_true")
    ap.add_argument("--zoom", type=float, default=1.12, help="Navbatma-navbat zoom (1 = o'chirilgan)")
    ap.add_argument("--min-seg", type=float, default=1.2, help="Shundan qisqa bo'laklarga zoom berilmaydi")
    args = ap.parse_args()

    tpath = resolve(args.transcript)
    tr = load_json(tpath)
    words = [w for w in all_words(tr) if args.keep_fillers or norm(w["word"]) not in FILLERS]
    if not words:
        raise SystemExit("Transkriptda so'z topilmadi.")

    segs = []
    for w in words:
        s, e = max(0.0, w["start"] - args.pad), min(tr["duration"], w["end"] + args.pad)
        if segs and s - segs[-1]["end"] <= args.max_gap:
            segs[-1]["end"] = max(segs[-1]["end"], e)
        else:
            segs.append({"start": s, "end": e})

    zoomed = False
    for seg in segs:
        seg["start"], seg["end"] = round(seg["start"], 3), round(seg["end"], 3)
        seg["zoom"] = 1.0
        if args.zoom > 1 and seg["end"] - seg["start"] >= args.min_seg:
            seg["zoom"] = args.zoom if zoomed is False else 1.0
            zoomed = not zoomed
        seg["x"], seg["y"] = 0.5, 0.5

    name = tpath.parent.name
    edit = {
        "source": tr["source"],
        "transcript": str(tpath.relative_to(ROOT)) if tpath.is_relative_to(ROOT) else str(tpath),
        "output": f"output/{name}.mp4",
        "format": args.format,
        "segments": segs,
        "subtitles": None if args.style == "none" else {"style": args.style},
        "title": None,
        "music": None,
        "sfx": [],
        "audio": {"denoise": True, "loudnorm": True},
    }
    out = tpath.parent / "edit.json"
    save_json(edit, out)

    kept = sum(s["end"] - s["start"] for s in segs)
    print(f"{len(segs)} ta bo'lak, {fmt_time(tr['duration'])} -> {fmt_time(kept)} "
          f"({100 * kept / max(tr['duration'], 0.01):.0f}%)")
    print(f"Reja: {out}")


if __name__ == "__main__":
    main()
