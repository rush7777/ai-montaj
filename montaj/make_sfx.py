"""Montaj uchun litsenziyasiz SFX ovozlarini FFmpeg bilan sintez qiladi: assets/sfx/synth/*.wav
Kenney (CC0) to'plamlarini to'ldiradi: whoosh, riser, sub-drop, ka-ching, kamera, yozuv mashinkasi va h.k.

Misol:
    python montaj/make_sfx.py
"""
from common import ROOT, run_ffmpeg


def tone(expr, d):
    return f"aevalsrc='{expr}':s=48000:d={d}"


def noise(color, d, chain, amp=0.7):
    return f"anoisesrc=color={color}:a={amp}:d={d}:r=48000,{chain}"


SOUNDS = {
    # pop / click
    "pop_low": tone("0.8*sin(2*PI*(300+1200*exp(-40*t))*t)*exp(-26*t)", 0.2),
    "pop": tone("0.8*sin(2*PI*(500+1800*exp(-40*t))*t)*exp(-28*t)", 0.18),
    "pop_high": tone("0.75*sin(2*PI*(900+2600*exp(-45*t))*t)*exp(-32*t)", 0.15),
    "bubble": tone("0.7*sin(2*PI*(400+900*t*8)*t)*exp(-22*t)", 0.18),
    "click": tone("0.7*sin(2*PI*2400*t)*exp(-90*t)", 0.06),
    "tick": tone("0.6*sin(2*PI*4200*t)*exp(-140*t)", 0.04),
    "typewriter": noise("white", 0.07, "highpass=f=2500,afade=t=out:st=0:d=0.07:curve=exp", 0.9),
    # ding / notification / money
    "ding": tone("0.45*(sin(2*PI*1320*t)+0.35*sin(2*PI*2640*t)+0.15*sin(2*PI*3960*t))*exp(-4.5*t)", 1.2),
    "ding_soft": tone("0.4*(sin(2*PI*880*t)+0.3*sin(2*PI*1760*t))*exp(-5*t)", 1.0),
    "notification": tone("0.45*(sin(2*PI*988*t)*lt(t,0.12)+sin(2*PI*1319*t)*gte(t,0.12))*exp(-6*(t-0.12*gte(t,0.12)))", 0.7),
    "success": tone("0.4*(sin(2*PI*523*t)*lt(t,0.1)+sin(2*PI*659*t)*between(t,0.1,0.2)+sin(2*PI*784*t)*gte(t,0.2))*exp(-3*t)", 0.9),
    "error": tone("0.5*sin(2*PI*180*t)*(lt(t,0.12)+between(t,0.18,0.3))", 0.32),
    "kaching": tone("0.5*(sin(2*PI*2093*t)+0.5*sin(2*PI*3136*t))*exp(-6*t)*gte(t,0.08)"
                    "+0.6*sin(2*PI*700*t)*exp(-60*t)*lt(t,0.08)", 1.1),
    "coin": tone("0.45*(sin(2*PI*1975*t)*lt(t,0.07)+sin(2*PI*2637*t)*gte(t,0.07))*exp(-7*t)", 0.6),
    # whoosh / swipe / transition
    "whoosh": noise("pink", 0.7, "bandpass=f=1400:width_type=h:w=1800,afade=t=in:d=0.35:curve=exp,"
                                 "afade=t=out:st=0.35:d=0.35:curve=exp"),
    "whoosh_short": noise("pink", 0.35, "bandpass=f=2000:width_type=h:w=2500,afade=t=in:d=0.15:curve=exp,"
                                        "afade=t=out:st=0.15:d=0.2:curve=exp"),
    "whoosh_deep": noise("brown", 0.9, "lowpass=f=900,afade=t=in:d=0.45:curve=exp,"
                                       "afade=t=out:st=0.45:d=0.45:curve=exp", 0.9),
    "swipe": noise("white", 0.25, "highpass=f=3000,afade=t=in:d=0.08,afade=t=out:st=0.08:d=0.17:curve=exp", 0.5),
    "rise": noise("white", 1.5, "highpass=f=600,afade=t=in:d=1.4:curve=exp,afade=t=out:st=1.4:d=0.1", 0.35),
    "riser_long": tone("0.35*sin(2*PI*(200*t+300*t*t))*(t/3)+0.0", 3.0),
    "reverse_swell": noise("pink", 1.2, "lowpass=f=4000,afade=t=in:d=1.15:curve=qsin,afade=t=out:st=1.15:d=0.05", 0.6),
    "tape_stop": tone("0.6*sin(2*PI*(220*t-90*t*t))*(1-t/1.1)", 1.1),
    "glitch": tone("0.5*sin(2*PI*(600+400*sin(2*PI*30*t))*t)*gt(sin(2*PI*17*t),0)", 0.35),
    # impact / boom
    "boom": tone("0.95*sin(2*PI*(45+140*exp(-9*t))*t)*exp(-3.5*t)", 1.4),
    "sub_drop": tone("0.95*sin(2*PI*(30+90*exp(-3*t))*t)*exp(-1.8*t)", 2.0),
    "bass_hit": tone("0.9*sin(2*PI*(55+200*exp(-25*t))*t)*exp(-6*t)", 0.7),
    "punch": tone("0.9*sin(2*PI*(80+300*exp(-35*t))*t)*exp(-12*t)", 0.4),
    "heartbeat": tone("0.9*sin(2*PI*55*t)*(exp(-25*t)+exp(-25*(t-0.28))*gte(t,0.28))", 0.9),
    # kamera
    "camera_shutter": noise("white", 0.12, "highpass=f=1500,afade=t=out:st=0:d=0.12:curve=exp", 0.8),
}


def main():
    out = ROOT / "assets" / "sfx" / "synth"
    out.mkdir(parents=True, exist_ok=True)
    for name, src in SOUNDS.items():
        run_ffmpeg(["-f", "lavfi", "-i", src, "-af", "alimiter=limit=0.95", "-ac", "2", out / f"{name}.wav"])
    print(f"{len(SOUNDS)} ta ovoz: {out}")


if __name__ == "__main__":
    main()
