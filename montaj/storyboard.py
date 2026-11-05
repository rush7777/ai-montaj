"""Storyboard: render qilishdan OLDIN montaj rejasini bitta HTML sahifada ko'rsatadi - har bir sahna eskizi
(kesish, zoom, kamera harakati, rang va HyperFrames animatsiyasi bilan), vaqti, aytilgan gap, ekrandagi matnlar,
o'tishlar, SFX va ogohlantirishlar. Foydalanuvchi tasdiqlamaguncha yakuniy render qilinmaydi.

Misol:
    python montaj/storyboard.py work/video/edit.json            # -> work/video/storyboard.html
    python montaj/storyboard.py work/video/pro.edit.json --no-anim   # animatsiya eskizlarisiz (tezroq)
"""
import argparse
import base64
import html
import re
import shutil
from pathlib import Path

from common import fmt_time, resolve, run_ffmpeg

import render

THUMB_W = 300


def esc(s):
    return html.escape(str(s), quote=True)


def thumb_times(seg):
    """Sahna ichida eskiz olinadigan nisbiy vaqtlar (harakat bo'lsa - boshi va eng yaqin nuqtasi)."""
    d, mv = seg["dur"], seg.get("move")
    if mv and mv.get("type") == "punch":
        at = min(float(mv.get("at", 0)), d - 0.05)
        return [max(0.05, at - 0.1), min(d - 0.03, at + float(mv.get("in", 0.2)) + 0.05)]
    if mv:
        return [0.05, max(0.06, d - 0.08)]
    return [d / 2]


def anim_brief(a):
    t = a["type"]
    if t == "remotion":
        p = a.get("props") or {}
        main = p.get("text") or p.get("title") or ""
        return f"remotion {a['comp']}: {str(main).replace(chr(10), ' / ')}".rstrip(": ")
    for k in ("text", "title", "label", "emoji", "shape"):
        if a.get(k):
            return f"{t}: {str(a[k]).replace(chr(10), ' / ')}"
    if t == "list":
        return f"list: {' | '.join(a['items'])}"
    if t == "counter":
        return f"counter: {a.get('prefix', '')}{a['to']}{a.get('suffix', '')}"
    return t


def build(edit_path, with_anim=True):
    P = render.prepare(edit_path)
    F, edit, src, info, fps = P["F"], P["edit"], P["src"], P["info"], P["fps"]
    segs, words, total, beats = P["segs"], P["words"], P["total"], P["beats"]
    out_dir = F["work"] / f"{F['tag']}storyboard"
    shutil.rmtree(out_dir, ignore_errors=True)
    out_dir.mkdir()

    shots = [(seg, t) for seg in segs for t in thumb_times(seg)]
    snaps = None
    anims = edit.get("animations") or []
    if with_anim and anims:
        import animate
        times = sorted({round(seg["offset"] + t, 2) for seg, t in shots})
        files = animate.build(edit_path, snapshot=times) or []
        at = {float(m.group(1)): f for f in files if (m := re.search(r"-at-([\d.]+)s\.png$", f.name))}
        snaps = {t: at[min(at, key=lambda x: abs(x - t))] for t in times
                 if at and abs(min(at, key=lambda x: abs(x - t)) - t) < 0.02} or None
        if not snaps and any(a.get("type") != "remotion" for a in anims):
            print("Ogohlantirish: animatsiya eskizlari olinmadi - eskizlar animatsiyasiz.")
    # Remotion klip(lar)i: yakuniy render ham shu keshdan foydalanadi
    rem = []
    if with_anim and any(a.get("type") == "remotion" for a in anims):
        import remotion_layer
        rem = remotion_layer.build(edit_path)

    grade = render.grade_filter(edit.get("grade"))
    fade = edit.get("fade") or {}
    fade = {"out": float(fade)} if isinstance(fade, (int, float)) else fade
    thumbs = {}
    for k, (seg, t) in enumerate(shots):
        vf = render.frame_filter(seg, info, P["aspect"], P["OW"], P["OH"], fps, at=t)
        if grade:
            vf += "," + grade
        dst = out_dir / f"s{seg['index']:02d}_{k}.jpg"
        snap = snaps.get(round(seg["offset"] + t, 2)) if snaps else None
        inputs = ["-ss", f"{seg['start'] + t:.3f}", "-i", src]
        layers = [["-i", snap]] if snap else []
        ot = seg["offset"] + t
        layers += [["-ss", f"{ot - r0:.3f}", "-i", mov] for mov, r0, r1 in rem if r0 <= ot < r1]
        # -ss dan keyin kirishlar 0 dan boshlanmasligi mumkin - overlay qatlamni tashlab ketmasin
        fc, lbl = f"[0:v]setpts=PTS-STARTPTS,{vf}[b0]", "[b0]"
        for n, extra in enumerate(layers, 1):
            inputs += extra
            fc += f";[{n}:v]setpts=PTS-STARTPTS,scale={P['OW']}:{P['OH']}[o{n}];{lbl}[o{n}]overlay=0:0[b{n}]"
            lbl = f"[b{n}]"
        fc += f";{lbl}scale={THUMB_W}:-2[v]"
        run_ffmpeg(inputs + ["-filter_complex", fc, "-map", "[v]", "-frames:v", 1, "-q:v", 4, dst])
        thumbs.setdefault(seg["index"], []).append((round(seg["offset"] + t, 2), dst))

    # ogohlantirishlar
    warns = []
    pp = edit.get("passport")
    max_shot = None
    if pp:
        import passport
        max_shot = passport.load_all().get(pp, {}).get("pacing", {}).get("max_shot_s")
    limit = (max_shot or 4.5) * 1.6
    for seg in segs:
        if seg["dur"] > limit and not seg.get("move"):
            warns.append(f"Sahna {seg['index'] + 1}: {seg['dur']:.1f} s harakatsiz - `move` (kenburns/punch) qo'shing")
        if seg["_tr"] and seg["dur"] < seg["_tr"]["dur"] * 2:
            warns.append(f"Sahna {seg['index'] + 1}: o'tish ({seg['_tr']['dur']:.2f} s) sahnaga nisbatan uzun")
        mv = seg.get("move")
        if mv and mv.get("type") == "punch" and float(mv.get("at", 0)) >= seg["dur"]:
            warns.append(f"Sahna {seg['index'] + 1}: punch vaqti ({mv['at']} s) sahnadan tashqarida")
    kinds = {s["_tr"]["type"] for s in segs if s["_tr"]}
    if len(kinds) > 2:
        warns.append(f"{len(kinds)} xil o'tish ({', '.join(sorted(kinds))}) - ko'pi bilan 2 xil tavsiya etiladi")
    f_out = float(fade.get("out", 0))
    if f_out and fade.get("audio", True) and words and words[-1]["end"] > total - f_out + 0.1:
        warns.append(f"Oxirgi so'z \"{words[-1]['word']}\" fade-out ichida ({f_out} s) - ovoz pasayib ketadi")
    for t in [seg["offset"] + x for seg in segs for x in (0.1, seg["dur"] / 2)]:
        live = [a for a in anims if a.get("type") != "progress" and float(a.get("start", 0)) <= t < float(a.get("end", 0))]
        if len(live) > 2:
            warns.append(f"{t:.1f} s da {len(live)} ta animatsiya bir vaqtda - ko'pi bilan 2 ta")
            break

    beat_list = beats["beats"] if beats else []
    cards = []
    for seg in segs:
        i = seg["index"]
        a0, a1 = seg["offset"], seg["offset"] + seg["dur"]
        said = " ".join(w["word"] for w in words if w["seg"] == i)
        chips = [f"zoom {seg.get('zoom', 1)}"]
        if seg.get("move"):
            chips.append("🎥 " + render.move_label(seg["move"]))
        if seg["_tr"]:
            chips.append(f"↔ {seg['_tr']['type']} {seg['_tr']['dur']:.2f} s")
        if i and beat_list and min(abs(b - a0) for b in beat_list) <= 0.06:
            chips.append("♪ kesim bitda")
        on = [anim_brief(a) + f" ({float(a.get('start', 0)):.1f}-{float(a.get('end', 0)):.1f})"
              for a in anims if float(a.get("start", 0)) < a1 and float(a.get("end", total)) > a0]
        fx = [f"{Path(s['file']).stem} @{float(s['at']):.2f}" for s in edit.get("sfx") or [] if a0 <= float(s["at"]) < a1]
        imgs = "".join(
            f'<figure><img src="data:image/jpeg;base64,{base64.b64encode(p.read_bytes()).decode()}" alt="">'
            f'<figcaption>{fmt_time(tt)}</figcaption></figure>' for tt, p in thumbs[i])
        rows = f'<p class="said">“{esc(said) or "—"}”</p>'
        if on:
            rows += '<p class="lbl">Ekranda</p><ul>' + "".join(f"<li>{esc(x)}</li>" for x in on) + "</ul>"
        if fx:
            rows += f'<p class="lbl">SFX</p><p>{esc(", ".join(fx))}</p>'
        cards.append(f'<article><header><b>{i + 1}</b><span>{fmt_time(a0)} – {fmt_time(a1)} · {seg["dur"]:.2f} s</span>'
                     f'<small>manba {seg["start"]:.2f}–{seg["end"]:.2f}</small></header><div class="imgs">{imgs}</div>'
                     f'<div class="chips">{"".join(f"<i>{esc(c)}</i>" for c in chips)}</div>{rows}</article>')

    music = P["music"]
    meta = [("Davomiylik", f"{fmt_time(total)} ({total:.1f} s), {len(segs)} sahna"),
            ("Format", f"{edit.get('format', '9:16')} · {P['OW']}x{P['OH']} · {fps} fps"),
            ("Pasport", pp or "—"), ("Rang", str(edit.get("grade") or "—")),
            ("Subtitr", (edit.get("subtitles") or {}).get("style", "yo'q") if edit.get("subtitles") else "yo'q"),
            ("Musiqa", f"{Path(music['file']).name}, volume {music.get('volume', 0.25)}"
                       + (f", {beats['tempo']} BPM, {beats['hits']}/{beats['cuts']} kesim bitda"
                          if beats and beats.get("hits") is not None else "") if music else "yo'q"),
            ("O'tishlar", ", ".join(f"{s['index'] + 1}: {s['_tr']['type']}" for s in segs if s["_tr"]) or "hard cut"),
            ("Fade", ", ".join(f"{k} {v} s" for k, v in fade.items() if k in ("in", "out")) or "yo'q"),
            ("SFX", f"{len(edit.get('sfx') or [])} ta"), ("Animatsiya", f"{len(anims)} blok")]
    warn_html = ("<section class='warn'><h2>Ogohlantirishlar</h2><ul>" + "".join(f"<li>{esc(w)}</li>" for w in warns)
                 + "</ul></section>") if warns else "<section class='ok'>Ogohlantirish yo'q.</section>"
    name = edit_path.name.replace(".edit.json", "").replace(".json", "")
    page = f"""<!doctype html>
<html lang="uz"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Storyboard {esc(name)}</title>
<style>
:root{{--bg:#f6f5f2;--card:#fff;--ink:#1b1b1b;--mut:#6b6b6b;--line:#e3e1dc;--acc:#e8620c;--warn:#fff4e5}}
@media (prefers-color-scheme:dark){{:root{{--bg:#151515;--card:#1f1f1f;--ink:#eee;--mut:#9a9a9a;--line:#333;--acc:#ff8a3d;--warn:#3a2a14}}}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font:15px/1.45 system-ui,Segoe UI,sans-serif}}
main{{max-width:1280px;margin:0 auto;padding:24px 16px 60px}}h1{{margin:0 0 4px;font-size:26px}}
.sub{{color:var(--mut);margin:0 0 18px}}dl{{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:8px 18px;margin:0 0 18px}}
dt{{color:var(--mut);font-size:12px;text-transform:uppercase;letter-spacing:.04em}}dd{{margin:0}}
.warn,.ok{{border-radius:10px;padding:10px 16px;margin:0 0 20px;background:var(--warn)}}.ok{{background:var(--card)}}
.warn h2{{font-size:15px;margin:4px 0}}.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:16px}}
article{{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:12px}}
article header{{display:flex;gap:10px;align-items:baseline;flex-wrap:wrap}}article header b{{background:var(--acc);color:#fff;border-radius:6px;padding:0 8px}}
article small{{color:var(--mut)}}.imgs{{display:flex;gap:6px;margin:10px 0}}figure{{margin:0;flex:1;min-width:0}}
img{{width:100%;border-radius:8px;display:block;aspect-ratio:{P['OW']}/{P['OH']};object-fit:cover;background:#000}}
figcaption{{font-size:12px;color:var(--mut);text-align:center}}.chips{{display:flex;gap:6px;flex-wrap:wrap}}
.chips i{{font-style:normal;font-size:12px;border:1px solid var(--line);border-radius:99px;padding:1px 8px}}
.said{{margin:10px 0 6px}}.lbl{{margin:8px 0 2px;font-size:12px;color:var(--mut);text-transform:uppercase}}
ul{{margin:0;padding-left:18px}}
</style></head><body><main>
<h1>Storyboard: {esc(name)}</h1>
<p class="sub">Render qilishdan oldingi reja. Tasdiqlang yoki o'zgartirishni yozing (masalan: "3-sahnaga punch-in", "2-o'tishni olib tashla").
Subtitrlar eskizlarda ko'rinmaydi.</p>
<dl>{"".join(f"<div><dt>{esc(k)}</dt><dd>{esc(v)}</dd></div>" for k, v in meta)}</dl>
{warn_html}
<div class="grid">{"".join(cards)}</div>
</main></body></html>"""
    out = F["work"] / f"{F['tag']}storyboard.html"
    out.write_text(page, encoding="utf-8")
    print(f"\nStoryboard: {out}")
    for w in warns:
        print("  ! " + w)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("edit")
    ap.add_argument("--no-anim", action="store_true", help="Animatsiya qatlamisiz eskizlar (tezroq)")
    args = ap.parse_args()
    build(resolve(args.edit), with_anim=not args.no_anim)


if __name__ == "__main__":
    main()
