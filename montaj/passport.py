"""Uslub pasportlari: montajning to'liq uslubi (subtitr, rang, ritm, zoom, SFX, animatsiya, musiqa).

Misol:
    python montaj/passport.py --list                              # barcha pasportlar
    python montaj/passport.py --show hormozi                      # to'liq pasport va yo'riqnoma
    python montaj/passport.py --apply hormozi work/video/edit.json

--apply nima qiladi:
    - subtitr, rang (grade), mavzu ranglari (theme) ni o'rnatadi;
    - max_shot_s dan uzun bo'laklarni so'zlar orasidagi eng katta pauzalardan bo'ladi;
    - zoom_pattern ni bo'laklarga navbatma-navbat beradi va yuzni avtomatik kadrlaydi (reframe);
    - progress-bar va musiqa sozlamalarini qo'shadi;
    - Claude uchun SFX palitrasi va animatsiya yo'riqnomasini chiqaradi (ularni Claude o'zi joylaydi).

O'rnatilgan pasportlar: styles/passports.json. O'rganilgan/o'zingiznikilar: styles/passports/<nom>.json
"""
import argparse
import json
import math

from common import ROOT, all_words, load_json, resolve, save_json

BUILTIN = ROOT / "styles" / "passports.json"
CUSTOM = ROOT / "styles" / "passports"


def load_all():
    data = dict(load_json(BUILTIN))
    if CUSTOM.exists():
        for f in sorted(CUSTOM.glob("*.json")):
            data[f.stem] = load_json(f)
    return data


def split_segments(segments, words, max_shot):
    """Uzun bo'laklarni so'zlar orasidagi eng katta pauzalardan teng bo'laklarga ajratadi."""
    out = []
    for seg in segments:
        s, e = float(seg["start"]), float(seg["end"])
        parts = math.ceil((e - s) / max_shot)
        inner = [w for w in words if s <= (w["start"] + w["end"]) / 2 <= e]
        if parts <= 1 or len(inner) < 2:
            out.append(dict(seg))
            continue
        gaps = [((a["end"] + b["start"]) / 2, b["start"] - a["end"]) for a, b in zip(inner, inner[1:])]
        cuts = []
        for k in range(1, parts):
            target = s + (e - s) * k / parts
            # maqsadga yaqin (+-35%) oraliqdagi eng katta pauza
            window = [g for g in gaps if abs(g[0] - target) <= (e - s) / parts * 0.35 and g[0] not in cuts]
            if window:
                cuts.append(max(window, key=lambda g: g[1])[0])
        bounds = [s] + sorted(cuts) + [e]
        for a, b in zip(bounds, bounds[1:]):
            piece = {k: v for k, v in seg.items() if k not in ("start", "end")}
            out.append({**piece, "start": round(a, 3), "end": round(b, 3)})
    return out


def apply(name, edit_path, reframe_faces=True):
    pp = load_all()
    if name not in pp:
        raise SystemExit(f"Pasport topilmadi: {name}. Mavjud: {', '.join(pp)}")
    p = pp[name]
    edit = load_json(edit_path)
    words = all_words(load_json(resolve(edit["transcript"])))

    pacing = p.get("pacing", {})
    if pacing.get("max_shot_s"):
        edit["segments"] = split_segments(edit["segments"], words, float(pacing["max_shot_s"]))
    pattern = pacing.get("zoom_pattern") or [1.0]
    for i, seg in enumerate(edit["segments"]):
        seg["zoom"] = pattern[i % len(pattern)]
    if reframe_faces:
        import reframe
        print("Yuzlar bo'yicha kadrlash:")
        reframe.reframe(edit)

    edit["subtitles"] = dict(p["subtitles"]) if p.get("subtitles") else None
    edit["grade"] = p.get("grade")
    edit["theme"] = p.get("theme")
    edit["passport"] = name
    anims = [a for a in (edit.get("animations") or []) if a.get("type") != "progress"]
    if p.get("progress_bar"):
        anims.insert(0, {"type": "progress", "position": "top"})
    edit["animations"] = anims
    if edit.get("music") and edit["music"].get("file"):
        edit["music"].setdefault("volume", p.get("music", {}).get("volume", 0.1))
        edit["music"].setdefault("sync", p.get("music", {}).get("sync", False))
    save_json(edit, edit_path)

    print(f"\n'{name}' qo'llandi: {len(edit['segments'])} ta bo'lak, zoom {pattern}, "
          f"subtitr {p['subtitles'].get('style') if p.get('subtitles') else '-'}, rang {p.get('grade')}")
    print("\nSFX palitrasi (assets/sfx/ ga nisbatan):")
    for k, v in (p.get("sfx") or {}).items():
        print(f"  {k}: {v}")
    print(f"\nMusiqa: {p.get('music', {}).get('mood', '-')}")
    print(f"\nYo'riqnoma: {p.get('guide', '')}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--show")
    ap.add_argument("--apply", nargs=2, metavar=("PASPORT", "EDIT_JSON"))
    ap.add_argument("--no-reframe", action="store_true")
    args = ap.parse_args()
    if args.list:
        for k, v in load_all().items():
            print(f"{k:18s} {v.get('description', '')}\n{'':18s} -> {', '.join(v.get('best_for', []))}")
    if args.show:
        print(json.dumps(load_all()[args.show], ensure_ascii=False, indent=2))
    if args.apply:
        apply(args.apply[0], resolve(args.apply[1]), not args.no_reframe)


if __name__ == "__main__":
    main()
