"""Animatsiya qatlami: edit.json dagi "animations" bloklaridan HyperFrames (HTML + GSAP) kompozitsiya
yasaydi va uni shaffof PNG kadrlar qilib render qiladi. render.py kadrlarni video ustiga qo'yadi.

Misol:
    python montaj/animate.py work/video/edit.json            # yasash + render
    python montaj/animate.py work/video/edit.json --snapshot 1.2 5   # faqat shu soniyalarni PNG qilib ko'rish

Vaqtlar - TAYYOR videodagi soniyalar (timeline.txt dagi kabi). Bloklar ro'yxati SKILL.md da.
Maxsus animatsiya: {"type": "html", "file": "work/video/my_block.html", "start": 2, "end": 4} -
faylda HTML va <script> bo'ladi; skriptda `tl` (GSAP timeline), `T` (blok boshlanishi), `W`, `H` mavjud.
"""
import argparse
import hashlib
import html
import json
import math
import os
import random
import re
import shutil
import subprocess
import sys
import time

from common import ROOT, TOOLS, edit_files, load_json, resolve, save_json

HF_DIR = TOOLS / "hf"
NODE_DIR = TOOLS / "node"
FONTS = ROOT / "assets" / "fonts"

DEFAULT_THEME = {"accent": "#FFE600", "text": "#FFFFFF", "dark": "#111111", "font": "Montserrat",
                 "weight": 900, "radius": 28}


def esc(s):
    return html.escape(str(s), quote=True)


def rich(text, accent_cls="hl"):
    """*so'z* -> ajratilgan so'z; \\n -> yangi qator."""
    out = []
    for part in re.split(r"(\*[^*]+\*)", str(text)):
        if part.startswith("*") and part.endswith("*"):
            out.append(f'<span class="{accent_cls}">{esc(part[1:-1])}</span>')
        else:
            out.append(esc(part))
    return "".join(out).replace("\n", "<br>")


def words_html(text):
    """Har bir so'zni alohida span'ga o'raydi (stagger animatsiya uchun).
    *so'z* - aksent rangi, ==ibora== - ustidan marker chiziladi (qo'lda chizilgandek)."""
    spans = []
    for line in str(text).split("\n"):
        for tok in re.findall(r"==[^=]+==|\*[^*]+\*|\S+", line):
            if tok.startswith("==") and tok.endswith("=="):
                inner = tok[2:-2]
                hl = inner.startswith("*") and inner.endswith("*")
                cls, word = ("w mk hl", inner[1:-1]) if hl else ("w mk", inner)
            else:
                hl = tok.startswith("*") and tok.endswith("*")
                cls, word = ("w hl", tok[1:-1]) if hl else ("w", tok)
            spans.append(f'<span class="{cls}">{esc(word)}</span>')
        spans.append("<br>")
    return " ".join(spans[:-1])


def rough_paths(shape, cx, cy, w, h, rnd):
    """Qo'lda chizilgandek notekis SVG yo'llar (piksellarda). Har biri alohida chiziladi."""
    j = lambda a: rnd.uniform(-a, a)
    poly = lambda pts: "M" + " L".join(f"{x:.1f} {y:.1f}" for x, y in pts)
    rx, ry = w / 2, h / 2
    if shape == "circle":
        a0, ph, n = rnd.uniform(0, 2 * math.pi), rnd.uniform(0, 6), 72
        pts = []
        for k in range(n + 1):
            p = k / n
            a = a0 - 2 * math.pi * 1.12 * p
            r = 1 + 0.035 * math.sin(3 * a + ph) + 0.07 * p
            pts.append((cx + rx * r * math.cos(a), cy + ry * r * math.sin(a)))
        return [poly(pts)]
    if shape == "underline":
        bow = h * 0.35 + j(h * 0.1)
        n = 24
        pts = [(cx - rx + w * k / n, cy + bow * math.sin(math.pi * k / n) * -0.4 + (k / n) * j(h * 0.3)) for k in range(n + 1)]
        return [poly(pts)]
    if shape == "box":
        c = [(cx - rx, cy - ry), (cx + rx, cy - ry), (cx + rx, cy + ry), (cx - rx, cy + ry)]
        out = []
        for i in range(4):
            (x0, y0), (x1, y1) = c[i], c[(i + 1) % 4]
            dx, dy = x1 - x0, y1 - y0
            o0, o1 = rnd.uniform(-0.02, 0.06), rnd.uniform(0.03, 0.09)
            out.append(f"M{x0 - dx * o0 + j(6):.1f} {y0 - dy * o0 + j(6):.1f} "
                       f"Q{(x0 + x1) / 2 + j(10):.1f} {(y0 + y1) / 2 + j(10):.1f} {x1 + dx * o1 + j(6):.1f} {y1 + dy * o1 + j(6):.1f}")
        return out
    if shape == "scribble":
        n = max(5, int(w / max(h * 0.35, 30)))
        pts = [(cx - rx + w * k / n + j(8), cy + (ry if k % 2 else -ry) * rnd.uniform(0.75, 1)) for k in range(n + 1)]
        return [poly(pts), poly([(x + j(10), y + j(10)) for x, y in reversed(pts)])]
    if shape == "strike":
        return [f"M{cx - rx:.1f} {cy + j(h * 0.2):.1f} Q{cx:.1f} {cy + j(h * 0.4):.1f} {cx + rx:.1f} {cy + j(h * 0.2):.1f}"]
    if shape == "highlight":
        return [f"M{cx - rx:.1f} {cy + j(h * 0.08):.1f} L{cx + rx:.1f} {cy + j(h * 0.08):.1f}"]
    if shape == "check":
        return [poly([(cx - rx, cy), (cx - rx * 0.25, cy + ry), (cx + rx, cy - ry)])]
    if shape == "cross":
        return [poly([(cx - rx, cy - ry), (cx + rx, cy + ry)]), poly([(cx + rx, cy - ry), (cx - rx, cy + ry)])]
    raise SystemExit(f"Noma'lum belgi shakli: {shape} (circle, underline, box, scribble, strike, highlight, check, cross)")


class Builder:
    def __init__(self, W, H, theme):
        self.W, self.H, self.th = W, H, theme
        self.html, self.js, self.css = [], [], []
        self.assets = []
        self.n = 0

    def add(self, block, total):
        t = block["type"]
        start = float(block.get("start", 0))
        end = float(block.get("end", total if t == "progress" else start + 2))
        self.n += 1
        bid = f"b{self.n}"
        fn = getattr(self, "b_" + t.replace("-", "_"), None)
        if not fn:
            raise SystemExit(f"Noma'lum animatsiya turi: {t}")
        inner, js = fn(bid, block, start, end, total)
        dur = max(end - start, 0.05)
        self.html.append(f'<div id="{bid}" class="clip" data-start="{start:.3f}" data-duration="{dur:.3f}" '
                         f'data-track-index="{self.n}">{inner}</div>')
        self.js.append(f"// {t} {start:.2f}-{end:.2f}\n(() => {{ const T = {start:.3f}, D = {dur:.3f}; {js} }})();")

    def pos(self, b, dx=0.5, dy=0.5):
        x, y = float(b.get("x", dx)), float(b.get("y", dy))
        return f"left:{x * self.W:.0f}px;top:{y * self.H:.0f}px;"

    # --- bloklar ---
    def b_text(self, bid, b, s, e, total):
        size = b.get("size", 110)
        eff = b.get("effect", "pop")
        style = b.get("style", "outline")  # outline | box | plain
        box = "".join(f"{k}:{v};" for k, v in (("border-radius", f'{b["radius"]}px' if "radius" in b else None),
                                                ("background", b.get("bg")), ("font-weight", b.get("weight")),
                                                ("padding", b.get("padding"))) if v is not None)
        inner = (f'<div class="anchor {esc(style)}" style="{self.pos(b, 0.5, 0.3)}font-size:{size}px;'
                 f'{"color:" + b["color"] + ";" if b.get("color") else ""}">'
                 f'<div class="txt" style="{box}">{words_html(b["text"])}</div></div>')
        mark_at = b.get("mark_at", 0.25 if eff == "none" else 0.55)
        mark_js = (f"tl.to('#{bid} .mk', {{backgroundSize:'100% 42%', duration:{b.get('mark_draw', 0.35)}, "
                   f"ease:'power2.out', stagger:0.12}}, T + {mark_at});" if "==" in str(b["text"]) else "")
        if eff == "none":  # doimiy sarlavha: birinchi kadrdan turadi, oxirida tez yo'qoladi
            exit_js = f"tl.to('#{bid} .anchor', {{opacity:0, duration:0.15}}, T + D - 0.15);" if b.get("exit", True) else ""
            return inner, mark_js + exit_js
        stag = float(b.get("stagger", 0.08))
        anims = {
            "pop": "{scale:0.3, opacity:0}, {scale:1, opacity:1, duration:0.35, ease:'back.out(2.2)', stagger:%s}",
            "slide": "{y:80, opacity:0}, {y:0, opacity:1, duration:0.4, ease:'power3.out', stagger:%s}",
            "blur": "{opacity:0, filter:'blur(18px)', scale:1.3}, {opacity:1, filter:'blur(0px)', scale:1, duration:0.4, ease:'power2.out', stagger:%s}",
            "drop": "{y:-260, opacity:0, rotation:-8}, {y:0, opacity:1, rotation:0, duration:0.45, ease:'bounce.out', stagger:%s}",
            "typewriter": "{opacity:0}, {opacity:1, duration:0.01, stagger:%s}",
        }
        a = anims.get(eff, anims["pop"]) % stag
        js = (f"tl.fromTo('#{bid} .w', {a}, T);"
              f"tl.to('#{bid} .hl', {{scale:1.08, duration:0.25, yoyo:true, repeat:1, ease:'sine.inOut'}}, T + 0.45);"
              f"tl.to('#{bid} .anchor', {{opacity:0, scale:0.9, duration:0.2, ease:'power2.in'}}, T + D - 0.2);")
        return inner, mark_js + js

    def b_mark(self, bid, b, s, e, total):
        """Qo'lda chizilgan belgi: circle, underline, box (sketchout), scribble, strike, highlight, check, cross.
        x, y - markaz; w, h - o'lcham (kadr ulushi); chiziq `draw` soniyada chizib chiqiladi."""
        shape = b.get("shape", "circle")
        cx, cy = float(b.get("x", 0.5)) * self.W, float(b.get("y", 0.5)) * self.H
        w = float(b.get("w", 0.6)) * self.W
        h = float(b.get("h", 0.1 if shape not in ("check", "cross") else 0.06)) * self.H
        rnd = random.Random(b.get("seed", self.n))
        color = b.get("color", self.th["accent"])
        hl = shape == "highlight"
        stroke = float(b.get("stroke", h * 0.9 if hl else 12))
        style = (f"stroke:{color};stroke-width:{stroke:.1f};stroke-linecap:{'butt' if hl else 'round'};"
                 f"opacity:{b.get('opacity', 0.45 if hl else 1)}")
        ds = rough_paths(shape, cx, cy, w, h, rnd)
        paths = "".join(f'<path d="{d}" pathLength="1" style="{style}"/>' for d in ds)
        inner = f'<svg class="full mark" viewBox="0 0 {self.W} {self.H}">{paths}</svg>'
        draw = float(b.get("draw", 0.45))
        n = len(ds)
        js = (f"tl.to('#{bid} path', {{strokeDashoffset:0, duration:{draw / n:.3f}, stagger:{draw / n:.3f}, "
              f"ease:'{b.get('ease', 'power1.inOut')}'}}, T);")
        if b.get("exit", True):
            js += f"tl.to('#{bid} .mark', {{opacity:0, duration:0.2}}, T + D - 0.2);"
        return inner, js

    def b_counter(self, bid, b, s, e, total):
        size = b.get("size", 170)
        label = f'<div class="label">{rich(b["label"])}</div>' if b.get("label") else ""
        inner = (f'<div class="anchor outline" style="{self.pos(b, 0.5, 0.3)}">'
                 f'<div class="num" style="font-size:{size}px">{esc(b.get("prefix", ""))}<span class="v">0</span>'
                 f'{esc(b.get("suffix", ""))}</div>{label}</div>')
        frm, to = float(b.get("from", 0)), float(b["to"])
        dec = int(b.get("decimals", 0))
        cnt = float(b.get("count_time", min(1.2, max(e - s - 0.4, 0.3))))
        js = (f"const o = {{v:{frm}}}; const el = document.querySelector('#{bid} .v');"
              f"const fmt = v => v.toFixed({dec}).replace(/\\B(?=(\\d{{3}})+(?!\\d))/g, ' ');"
              f"el.textContent = fmt({frm});"
              f"tl.fromTo('#{bid} .anchor', {{scale:0.4, opacity:0}}, {{scale:1, opacity:1, duration:0.3, ease:'back.out(2)'}}, T);"
              f"tl.to(o, {{v:{to}, duration:{cnt}, ease:'power2.out', onUpdate:() => el.textContent = fmt(o.v)}}, T + 0.1);"
              f"tl.to('#{bid} .num', {{scale:1.12, duration:0.15, yoyo:true, repeat:1}}, T + 0.1 + {cnt});"
              f"tl.to('#{bid} .anchor', {{opacity:0, y:-40, duration:0.2}}, T + D - 0.2);")
        return inner, js

    def b_emoji(self, bid, b, s, e, total):
        size = b.get("size", 190)
        inner = (f'<div class="anchor" style="{self.pos(b, 0.8, 0.25)}">'
                 f'<div class="emoji" style="font-size:{size}px">{esc(b["emoji"])}</div></div>')
        js = (f"tl.fromTo('#{bid} .emoji', {{scale:0, rotation:-30}}, {{scale:1, rotation:0, duration:0.45, ease:'back.out(3)'}}, T);"
              f"tl.to('#{bid} .emoji', {{rotation:10, y:-14, duration:0.35, yoyo:true, repeat:Math.max(1, Math.floor((D-0.8)/0.35)), ease:'sine.inOut'}}, T + 0.45);"
              f"tl.to('#{bid} .emoji', {{scale:0, duration:0.2, ease:'back.in(2)'}}, T + D - 0.2);")
        return inner, js

    def b_flash(self, bid, b, s, e, total):
        color = b.get("color", "#FFFFFF")
        inner = f'<div class="full flash" style="background:{color}"></div>'
        d = float(b.get("duration", e - s))
        js = (f"tl.fromTo('#{bid} .flash', {{opacity:0}}, {{opacity:{b.get('opacity', 0.85)}, duration:{d * 0.3:.3f}, ease:'power1.out'}}, T);"
              f"tl.to('#{bid} .flash', {{opacity:0, duration:{d * 0.7:.3f}, ease:'power2.in'}}, T + {d * 0.3:.3f});")
        return inner, js

    def b_progress(self, bid, b, s, e, total):
        top = b.get("position", "top") == "top"
        color = b.get("color", self.th["accent"])
        h = b.get("height", 14)
        inner = (f'<div class="bar-bg" style="{"top" if top else "bottom"}:0;height:{h}px"></div>'
                 f'<div class="bar" style="{"top" if top else "bottom"}:0;height:{h}px;background:{color}"></div>')
        js = f"tl.fromTo('#{bid} .bar', {{scaleX:0}}, {{scaleX:1, duration:D, ease:'none'}}, T);"
        return inner, js

    def b_lower_third(self, bid, b, s, e, total):
        sub = f'<div class="lt-sub">{rich(b["subtitle"])}</div>' if b.get("subtitle") else ""
        inner = (f'<div class="lt" style="top:{float(b.get("y", 0.62)) * self.H:.0f}px">'
                 f'<div class="lt-bar"></div><div class="lt-body"><div class="lt-title">{rich(b["title"])}</div>{sub}</div></div>')
        js = (f"tl.fromTo('#{bid} .lt-bar', {{scaleY:0}}, {{scaleY:1, duration:0.25, ease:'power3.out'}}, T);"
              f"tl.fromTo('#{bid} .lt-body', {{x:-60, opacity:0}}, {{x:0, opacity:1, duration:0.35, ease:'power3.out'}}, T + 0.1);"
              f"tl.to('#{bid} .lt', {{x:-80, opacity:0, duration:0.25, ease:'power2.in'}}, T + D - 0.25);")
        return inner, js

    def b_list(self, bid, b, s, e, total):
        items = b["items"]
        times = b.get("times") or [s + 0.35 * i for i in range(len(items))]
        rows = "".join(f'<div class="li"><span class="ck">{esc(b.get("bullet", "✓"))}</span>{rich(it)}</div>' for it in items)
        inner = f'<div class="list" style="top:{float(b.get("y", 0.25)) * self.H:.0f}px;font-size:{b.get("size", 64)}px">{rows}</div>'
        js = "".join(f"tl.fromTo('#{bid} .li:nth-child({i + 1})', {{x:-120, opacity:0}}, {{x:0, opacity:1, duration:0.35, ease:'back.out(1.6)'}}, {float(t):.3f});"
                     for i, t in enumerate(times))
        js += f"tl.to('#{bid} .list', {{opacity:0, duration:0.2}}, T + D - 0.2);"
        return inner, js

    def b_cta(self, bid, b, s, e, total):
        inner = (f'<div class="anchor" style="{self.pos(b, 0.5, 0.82)}"><div class="cta">{rich(b.get("text", "Direktga yozing"))}'
                 f'<span class="tap">{esc(b.get("icon", "👆"))}</span></div></div>')
        js = (f"tl.fromTo('#{bid} .cta', {{scale:0, opacity:0}}, {{scale:1, opacity:1, duration:0.4, ease:'back.out(2.5)'}}, T);"
              f"tl.to('#{bid} .cta', {{scale:1.07, duration:0.4, yoyo:true, repeat:Math.max(1, Math.floor((D-0.7)/0.4)), ease:'sine.inOut'}}, T + 0.4);"
              f"tl.fromTo('#{bid} .tap', {{y:30, opacity:0}}, {{y:0, opacity:1, duration:0.3, repeat:Math.max(1, Math.floor((D-0.7)/0.6)), yoyo:true}}, T + 0.4);")
        return inner, js

    def b_arrow(self, bid, b, s, e, total):
        ang = float(b.get("angle", 90))
        inner = (f'<div class="anchor" style="{self.pos(b, 0.5, 0.5)}"><div class="arrow" style="transform:rotate({ang}deg);'
                 f'font-size:{b.get("size", 150)}px;color:{b.get("color", self.th["accent"])}">➜</div></div>')
        js = (f"tl.fromTo('#{bid} .arrow', {{opacity:0, scale:0.3}}, {{opacity:1, scale:1, duration:0.3, ease:'back.out(2)'}}, T);"
              f"tl.to('#{bid} .anchor', {{x:'+=' + 30*Math.cos({ang}*Math.PI/180), y:'+=' + 30*Math.sin({ang}*Math.PI/180), duration:0.3, yoyo:true, repeat:Math.max(1, Math.floor((D-0.6)/0.3)), ease:'sine.inOut'}}, T + 0.3);")
        return inner, js

    def b_sticker(self, bid, b, s, e, total):
        rot = float(b.get("rotate", -8))
        bg = b.get("bg", self.th["accent"])
        inner = (f'<div class="anchor" style="{self.pos(b, 0.75, 0.2)}"><div class="sticker" style="background:{bg};'
                 f'color:{b.get("color", self.th["dark"])};font-size:{b.get("size", 64)}px;transform:rotate({rot}deg)">{rich(b["text"])}</div></div>')
        js = (f"tl.fromTo('#{bid} .sticker', {{scale:0}}, {{scale:1, duration:0.4, ease:'elastic.out(1, 0.5)'}}, T);"
              f"tl.to('#{bid} .sticker', {{scale:0, duration:0.2, ease:'back.in(2)'}}, T + D - 0.2);")
        return inner, js

    def b_burst(self, bid, b, s, e, total):
        rays = "".join(f'<div class="ray" style="transform:rotate({i * 30}deg)"></div>' for i in range(12))
        inner = f'<div class="anchor" style="{self.pos(b, 0.5, 0.3)}"><div class="burst" style="color:{b.get("color", self.th["accent"])}">{rays}</div></div>'
        js = (f"tl.fromTo('#{bid} .ray', {{scaleY:0, opacity:1}}, {{scaleY:1, duration:0.35, ease:'expo.out'}}, T);"
              f"tl.to('#{bid} .ray', {{opacity:0, duration:0.3}}, T + 0.35);"
              f"tl.fromTo('#{bid} .burst', {{rotation:0}}, {{rotation:20, duration:0.65, ease:'none'}}, T);")
        return inner, js

    def b_profile_card(self, bid, b, s, e, total):
        """Instagram uslubidagi profil kartochka: avatar, ism, @handle, Follow tugmasi."""
        avatar = self.asset(b["avatar"]) if b.get("avatar") else None
        img = (f'<img class="pc-av" src="{avatar}">' if avatar
               else f'<div class="pc-av pc-ph">{esc(str(b.get("name", "?"))[:1])}</div>')
        sub = f'<div class="pc-sub">{esc(b["subtitle"])}</div>' if b.get("subtitle") else ""
        inner = (f'<div class="anchor" style="{self.pos(b, 0.5, 0.5)}"><div class="pc">{img}'
                 f'<div class="pc-name">{esc(b.get("name", ""))}</div><div class="pc-handle">{esc(b.get("handle", ""))}</div>'
                 f'{sub}<div class="pc-btn" style="background:{b.get("button_color", self.th["accent"])}">'
                 f'{esc(b.get("button", "Follow"))}</div></div></div>')
        js = (f"tl.fromTo('#{bid} .pc', {{y:120, opacity:0, scale:0.92}}, {{y:0, opacity:1, scale:1, duration:0.35, ease:'power3.out'}}, T);"
              f"tl.fromTo('#{bid} .pc-btn', {{scale:1}}, {{scale:1.08, duration:0.3, yoyo:true, repeat:1, ease:'sine.inOut'}}, T + 0.5);")
        return inner, js

    def asset(self, path):
        """Rasm/video faylini kompozitsiya papkasiga ko'chirish uchun ro'yxatga oladi, nisbiy yo'lni qaytaradi."""
        src = resolve(path)
        name = f"a{len(self.assets)}_{src.name}"
        self.assets.append((src, name))
        return f"assets/{name}"

    def b_html(self, bid, b, s, e, total):
        src = resolve(b["file"]).read_text(encoding="utf-8")
        scripts = re.findall(r"<script>(.*?)</script>", src, flags=re.S)
        markup = re.sub(r"<script>.*?</script>", "", src, flags=re.S)
        return markup, f"const W = {self.W}, H = {self.H}; const root = document.getElementById('{bid}');" + "\n".join(scripts)

    # --- hujjat ---
    def document(self, total, fps):
        th = self.th
        font_faces = "".join(
            f"@font-face{{font-family:'{fam}';src:url('fonts/{f}');font-weight:{w};}}"
            for fam, f, w in [("Montserrat", "Montserrat-Black.ttf", 900), ("Montserrat", "Montserrat-ExtraBold.ttf", 800),
                              ("Montserrat", "Montserrat-SemiBold.ttf", 600), ("Bebas Neue", "BebasNeue-Regular.ttf", 400)])
        css = f"""{font_faces}
*{{margin:0;padding:0;box-sizing:border-box}}
html,body{{width:{self.W}px;height:{self.H}px;overflow:hidden;background:transparent}}
#root{{position:relative;width:100%;height:100%;font-family:'{th["font"]}','Segoe UI Emoji',sans-serif;font-weight:{th["weight"]};color:{th["text"]}}}
.clip{{position:absolute;inset:0}}
.anchor{{position:absolute;transform:translate(-50%,-50%);text-align:center;width:max-content;max-width:{self.W - 120}px;line-height:1.08}}
.w{{display:inline-block;margin:0 .08em}}
.outline .txt,.outline .num,.outline .label{{paint-order:stroke fill;-webkit-text-stroke:.22em #000;text-shadow:0 .07em .14em rgba(0,0,0,.55)}}
.box .txt{{background:{th["dark"]};padding:.18em .45em;border-radius:{th["radius"]}px;display:inline-block}}
.hl{{color:{th["accent"]}}}
.mk{{background-image:linear-gradient({th.get("marker", th["accent"])},{th.get("marker", th["accent"])});background-repeat:no-repeat;
     background-position:0 88%;background-size:0% 42%;padding:0 .06em}}
.mk.hl,.box .mk.hl{{color:{th["dark"]};background-position:0 50%}}
.mark{{width:100%;height:100%;overflow:visible;filter:drop-shadow(0 4px 6px rgba(0,0,0,.35))}}
.mark path{{fill:none;stroke-linejoin:round;stroke-dasharray:1 2;stroke-dashoffset:1}}
.box .hl{{color:{th["accent"]}}}
.num{{font-variant-numeric:tabular-nums;letter-spacing:-.02em}}
.label{{font-size:56px;margin-top:10px;font-weight:800}}
.emoji{{font-family:'Segoe UI Emoji','Apple Color Emoji','Noto Color Emoji';filter:drop-shadow(0 10px 18px rgba(0,0,0,.4))}}
.full{{position:absolute;inset:0}}
.bar-bg{{position:absolute;left:0;right:0;background:rgba(0,0,0,.35)}}
.bar{{position:absolute;left:0;right:0;transform-origin:left center}}
.lt{{position:absolute;left:70px;display:flex;align-items:stretch;gap:22px}}
.lt-bar{{width:14px;background:{th["accent"]};border-radius:7px;transform-origin:top}}
.lt-body{{background:rgba(0,0,0,.72);padding:22px 34px;border-radius:{th["radius"]}px}}
.lt-title{{font-size:62px;font-weight:900}}
.lt-sub{{font-size:40px;font-weight:600;opacity:.85;margin-top:6px}}
.list{{position:absolute;left:90px;right:90px;display:flex;flex-direction:column;gap:26px;font-weight:800}}
.li{{background:rgba(0,0,0,.7);padding:.35em .6em;border-radius:{th["radius"]}px;display:flex;gap:.5em;align-items:center}}
.ck{{color:{th["accent"]};font-family:'Segoe UI Symbol',sans-serif;font-variant-emoji:text}}
.cta{{background:{th["accent"]};color:{th["dark"]};font-size:66px;padding:.45em 1.1em;border-radius:999px;box-shadow:0 18px 40px rgba(0,0,0,.45);position:relative}}
.cta .hl{{background:{th["dark"]};color:{th["accent"]};padding:0 .28em;border-radius:.3em}}
.tap{{position:absolute;right:-.4em;bottom:-.7em;font-size:1.3em;font-family:'Segoe UI Emoji'}}
.arrow{{font-family:'Segoe UI Symbol',sans-serif;-webkit-text-stroke:6px #000;paint-order:stroke fill}}
.sticker{{padding:.3em .7em;border-radius:18px;font-weight:900;box-shadow:0 12px 26px rgba(0,0,0,.4)}}
.pc{{background:#fff;color:#111;border-radius:44px;padding:56px 70px 50px;width:640px;text-align:center;
     box-shadow:0 30px 70px rgba(0,0,0,.45);font-family:'Montserrat',sans-serif}}
.pc-av{{width:210px;height:210px;border-radius:50%;object-fit:cover;display:block;margin:0 auto 26px;
        border:6px solid #fff;box-shadow:0 0 0 5px {th["accent"]}}}
.pc-ph{{background:{th["accent"]};color:#fff;font-size:110px;line-height:210px;font-weight:900}}
.pc-name{{font-size:50px;font-weight:900}}
.pc-handle{{font-size:36px;font-weight:600;color:#666;margin-top:6px}}
.pc-sub{{font-size:32px;font-weight:600;color:#444;margin-top:14px}}
.pc-btn{{margin:34px auto 0;color:#fff;font-size:44px;font-weight:800;padding:20px 0;border-radius:18px;width:100%}}
.burst{{position:relative;width:0;height:0}}
.ray{{position:absolute;left:-7px;top:-330px;width:14px;height:200px;background:currentColor;border-radius:7px;transform-origin:7px 330px}}
"""
        body = "\n".join(self.html)
        js = "\n".join(self.js)
        return f"""<!doctype html>
<html lang="uz">
<head><meta charset="UTF-8"><meta name="viewport" content="width={self.W}, height={self.H}">
<script src="gsap.min.js"></script>
<style>{css}</style></head>
<body>
<div id="root" data-composition-id="main" data-start="0" data-duration="{total:.3f}" data-fps="{fps}"
     data-width="{self.W}" data-height="{self.H}">
{body}
</div>
<script>
window.__timelines = window.__timelines || {{}};
const tl = gsap.timeline({{paused: true}});
{js}
tl.set({{}}, {{}}, {total:.3f});
window.__timelines["main"] = tl;
tl.seek(0);
</script>
</body></html>
"""


def hf(args, cwd):
    env = dict(os.environ)
    env["PATH"] = f"{NODE_DIR};{TOOLS / 'ffmpeg' / 'bin'};" + env.get("PATH", "")
    env["HYPERFRAMES_SKIP_SKILLS"] = "1"
    cli = HF_DIR / "node_modules" / "hyperframes" / "bin" / "hyperframes.mjs"
    if not cli.exists() or not (NODE_DIR / "node.exe").exists():
        sys.exit("HyperFrames topilmadi. setup.ps1 ni ishga tushiring.")
    res = subprocess.run([str(NODE_DIR / "node.exe"), str(cli)] + [str(a) for a in args], cwd=cwd, env=env,
                         capture_output=True, text=True, encoding="utf-8", errors="replace")
    return res


def anim_dir(edit_path):
    """HyperFrames ichki papkalari juda chuqur - Windows'ning 260 belgilik chegarasiga tushmaslik uchun
    kompozitsiya qisqa yo'lda yasaladi: %USERPROFILE%\\.ai-montaj\\anim\\<nom>-<xesh>"""
    key = hashlib.sha1(str(edit_path.resolve()).encode()).hexdigest()[:8]
    return TOOLS / "anim" / f"{edit_path.parent.name}-{edit_path.stem.replace('.edit', '')}-{key}"


def build(edit_path, snapshot=None):
    work = edit_path.parent
    edit = load_json(edit_path)
    tl_path = edit_files(edit_path)["timeline_json"]
    if not tl_path.exists():
        sys.exit(f"Avval vaqt jadvalini yarating: render.py {edit_path.name} --timeline-only")
    tl_data = load_json(tl_path)
    total, fps = tl_data["duration"], tl_data["fps"]
    W, H = tl_data.get("width", 1080), tl_data.get("height", 1920)
    # "remotion" bloklari alohida qatlamda (remotion_layer.py)
    blocks = [b for b in (edit.get("animations") or []) if b.get("type") != "remotion"]
    if not blocks:
        print("Animatsiya bloklari yo'q.")
        return None
    theme = {**DEFAULT_THEME, **(edit.get("theme") or {})}

    b = Builder(W, H, theme)
    for blk in blocks:
        b.add(blk, total)
    doc = b.document(total, fps)

    anim = anim_dir(edit_path)
    anim.mkdir(parents=True, exist_ok=True)
    (anim / "index.html").write_text(doc, encoding="utf-8")
    shutil.copy2(HF_DIR / "node_modules" / "gsap" / "dist" / "gsap.min.js", anim / "gsap.min.js")
    (anim / "fonts").mkdir(exist_ok=True)
    for f in FONTS.glob("*.ttf"):
        if not (anim / "fonts" / f.name).exists():
            shutil.copy2(f, anim / "fonts" / f.name)
    save_json({"id": "anim", "name": work.name}, anim / "meta.json")
    if b.assets:
        (anim / "assets").mkdir(exist_ok=True)
        for src, name in b.assets:
            shutil.copy2(src, anim / "assets" / name)
            doc += f"<!-- {name} {src.stat().st_size} {src.stat().st_mtime} -->"  # kesh xeshi uchun

    if snapshot:
        snaps = anim / ".hyperframes"
        shutil.rmtree(snaps, ignore_errors=True)
        res = hf(["snapshot", ".", "--at", ",".join(str(s) for s in snapshot)], anim)
        # nomlar: frame-00-at-1s.png ... - tartib --at ro'yxati bilan bir xil
        pngs = sorted(snaps.rglob("frame-*.png"), key=lambda p: p.name) if snaps.exists() else []
        if not pngs:
            sys.exit(f"Snapshot xatosi:\n{res.stdout[-2000:]}\n{res.stderr[-2000:]}")
        out = work / "anim_snapshots"
        shutil.rmtree(out, ignore_errors=True)
        out.mkdir()
        for p in pngs:
            shutil.copy2(p, out / p.name)
            print(out / p.name)
        return [out / p.name for p in pngs]

    digest = hashlib.sha1((doc + str(fps)).encode()).hexdigest()
    frames = anim / "frames"
    stamp = anim / "frames.sha1"
    if frames.exists() and stamp.exists() and stamp.read_text() == digest and any(frames.glob("*.png")):
        print("Animatsiya o'zgarmagan - oldingi kadrlar ishlatiladi.")
        return frames
    shutil.rmtree(frames, ignore_errors=True)
    t0 = time.time()
    print(f"HyperFrames render: {len(blocks)} blok, {total:.1f} s, {fps} fps...", flush=True)
    res = hf(["render", ".", "--format", "png-sequence", "-o", "frames", "--fps", fps, "--workers", "4", "--quiet"], anim)
    pngs = sorted(frames.rglob("*.png")) if frames.exists() else []
    if res.returncode != 0 or not pngs:
        sys.exit(f"HyperFrames xatosi:\n{res.stdout[-3000:]}\n{res.stderr[-3000:]}")
    stamp.write_text(digest)
    print(f"Animatsiya tayyor ({time.time() - t0:.0f} s): {len(pngs)} kadr")
    return frames


def frame_pattern(frames):
    """PNG nomlaridan FFmpeg uchun naqsh (masalan frame_%05d.png) va boshlang'ich raqam."""
    pngs = sorted(frames.rglob("*.png"))
    first = pngs[0]
    m = re.match(r"^(.*?)(\d+)(\.png)$", first.name)
    pattern = f"{m.group(1)}%0{len(m.group(2))}d{m.group(3)}"
    return first.parent / pattern, int(m.group(2))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("edit")
    ap.add_argument("--snapshot", nargs="*", type=float)
    args = ap.parse_args()
    build(resolve(args.edit), snapshot=args.snapshot)


if __name__ == "__main__":
    main()
