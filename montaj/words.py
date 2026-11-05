"""Transkriptdagi so'zlarni indeks, vaqt va ishonch darajasi bilan chiqaradi (tuzatish uchun).

Misol:
    python montaj/words.py work/video/transcript.json
    python montaj/words.py work/video/transcript.json --from 10 --to 25

Ishonchi past (prob < 0.6) yoki 1.5 s dan uzun so'zlar "!" bilan belgilanadi - ularni tekshiring.
"""
import argparse

from common import load_json, resolve


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("transcript")
    ap.add_argument("--from", dest="t_from", type=float, default=0.0)
    ap.add_argument("--to", dest="t_to", type=float, default=1e9)
    args = ap.parse_args()

    tr = load_json(resolve(args.transcript))
    for si, seg in enumerate(tr["segments"]):
        for wi, w in enumerate(seg["words"]):
            if not (args.t_from <= w["start"] <= args.t_to):
                continue
            flag = "!" if w.get("prob", 1) < 0.6 or w["end"] - w["start"] > 1.5 else " "
            print(f"{flag} [{si}][{wi}] {w['start']:7.2f}-{w['end']:7.2f}  p={w.get('prob', 1):.2f}  {w['word']}")


if __name__ == "__main__":
    main()
