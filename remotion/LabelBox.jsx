// Sariq yorliq qutisi (Azizon: "Bundan 4-5 yil oldin"): avval quti chapdan ochiladi, keyin matn harfma-harf yoziladi.
// props: text ("\n" - yangi qator), at (s), x, y (chap-yuqori burchak, kadr ulushi), w (kenglik ulushi),
//        size, bg, color, cps (soniyasiga harf), font ('serif'|'sans')
import {AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import {clamp, STORY, uz} from './StoryKit';

export const LabelBox = ({text: raw = '', at = 0, x = 0.07, y = 0.2, w = 0.6, size = 58, bg = STORY.gold,
  color = '#1E1A16', cps = 22, font = 'serif'}) => {
  const frame = useCurrentFrame();
  const text = uz(raw);
  const {fps, width, durationInFrames} = useVideoConfig();
  const s = width / 1080;
  const open = interpolate(frame, [at * fps, (at + 0.28) * fps], [0, 1], clamp);
  const n = Math.floor(Math.max(0, frame / fps - at - 0.25) * cps);
  const out = interpolate(frame, [durationInFrames - 0.25 * fps, durationInFrames], [1, 0], clamp);
  return (
    <AbsoluteFill style={{opacity: out}}>
      <div style={{position: 'absolute', left: x * width, top: y * 1920 * s, width: w * width,
        background: bg, transformOrigin: '0 50%', transform: `scaleX(${1 - Math.pow(1 - open, 3)})`,
        padding: `${16 * s}px ${26 * s}px`, boxSizing: 'border-box', minHeight: size * 1.5 * s,
        boxShadow: '0 10px 30px rgba(0,0,0,.25)'}}>
        <div style={{fontFamily: font === 'serif' ? STORY.serif : STORY.sans, fontStyle: font === 'serif' ? 'italic' : 'normal',
          fontWeight: font === 'serif' ? 400 : 700, fontSize: size * s, lineHeight: 1.0, color, whiteSpace: 'pre-wrap'}}>
          {text.slice(0, n)}
          <span style={{opacity: 0}}>{text.slice(n)}</span>
        </div>
      </div>
    </AbsoluteFill>
  );
};
