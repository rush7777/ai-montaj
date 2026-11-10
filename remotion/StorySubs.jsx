// "Hikoya" subtitrlari (Azizon uslubi): ingichka serif kursiv, so'zlar gapirilgan paytda birma-bir yumshoq chiqadi
// (shaffoflik + xiralik), kalit so'z tik va kattaroq, ba'zi so'zlar tagiga sariq chiziq chiziladi.
// props.chunks: [{start, end, lines: [[{w, s, emph, ul}]], color?, y?, size?, shadow?}] - vaqtlar butun video bo'yicha
// props.style: {y: 0.70, size: 64, color, emph_scale: 1.3, underline: '#E2B93B', font, italic, weight, emph_color, emph_weight}
import {AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import {clamp, reveal, STORY, uz} from './StoryKit';

const Word = ({wd, frame, fps, st, color, size, s}) => {
  const big = wd.emph;
  const r = reveal(frame, fps, wd.s, 0.24, 8);
  const ulP = interpolate(frame, [(wd.s + 0.25) * fps, (wd.s + 0.6) * fps], [0, 1], clamp);
  return (
    <span style={{position: 'relative', display: 'inline-block', margin: `0 ${0.13 * size * s}px`,
      fontStyle: big || !st.italic ? 'normal' : 'italic', fontSize: (big ? st.emph_scale : 1) * size * s,
      fontWeight: big ? (st.emph_weight ?? st.weight) : st.weight, color: big && st.emph_color ? st.emph_color : undefined,
      lineHeight: 1, ...r}}>
      {uz(wd.w)}
      {wd.ul ? (
        <svg viewBox="0 0 100 12" preserveAspectRatio="none" style={{position: 'absolute', left: '-4%', width: '108%',
          bottom: -0.16 * size * s, height: 0.2 * size * s, overflow: 'visible'}}>
          <path d="M2 7 Q 50 11 98 4" fill="none" stroke={st.underline} strokeWidth={4} strokeLinecap="round"
            vectorEffect="non-scaling-stroke" pathLength={1} strokeDasharray={1} strokeDashoffset={1 - ulP}
            style={{strokeWidth: Math.max(3, 0.07 * size * s)}} />
        </svg>
      ) : null}
    </span>
  );
};

export const StorySubs = ({chunks = [], style = {}}) => {
  const frame = useCurrentFrame();
  const {fps, width, height} = useVideoConfig();
  const s = width / 1080;
  const t = frame / fps;
  const st = {y: 0.70, size: 64, color: '#FFFFFF', emph_scale: 1.3, underline: STORY.gold, fade_out: 0.18,
    font: STORY.serif, italic: true, weight: 400, ...style};
  const active = chunks.filter((c) => t >= c.start - 0.05 && t < c.end + st.fade_out);
  return (
    <AbsoluteFill style={{fontFamily: st.font}}>
      {active.map((c, ci) => {
        const out = interpolate(t, [c.end, c.end + st.fade_out], [1, 0], clamp);
        const color = c.color || st.color;
        const size = c.size || st.size;
        const dark = color.toLowerCase() !== '#ffffff';
        const shadow = c.shadow ?? !dark;
        return (
          <div key={ci} style={{position: 'absolute', left: 0, right: 0, top: height * (c.y ?? st.y),
            transform: 'translateY(-50%)', textAlign: 'center', color, opacity: out,
            filter: out < 1 ? `blur(${(1 - out) * 6}px)` : 'none',
            textShadow: shadow ? '0 2px 14px rgba(0,0,0,.55), 0 0 2px rgba(0,0,0,.35)' : 'none'}}>
            {c.lines.map((line, li) => (
              <div key={li} style={{display: 'flex', justifyContent: 'center', alignItems: 'baseline',
                flexWrap: 'wrap', padding: `0 ${70 * s}px`, marginTop: li ? 0.12 * size * s : 0}}>
                {line.map((wd, wi) => <Word key={wi} wd={wd} frame={frame} fps={fps} st={st} color={color}
                  size={size} s={s} />)}
              </div>
            ))}
          </div>
        );
      })}
    </AbsoluteFill>
  );
};
