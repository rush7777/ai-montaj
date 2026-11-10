"""edit.json asosida tayyor videoni yig'adi.

1-bosqich: har bir bo'lak alohida kesiladi, kadr formatiga (9:16 va h.k.) moslanadi, zoom va kamera harakati
(punch-in, Ken Burns) beriladi.
O'tishlar bo'lsa: bo'laklar crossfade/zoom/dip bilan bitta video oqimiga yig'iladi (vaqt jadvali siljimaydi).
2-bosqich: bo'laklar ulanadi, rang korreksiyasi, HyperFrames animatsiya qatlami, subtitr va sarlavha, boshi/oxirida
fade; ovoz tozalanadi, musiqa (bitga moslab) va SFX (balandligi tenglashtirilgan) qo'shiladi.

Misol:
    python montaj/render.py work/video/edit.json
    python montaj/render.py work/video/edit.json --timeline-only   # faqat yangi vaqt jadvali
    python montaj/render.py work/video/edit.json --preview         # tez, past sifat

Yonida work/<nom>/timeline.txt paydo bo'ladi: so'zlarning TAYYOR videodagi vaqtlari
(SFX, sarlavha, animatsiya va musiqa vaqtini shunga qarab qo'yish kerak).
"""
import argparse
import os
import re
import shutil
import time
from pathlib import Path

from common import ROOT, all_words, edit_files, fmt_time, load_json, probe, resolve, run_ffmpeg, save_json

OUT_SIZES = {"9:16": (1080, 1920), "16:9": (1920, 1080), "1:1": (1080, 1080), "4:5": (1080, 1350)}

GRADES = {
    "clean": "eq=contrast=1.04:saturation=1.08",
    "punchy": "eq=contrast=1.1:saturation=1.28:brightness=0.01,unsharp=5:5:0.4",
    "warm": "colorbalance=rs=0.05:bs=-0.05:rm=0.04:bm=-0.04:rh=0.03:bh=-0.03,eq=saturation=1.12:contrast=1.04",
    "cool": "colorbalance=rs=-0.04:bs=0.06:rm=-0.02:bm=0.04,eq=saturation=1.05:contrast=1.05",
    "cinematic": "colorbalance=rs=-0.06:bs=0.08:rh=0.07:bh=-0.06,eq=contrast=1.12:saturation=0.92,vignette=angle=PI/5",
    "moody": "eq=contrast=1.15:saturation=0.8:brightness=-0.03,vignette=angle=PI/4",
    "soft-warm": "colorbalance=rs=0.04:bs=-0.04:rm=0.03:bm=-0.03,eq=contrast=0.93:saturation=0.9:brightness=0.015:gamma=1.03",
    "bw": "hue=s=0,eq=contrast=1.18",
    # Azizon (hikoya): iliq kino tusi - soyalar iliq, kontrast yumshoq, teri tabiiy, chetlari biroz qoraygan
    "story-warm": "colorbalance=rs=0.05:gs=0.01:bs=-0.05:rm=0.04:bm=-0.05:rh=0.02:bh=-0.04,"
                  "eq=contrast=1.05:saturation=1.08:brightness=-0.01:gamma=0.98,vignette=angle=PI/6",
}
SFX_TARGET_PEAK_DB = -6.0

# o'tish nomi -> (FFmpeg xfade turi, standart davomiylik). Boshqa xfade nomlari ham to'g'ridan-to'g'ri ishlaydi.
TRANSITIONS = {"crossfade": ("fade", 0.3), "dip": ("fadeblack", 0.4), "flash": ("fadewhite", 0.25),
               "zoom": ("zoomin", 0.35), "slide": ("slideleft", 0.3), "slide-up": ("slideup", 0.3),
               "wipe": ("wipeleft", 0.3), "blur": ("hblur", 0.3), "circle": ("circleopen", 0.4)}


# ---------- vaqt jadvali ----------

def transition_spec(seg):
    """Bo'lakka KIRISH o'tishi: "crossfade" yoki {"type": "zoom", "dur": 0.4} -> {type, xfade, dur} yoki None."""
    tr = seg.get("transition")
    if not tr:
        return None
    tr = {"type": tr} if isinstance(tr, str) else dict(tr)
    xf, dur = TRANSITIONS.get(tr["type"], (tr["type"], 0.3))
    return {"type": tr["type"], "xfade": xf, "dur": float(tr.get("dur", dur))}


def build_timeline(edit, words, fps):
    """Bo'laklarning tayyor videodagi o'rni va so'zlarning yangi vaqtlari.
    Har bir bo'lak davomiyligi butun kadrlar soniga yaxlitlanadi - shunda subtitr siljimaydi.
    O'tish vaqtni qisqartirmaydi: oldingi bo'lak "dum" kadrlari bilan uzaytirilib, yangisi ustiga eriydi."""
    segs, out_words, offset = [], [], 0.0
    for i, seg in enumerate(edit["segments"]):
        s, e = float(seg["start"]), float(seg["end"])
        frames = max(1, round((e - s) * fps))
        dur = frames / fps
        tr = transition_spec(seg) if i else None
        if tr:
            tr["frames"] = max(2, min(round(tr["dur"] * fps), frames - 1))
            tr["dur"] = tr["frames"] / fps
        segs.append({**seg, "index": i, "frames": frames, "dur": dur, "offset": offset, "_tr": tr})
        for w in words:
            mid = (w["start"] + w["end"]) / 2
            if s <= mid <= e:
                out_words.append({"word": w["word"],
                                  "start": round(offset + min(max(w["start"] - s, 0), dur), 3),
                                  "end": round(offset + min(max(w["end"] - s, 0), dur), 3),
                                  "seg": i})
        offset += dur
    return segs, out_words, offset


def write_timeline_txt(path, segs, words, beats=None):
    lines = []
    for seg in segs:
        ws = [w for w in words if w["seg"] == seg["index"]]
        extra = ""
        if seg.get("move"):
            extra += f", harakat {move_label(seg['move'])}"
        if seg.get("_tr"):
            extra += f", o'tish {seg['_tr']['type']} {seg['_tr']['dur']:.2f} s"
        lines.append(f"\n# bo'lak {seg['index']}  [{fmt_time(seg['offset'])} - {fmt_time(seg['offset'] + seg['dur'])}]"
                     f"  (manba {seg['start']:.2f}-{seg['end']:.2f}, zoom {seg.get('zoom', 1)}{extra})")
        lines.append(" ".join(f"{w['word']}@{w['start']:.2f}" for w in ws))
    if beats:
        lines.append(f"\n# musiqa bitlari tayyor videoda (offset {beats['offset']:.2f} s, {beats['tempo']} BPM)")
        lines.append("kuchli: " + " ".join(f"{b:.2f}" for b in beats["downbeats"]))
        lines.append("barcha: " + " ".join(f"{b:.2f}" for b in beats["beats"]))
    Path(path).write_text("\n".join(lines).strip() + "\n", encoding="utf-8")


# ---------- subtitr (ASS) ----------

def ass_color(hex_rgb, alpha="00"):
    h = hex_rgb.lstrip("#")
    return f"&H{alpha}{h[4:6]}{h[2:4]}{h[0:2]}".upper()


def ass_time(t):
    t = max(0.0, t)
    cs = int(round(t * 100))
    return f"{cs // 360000}:{cs // 6000 % 60:02d}:{cs // 100 % 60:02d}.{cs % 100:02d}"


def clean(text, upper):
    text = re.sub(r"[{}\\]", "", text).strip()
    return text.upper() if upper else text


def style_line(name, st):
    return (f"Style: {name},{st['font']},{st['size']},{ass_color(st['color'])},{ass_color(st['color'])},"
            f"{ass_color(st['outline_color'])},{ass_color(st['outline_color'], '80')},-1,0,0,0,100,100,0,0,"
            f"{3 if st.get('box') else 1},{st['outline']},{st['shadow']},5,80,80,40,1")


def chunk_words(words, max_words):
    chunks, cur = [], []
    for w in words:
        if cur and (len(cur) >= max_words or w["start"] - cur[-1]["end"] > 0.6 or w["seg"] != cur[-1]["seg"]):
            chunks.append(cur)
            cur = []
        cur.append(w)
        if re.search(r"[.!?,]$", w["word"]):
            chunks.append(cur)
            cur = []
    if cur:
        chunks.append(cur)
    return chunks


def build_ass(words, sub_style, title, title_style, W, H, total):
    events = []
    if sub_style:
        st = sub_style
        pos = f"\\an5\\pos({W // 2},{int(H * st['position'])})"
        hl = ass_color(st["highlight"]) if st.get("highlight") else None
        chunks = chunk_words(words, st.get("max_words", 3))
        for ci, ch in enumerate(chunks):
            nxt = chunks[ci + 1][0]["start"] if ci + 1 < len(chunks) else total
            end = nxt if nxt - ch[-1]["end"] < 0.4 else ch[-1]["end"] + 0.15
            texts = [clean(w["word"], st.get("uppercase")) for w in ch]
            if not hl:
                events.append((ch[0]["start"], end, "Sub", "{" + pos + "}" + " ".join(texts)))
                continue
            for i, w in enumerate(ch):
                s = ch[0]["start"] if i == 0 else w["start"]
                e = ch[i + 1]["start"] if i + 1 < len(ch) else end
                active = (f"{{\\c{hl}\\fscx130\\fscy130\\t(0,90,\\fscx112\\fscy112)}}" if st.get("pop")
                          else f"{{\\c{hl}}}")
                parts = [active + t + "{\\r}" if j == i else t for j, t in enumerate(texts)]
                events.append((s, e, "Sub", "{" + pos + "}" + " ".join(parts)))
    if title and title.get("text"):
        ts = title_style
        hl = ass_color(ts["highlight"])
        text = clean(title["text"], ts.get("uppercase"))
        text = re.sub(r"\*(.+?)\*", lambda m: f"{{\\c{hl}}}{m.group(1)}{{\\r}}", text)
        tag = (f"{{\\an5\\pos({W // 2},{int(H * ts['position'])})\\fad(120,200)"
               f"\\fscx60\\fscy60\\t(0,160,\\fscx100\\fscy100)}}")
        events.append((float(title.get("start", 0)), float(title.get("end", 2.5)), "Title", tag + text))

    head = ["[Script Info]", "ScriptType: v4.00+", f"PlayResX: {W}", f"PlayResY: {H}",
            "WrapStyle: 0", "ScaledBorderAndShadow: yes", "", "[V4+ Styles]",
            "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, "
            "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, "
            "Shadow, Alignment, MarginL, MarginR, MarginV, Encoding"]
    if sub_style:
        head.append(style_line("Sub", sub_style))
    head.append(style_line("Title", title_style))
    head += ["", "[Events]", "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"]
    body = [f"Dialogue: {1 if sty == 'Title' else 0},{ass_time(s)},{ass_time(e)},{sty},,0,0,0,,{txt}"
            for s, e, sty, txt in sorted(events)]
    return "\n".join(head + body) + "\n", len(events)


def _norm(w):
    w = w.lower().replace("ʻ", "'").replace("ʼ", "'").replace("‘", "'").replace("’", "'").replace("`", "'")
    return re.sub(r"[^\w']", "", w)


def story_subs_block(words, st, edit, total):
    """"Hikoya" subtitrlari (Remotion StorySubs) uchun blok: so'zlar bo'laklarga, bo'lak 1-2 qatorga bo'linadi.
    st: max_words, emphasis (kalit so'zlar ro'yxati yoki "auto"), underline (so'zlar ro'yxati), y, size, color.
    WallCard bloklari vaqtida subtitr rangi to'q bo'ladi ("subs": {...} bilan o'zgartiriladi, false - yashiriladi)."""
    emph_cfg = st.get("emphasis", "auto")
    emph_set = {_norm(x) for x in emph_cfg} if isinstance(emph_cfg, list) else set()
    ul_set = {_norm(x) for x in (st.get("underline") or [])}
    zones = []
    for b in edit.get("animations") or []:
        if b.get("type") == "remotion" and (b.get("comp") == "WallCard" or "subs" in b):
            z = b.get("subs", {"color": "#241D18", "shadow": False} if b.get("comp") == "WallCard" else None)
            if z is not None:
                zones.append((float(b["start"]), float(b.get("end", b["start"] + 3)), z))
    chunks = []
    groups = chunk_words(words, st.get("max_words", 6))
    for ci, ch in enumerate(groups):
        nxt = groups[ci + 1][0]["start"] if ci + 1 < len(groups) else total
        end = nxt - 0.02 if nxt - ch[-1]["end"] < 0.45 else min(ch[-1]["end"] + 0.35, nxt - 0.02)
        ws = [{"w": clean(w["word"], False), "s": round(w["start"], 3)} for w in ch]
        ws = [w for w in ws if w["w"]]
        if not ws:
            continue
        # kalit so'z: ro'yxatdagilar, "auto" bo'lsa - bo'lakdagi eng uzun so'z (5+ harf)
        hit = False
        for w in ws:
            if _norm(w["w"]) in emph_set:
                w["emph"] = hit = True
            if _norm(w["w"]) in ul_set:
                w["ul"] = True
        if emph_cfg in ("auto", True) and not hit:
            best = max(ws, key=lambda w: len(_norm(w["w"])))
            if len(_norm(best["w"])) >= 5:
                best["emph"] = True
        # 4+ so'z - 2 qator; vergul bo'lsa o'sha yerdan bo'linadi
        if len(ws) >= 4:
            k = next((i + 1 for i, w in enumerate(ws[:-1]) if w["w"].endswith(",") and 1 <= i + 1 < len(ws) - 0),
                     (len(ws) + 1) // 2)
            lines = [ws[:k], ws[k:]]
        else:
            lines = [ws]
        c = {"start": ws[0]["s"], "end": round(end, 3), "lines": lines}
        z = next((z for a, b, z in zones if a - 0.05 <= c["start"] < b), None)
        if z is False:
            continue
        hide_at = min((a for a, b, zz in zones if zz is False and c["start"] < a < c["end"]), default=None)
        if hide_at is not None:
            c["end"] = round(hide_at - 0.15, 3)    # fade_out tugaguncha sahna almashadi
        if z:
            c.update({k: v for k, v in z.items() if k in ("color", "y", "size", "shadow")})
        chunks.append(c)
    style = {k: st[k] for k in ("y", "size", "color", "emph_scale", "underline_color", "italic", "weight",
                                "emph_color", "emph_weight", "fade_out") if k in st}
    if st.get("font") and st["font"] != "Instrument Serif":
        style["font"] = st["font"]
    if "position" in st:
        style.setdefault("y", st["position"])
    if "underline_color" in style:
        style["underline"] = style.pop("underline_color")
    return {"type": "remotion", "comp": st.get("comp", "StorySubs"), "start": 0.0, "end": total,
            "props": {"chunks": chunks, "style": style}}


# ---------- kadr ----------

def frame_geometry(fmt, W, H):
    if fmt == "original":
        scale = min(1.0, 1920 / max(W, H))
        return W / H, int(W * scale) // 2 * 2, int(H * scale) // 2 * 2
    ow, oh = OUT_SIZES[fmt]
    return ow / oh, ow, oh


def crop_box(W, H, aspect, zoom, x, y):
    cw, ch = (H * aspect, H) if W / H > aspect else (W, W / aspect)
    cw, ch = int(cw / zoom) // 2 * 2, int(ch / zoom) // 2 * 2
    return cw, ch, int((W - cw) * x), int((H - ch) * y)


# ---------- kamera harakati (bo'lak ichida) ----------
# "move": {"type": "punch", "at": 0.8, "to": 1.25, "in": 0.2, "hold": 1.0, "out": 0.3}
#         {"type": "kenburns", "from": 1.0, "to": 1.1, "pan": [0.03, 0], "ease": "linear"|"smooth"}
# Zoom bo'lakning o'z zoomiga nisbatan (1.0 = o'zgarishsiz). "anchor" [x, y] - kattalashish markazi
# (standart [0.5, 0.35] - reframe yuzni shu nuqtaga qo'yadi, shuning uchun yuz joyidan qochmaydi).

def move_label(mv):
    if mv.get("type") == "punch":
        return f"punch {mv.get('to', 1.25)} @{mv.get('at', 0)} s"
    return f"kenburns {mv.get('from', 1.0)}->{mv.get('to', 1.1)}"


def _ease(p, kind):
    return p if kind == "linear" else f"({p}*{p}*(3-2*{p}))"


def move_exprs(mv, dur, t):
    """(zoom, anchor_x, anchor_y) ifodalari. t - vaqt ifodasi: FFmpeg uchun "(n/50)", Python uchun "1.25"."""
    ax, ay = (float(v) for v in mv.get("anchor", (0.5, 0.35)))
    if mv.get("type", "kenburns") == "punch":
        at, to = float(mv.get("at", 0)), float(mv.get("to", 1.25))
        tin, tout = max(float(mv.get("in", 0.2)), 0.01), max(float(mv.get("out", 0.3)), 0.01)
        p1 = f"clip(({t}-{at:.4f})/{tin:.4f},0,1)"
        e = f"(1-pow(1-{p1},3))"
        if mv.get("hold") is not None:
            p2 = f"clip(({t}-{at + tin + float(mv['hold']):.4f})/{tout:.4f},0,1)"
            e = f"({e}-{_ease(p2, 'smooth')})"
        return f"max(1,1+{to - 1:.4f}*{e})", f"{ax}", f"{ay}"
    a, b = float(mv.get("from", 1.0)), float(mv.get("to", 1.1))
    e = _ease(f"clip({t}/{dur:.4f},0,1)", mv.get("ease", "linear"))
    dx, dy = (float(v) for v in mv.get("pan", (0, 0)))
    return (f"max(1,{a:.4f}+{b - a:.4f}*{e})", f"clip({ax}+{dx}*{e},0,1)", f"clip({ay}+{dy}*{e},0,1)")


def move_value(mv, dur, t):
    """Harakatning t soniyadagi (zoom, ax, ay) qiymati - storyboard eskizlari uchun."""
    env = {"clip": lambda v, lo, hi: min(max(v, lo), hi), "pow": pow, "max": max, "__builtins__": {}}
    return tuple(eval(x, env) for x in move_exprs(mv, dur, f"{t:.4f}"))


def frame_filter(seg, info, aspect, OW, OH, fps, n0=0, at=None):
    """Bo'lak uchun kadr filtri: kesish + format + zoom + harakat. at berilsa - bitta kadr (eskiz) uchun.
    "shift_y": 0.3 - kadr 30% pastga suriladi (tepasi qora; split-screen paneli ostida yuz pastki yarmida ko'rinadi)."""
    vf = _frame_filter(seg, info, aspect, OW, OH, fps, n0, at)
    dy = int(OH * float(seg.get("shift_y", 0))) // 2 * 2
    if dy > 0:
        vf += f",pad={OW}:{OH + dy}:0:{dy}:black,crop={OW}:{OH}:0:0"
    return vf


def _frame_filter(seg, info, aspect, OW, OH, fps, n0=0, at=None):
    cw, ch, cx, cy = crop_box(info["width"], info["height"], aspect, float(seg.get("zoom", 1.0)),
                              float(seg.get("x", 0.5)), float(seg.get("y", 0.5)))
    vf = f"crop={cw}:{ch}:{cx}:{cy}"
    mv = seg.get("move")
    if not mv:
        return vf + f",scale={OW}:{OH}:flags=lanczos,setsar=1"
    if at is not None:
        z, ax, ay = move_value(mv, seg["dur"], at)
        sw, sh = int(OW * z) // 2 * 2, int(OH * z) // 2 * 2
        return vf + (f",scale={sw}:{sh}:flags=lanczos,crop={OW}:{OH}:{int((sw - OW) * ax)}:{int((sh - OH) * ay)},"
                     f"setsar=1")
    z, ax, ay = move_exprs(mv, seg["dur"], f"((n+{n0})/{fps})")
    return vf + (f",scale=w='trunc({OW}*{z}/2)*2':h='trunc({OH}*{z}/2)*2':eval=frame:flags=lanczos,"
                 f"crop={OW}:{OH}:'(iw-{OW})*{ax}':'(ih-{OH})*{ay}',setsar=1")


def assemble_transitions(segs, seg_dir, fps, enc, out):
    """O'tishli bo'laklarni bitta video oqimiga yig'adi (faqat video; ovoz concat orqali o'zgarishsiz qoladi).
    O'tishdan oldingi bo'lak dum kadrlari (tail_*.mkv) bilan uzaytiriladi va keyingisi aynan o'z vaqtida
    boshlanib, ustiga eriydi - shuning uchun subtitr, SFX va animatsiya vaqtlari siljimaydi."""
    inputs, fc = [], []

    def inp(path):
        k = len(inputs) // 2
        inputs.extend(["-i", path])
        fc.append(f"[{k}:v]fps={fps},settb=AVTB,setpts=PTS-STARTPTS[i{k}]")
        return f"[i{k}]"

    cur = inp(seg_dir / "seg_000.mkv")
    for seg in segs[1:]:
        i = seg["index"]
        nxt = inp(seg_dir / f"seg_{i:03d}.mkv")
        tr = seg["_tr"]
        if tr:
            tail = inp(seg_dir / f"tail_{i - 1:03d}.mkv")
            fc.append(f"{cur}{tail}concat=n=2:v=1:a=0,fps={fps},settb=AVTB[c{i}]")
            fc.append(f"[c{i}]{nxt}xfade=transition={tr['xfade']}:duration={tr['dur']:.4f}:"
                      f"offset={seg['offset']:.4f}[x{i}]")
        else:
            fc.append(f"{cur}{nxt}concat=n=2:v=1:a=0,fps={fps},settb=AVTB[x{i}]")
        cur = f"[x{i}]"
    run_ffmpeg(inputs + ["-filter_complex", ";".join(fc), "-map", cur, "-an"] + enc + [out])


def grade_filter(grade):
    if not grade:
        return None
    if isinstance(grade, str):
        if grade not in GRADES:
            raise SystemExit(f"Noma'lum grade: {grade}. Mavjud: {', '.join(GRADES)}")
        return GRADES[grade]
    parts = [GRADES[grade["preset"]]] if grade.get("preset") else []
    eq = {k: grade[k] for k in ("contrast", "saturation", "brightness", "gamma") if k in grade}
    if eq:
        parts.append("eq=" + ":".join(f"{k}={v}" for k, v in eq.items()))
    if grade.get("vignette"):
        parts.append("vignette=angle=PI/5")
    return ",".join(parts) or None


# ---------- musiqa va SFX ----------

def music_sync(music, segs, total):
    """Musiqa offsetini kesimlar bitga tushadigan qilib tanlaydi. Natija: offset va tayyor videodagi bitlar."""
    import beats as beatmod
    os.environ.setdefault("NUMBA_CACHE_DIR", str(Path.home() / ".ai-montaj" / "numba"))
    data = beatmod.analyze(resolve(music["file"]))
    cuts = [s["offset"] for s in segs[1:]]
    if "offset" in music:
        off, hits = float(music["offset"]), None
    else:
        off, hits = beatmod.best_offset(data["beats"], cuts, data["duration"], total)
    shift = lambda arr: [round(b - off, 3) for b in arr if 0 <= b - off <= total]
    return {"offset": off, "hits": hits, "cuts": len(cuts), "tempo": data["tempo"],
            "beats": shift(data["beats"]), "downbeats": shift(data["downbeats"])}


def sfx_gain(path):
    """Katalogdagi cho'qqi qiymatiga qarab barcha SFX'ni bir xil balandlikka keltiruvchi koeffitsient."""
    cat = ROOT / "assets" / "sfx" / "catalog.json"
    if not cat.exists():
        return 1.0
    rel = Path(path).resolve().relative_to(ROOT).as_posix() if Path(path).resolve().is_relative_to(ROOT) else None
    for s in load_json(cat)["sounds"]:
        if s["file"] == rel:
            return 10 ** ((SFX_TARGET_PEAK_DB - s["peak_db"]) / 20)
    return 1.0


# ---------- asosiy ----------

def prepare(edit_path):
    """Rejani o'qib, vaqt jadvalini (timeline.json/txt) yozadi. render va storyboard umumiy qismi."""
    F = edit_files(edit_path)
    edit = load_json(edit_path)
    src = resolve(edit["source"])
    info = probe(src)
    fps = round(info["fps"]) if info["fps"] > 0 else 30
    words = all_words(load_json(resolve(edit["transcript"])))

    segs, tl_words, total = build_timeline(edit, words, fps)
    aspect, OW, OH = frame_geometry(edit.get("format", "9:16"), info["width"], info["height"])
    music = edit.get("music") if (edit.get("music") or {}).get("file") else None
    beat_info = music_sync(music, segs, total) if music and music.get("sync") else None
    save_json({"fps": fps, "duration": total, "width": OW, "height": OH, "segments": segs, "words": tl_words,
               "beats": beat_info}, F["timeline_json"])
    write_timeline_txt(F["timeline_txt"], segs, tl_words, beat_info)
    print(f"{len(segs)} ta bo'lak, tayyor video {fmt_time(total)} ({total:.2f} s). Vaqt jadvali: {F['timeline_txt']}")
    if beat_info:
        print(f"Musiqa: {beat_info['tempo']} BPM, offset {beat_info['offset']:.2f} s"
              + (f", {beat_info['hits']}/{beat_info['cuts']} kesim bitga tushdi" if beat_info["hits"] is not None else ""))
    return dict(F=F, edit=edit, src=src, info=info, fps=fps, segs=segs, words=tl_words, total=total,
                aspect=aspect, OW=OW, OH=OH, music=music, beats=beat_info)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("edit")
    ap.add_argument("--timeline-only", action="store_true")
    ap.add_argument("--preview", action="store_true", help="Tez, past sifatli render (tekshirish uchun)")
    args = ap.parse_args()

    edit_path = resolve(args.edit)
    P = prepare(edit_path)
    if args.timeline_only:
        return
    F, edit, src, info, fps = P["F"], P["edit"], P["src"], P["info"], P["fps"]
    segs, tl_words, total, aspect, OW, OH = P["segs"], P["words"], P["total"], P["aspect"], P["OW"], P["OH"]
    music, beat_info = P["music"], P["beats"]
    work = F["work"]

    t0 = time.time()
    preset, crf = ("ultrafast", 26) if args.preview else ("veryfast", 16)

    # 1-bosqich: bo'laklar
    seg_dir = F["segments"]
    shutil.rmtree(seg_dir, ignore_errors=True)
    seg_dir.mkdir(parents=True)
    enc = ["-c:v", "libx264", "-preset", preset, "-crf", crf, "-pix_fmt", "yuv420p"]
    for seg in segs:
        d = seg["dur"]
        inputs = ["-ss", f"{seg['start']:.3f}", "-i", src]
        if not info["has_audio"]:
            inputs += ["-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo"]
        a_in = "0:a" if info["has_audio"] else "1:a"
        fc = (f"[0:v]fps={fps},{frame_filter(seg, info, aspect, OW, OH, fps)}[v];"
              f"[{a_in}]aresample=48000,aformat=channel_layouts=stereo,atrim=0:{d:.4f},"
              f"afade=t=in:d=0.02,afade=t=out:st={max(d - 0.03, 0):.4f}:d=0.03,apad=whole_dur={d:.4f}[a]")
        run_ffmpeg(inputs + ["-t", f"{d + 0.5:.3f}", "-filter_complex", fc, "-map", "[v]", "-map", "[a]",
                             "-frames:v", seg["frames"]] + enc + ["-c:a", "pcm_s16le",
                             seg_dir / f"seg_{seg['index']:03d}.mkv"])
        nxt = segs[seg["index"] + 1] if seg["index"] + 1 < len(segs) else None
        if nxt and nxt["_tr"]:
            # o'tish uchun dum: bo'lak tugagan joydan davom etuvchi kadrlar (manba tugasa - oxirgi kadr ushlanadi)
            n = nxt["_tr"]["frames"]
            run_ffmpeg(["-ss", f"{seg['start'] + d:.3f}", "-i", src, "-t", f"{n / fps + 0.5:.3f}", "-vf",
                        f"fps={fps},{frame_filter(seg, info, aspect, OW, OH, fps, n0=seg['frames'])},"
                        f"tpad=stop_mode=clone:stop={n}", "-frames:v", n, "-an"] + enc
                       + [seg_dir / f"tail_{seg['index']:03d}.mkv"])
        print(f"  bo'lak {seg['index'] + 1}/{len(segs)}", flush=True)
    (work / F["concat"]).write_text(
        "".join(f"file '{seg_dir.name}/seg_{s['index']:03d}.mkv'\n" for s in segs), encoding="utf-8")
    xfade_video = None
    if any(s["_tr"] for s in segs):
        xfade_video = seg_dir / "video_xfade.mkv"
        assemble_transitions(segs, seg_dir, fps, enc, xfade_video)
        print(f"  o'tishlar: {', '.join(s['_tr']['type'] for s in segs if s['_tr'])}", flush=True)

    # animatsiya qatlami (HyperFrames)
    anim_frames = None
    if edit.get("animations"):
        import animate
        frames = animate.build(edit_path)
        if frames:
            anim_frames = animate.frame_pattern(frames)
    # subtitr: oddiy uslublar - ASS (libass); "engine": "remotion" uslublar (hikoya) - Remotion StorySubs qatlami
    styles = load_json(ROOT / "styles" / "subtitles.json")
    sub_cfg = edit.get("subtitles")
    sub_style = None
    if sub_cfg:
        name = sub_cfg.get("style", "pop")
        if name not in styles:
            raise SystemExit(f"Noma'lum uslub: {name}. Mavjud: {', '.join(k for k in styles if not k.startswith('_'))}")
        sub_style = {**styles[name], **{k: v for k, v in sub_cfg.items() if k != "style"}}
    story_blocks = []
    if sub_style and sub_style.get("engine") == "remotion":
        story_blocks = [story_subs_block(tl_words, sub_style, edit, total)]
        sub_style = None
    ass, n_events = build_ass(tl_words, sub_style, edit.get("title"), styles["_title"], OW, OH, total)
    (work / F["subs"]).write_text(ass, encoding="utf-8")

    # Remotion qatlami: har bir blok - alohida shaffof klip; "layer": "behind" bloklar odam orqasiga qo'yiladi
    import remotion_layer
    behind_clips = remotion_layer.build(edit_path, layer="behind")
    rem_clips = remotion_layer.build(edit_path, extra=story_blocks, layer="front")
    mattes = []
    if behind_clips:
        import matte
        base, is_concat = (xfade_video, False) if xfade_video else (work / F["concat"], True)
        for k, (mov, r_start, r_end) in enumerate(behind_clips):
            mf = work / f"matte_{k:02d}.mkv"
            print(f"  odam niqobi {r_start:.2f}-{r_end:.2f} s...", flush=True)
            matte.build(base, r_start, r_end - r_start, mf, OW, OH, fps, concat=is_concat, cwd=work)
            mattes.append((mov, r_start, r_end, mf, base, is_concat))

    # 2-bosqich: yig'ish
    inputs = ["-f", "concat", "-safe", "0", "-i", F["concat"]]
    idx = 1
    vchain, vlabel = [], "[0:v]"
    if xfade_video:
        inputs += ["-i", xfade_video]
        vlabel = f"[{idx}:v]"
        idx += 1
    g = grade_filter(edit.get("grade"))
    if g:
        vchain.append(f"{vlabel}{g}[vg]")
        vlabel = "[vg]"
    # odam orqasidagi bloklar: fon + blok, ustiga o'sha kadrlardan niqob bilan kesilgan odam
    for k, (mov, r_start, r_end, mf, base, is_concat) in enumerate(mattes):
        d = r_end - r_start
        inputs += ["-i", mov]
        vchain.append(f"[{idx}:v]setpts=PTS-STARTPTS+{r_start:.3f}/TB[bw{k}]")
        vchain.append(f"{vlabel}[bw{k}]overlay=0:0:format=auto:eof_action=pass:"
                      f"enable='between(t,{r_start:.3f},{r_end:.3f})'[bt{k}]")
        idx += 1
        inputs += ["-ss", f"{r_start:.3f}", "-t", f"{d:.3f}"] + (["-f", "concat", "-safe", "0"] if is_concat else []) \
            + ["-i", base if not is_concat else F["concat"]]
        pc = f"[{idx}:v]fps={fps},setpts=PTS-STARTPTS" + (f",{g}" if g else "") + f"[bc{k}]"
        vchain.append(pc)
        idx += 1
        inputs += ["-i", mf]
        vchain.append(f"[{idx}:v]format=gray,setpts=PTS-STARTPTS[bm{k}]")
        vchain.append(f"[bc{k}][bm{k}]alphamerge,setpts=PTS-STARTPTS+{r_start:.3f}/TB[bp{k}]")
        vchain.append(f"[bt{k}][bp{k}]overlay=0:0:format=auto:eof_action=pass:"
                      f"enable='between(t,{r_start:.3f},{r_end - 1 / fps:.3f})'[bv{k}]")
        vlabel = f"[bv{k}]"
        idx += 1
    if anim_frames:
        pattern, start_no = anim_frames
        inputs += ["-framerate", fps, "-start_number", start_no, "-i", pattern]
        vchain.append(f"{vlabel}[{idx}:v]overlay=0:0:format=auto:eof_action=pass[va]")
        vlabel = "[va]"
        idx += 1
    for k, (mov, r_start, r_end) in enumerate(rem_clips):
        inputs += ["-i", mov]
        vchain.append(f"[{idx}:v]setpts=PTS-STARTPTS+{r_start:.3f}/TB[rm{k}]")
        vchain.append(f"{vlabel}[rm{k}]overlay=0:0:format=auto:eof_action=pass:"
                      f"enable='between(t,{r_start:.3f},{r_end:.3f})'[vr{k}]")
        vlabel = f"[vr{k}]"
        idx += 1
    # "fade": 0.6 yoki {"in": 0.3, "out": 0.6, "color": "black", "audio": true} - boshi/oxirida rangga erish
    fade = edit.get("fade") or {}
    fade = {"out": float(fade)} if isinstance(fade, (int, float)) else fade
    f_in, f_out, f_col = float(fade.get("in", 0)), float(fade.get("out", 0)), fade.get("color", "black")
    vend = ""
    if f_in:
        vend += f",fade=t=in:d={f_in:.3f}:color={f_col}"
    if f_out:
        vend += f",fade=t=out:st={total - f_out:.3f}:d={f_out:.3f}:color={f_col}"
    aend = f",afade=t=out:st={total - f_out:.3f}:d={f_out:.3f}" if f_out and fade.get("audio", True) else ""
    if n_events:
        fonts = os.path.relpath(ROOT / "assets" / "fonts", work).replace("\\", "/")
        vchain.append(f"{vlabel}subtitles={F['subs']}:fontsdir={fonts}{vend}[v]")
    else:
        vchain.append(f"{vlabel}null{vend}[v]")

    afc = []
    audio_cfg = edit.get("audio") or {}
    chain = ["highpass=f=80"]
    if audio_cfg.get("denoise", True):
        chain.append("afftdn=nf=-25")
    if audio_cfg.get("loudnorm", True):
        chain.append("loudnorm=I=-14:TP=-1.5:LRA=11")
    chain += ["aresample=48000", "aformat=channel_layouts=stereo"]
    if audio_cfg.get("voice_volume"):
        chain.append(f"volume={audio_cfg['voice_volume']}")
    afc.append(f"[0:a]{','.join(chain)}[voice]")
    mix = ["[voice]"]

    if music:
        inputs += ["-stream_loop", "-1", "-i", resolve(music["file"])]
        # musiqa avval ovoz kabi -14 LUFS ga keltiriladi, so'ng volume = ovozga nisbatan (0.25 ~ 12 LU past)
        vol = float(music.get("volume", 0.25))
        off = beat_info["offset"] if beat_info else float(music.get("offset", 0))
        fade = min(1.5, total / 4)
        afc.append(f"[{idx}:a]aresample=48000,aformat=channel_layouts=stereo,"
                   f"atrim={off:.3f}:{off + total:.3f},asetpts=PTS-STARTPTS,"
                   f"loudnorm=I=-14:TP=-2:LRA=11,aresample=48000,volume={vol},"
                   f"afade=t=in:d=0.3,afade=t=out:st={total - fade:.3f}:d={fade:.3f}[m0]")
        if music.get("duck", True):
            afc[0] = afc[0].replace("[voice]", "[voicepre]")
            afc.append("[voicepre]asplit=2[voice][sc]")
            afc.append("[m0][sc]sidechaincompress=threshold=0.03:ratio=6:attack=15:release=350[m]")
            mix.append("[m]")
        else:
            mix.append("[m0]")
        idx += 1

    snap = beat_info["beats"] if beat_info and music.get("snap_sfx") else None
    for k, fx in enumerate(edit.get("sfx") or []):
        at = float(fx["at"])
        if snap:
            near = min(snap, key=lambda b: abs(b - at))
            at = near if abs(near - at) <= 0.15 else at
        inputs += ["-i", resolve(fx["file"])]
        vol = float(fx.get("volume", 0.7)) * sfx_gain(resolve(fx["file"]))
        afc.append(f"[{idx}:a]aresample=48000,aformat=channel_layouts=stereo,"
                   f"volume={vol:.4f},adelay={int(at * 1000)}:all=1[s{k}]")
        mix.append(f"[s{k}]")
        idx += 1

    if len(mix) > 1:
        afc.append(f"{''.join(mix)}amix=inputs={len(mix)}:normalize=0:duration=first:dropout_transition=0,"
                   f"alimiter=limit=0.95{aend}[a]")
    else:
        afc.append(f"[voice]anull{aend}[a]")

    out = resolve(edit.get("output", f"output/{work.name}.mp4"))
    if args.preview:
        out = out.with_name(out.stem + "_preview.mp4")
    out.parent.mkdir(parents=True, exist_ok=True)
    run_ffmpeg(inputs + ["-filter_complex", ";".join(vchain + afc), "-map", "[v]", "-map", "[a]",
                         "-t", f"{total:.3f}", "-c:v", "libx264", "-preset", "ultrafast" if args.preview else "medium",
                         "-crf", 28 if args.preview else 20, "-pix_fmt", "yuv420p", "-r", fps,
                         "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", out], cwd=work)
    print(f"\nTayyor ({time.time() - t0:.0f} s): {out}")


if __name__ == "__main__":
    main()
