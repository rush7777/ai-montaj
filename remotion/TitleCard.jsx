// Kinetik sarlavha: so'zlar birma-bir prujina bilan chiqadi, "*so'z*" aksent plashkada. "\n" - yangi qator.
// props: text, y (markaz, kadr ulushi, 0.2), size (96), stagger (so'zlar orasi, s), theme
import {AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {parseRich, THEME} from './fonts';

export const TitleCard = ({text, y = 0.2, size = 96, stagger = 0.09, theme = {}}) => {
  const frame = useCurrentFrame();
  const {fps, width, height, durationInFrames} = useVideoConfig();
  const th = {...THEME, ...theme};
  const s = width / 1080;
  const out = interpolate(frame, [durationInFrames - 0.25 * fps, durationInFrames], [1, 0],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  let k = 0;
  const lines = String(text).split('\n').map((line) => parseRich(line).flatMap((p) =>
    p.text.split(/\s+/).filter(Boolean).map((w) => ({w, accent: p.accent, i: k++}))));

  return (
    <AbsoluteFill style={{fontFamily: 'Montserrat', fontWeight: 900, opacity: out}}>
      <div style={{position: 'absolute', top: height * y, width: '100%', transform: 'translateY(-50%)',
        textAlign: 'center', lineHeight: 1.15}}>
        {lines.map((ws, li) => (
          <div key={li} style={{marginBottom: 8 * s}}>
            {ws.map(({w, accent, i}) => {
              const p = spring({frame: frame - i * stagger * fps, fps, config: {damping: 11, mass: 0.6}});
              return (
                <span key={i} style={{display: 'inline-block', margin: `0 ${12 * s}px`, fontSize: size * s,
                  color: accent ? th.dark : th.text, background: accent ? th.accent : 'transparent',
                  padding: accent ? `0 ${16 * s}px` : 0, borderRadius: 14 * s,
                  textShadow: accent ? 'none' : '0 6px 24px rgba(0,0,0,.6), 0 0 3px #000',
                  opacity: Math.min(1, p * 1.4), transform: `translateY(${(1 - p) * 60}px) scale(${0.6 + 0.4 * p})`}}>
                  {w}
                </span>
              );
            })}
          </div>
        ))}
      </div>
    </AbsoluteFill>
  );
};
