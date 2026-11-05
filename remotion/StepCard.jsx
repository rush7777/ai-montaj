// Qadam kartochkasi (split-screen): kadrning yuqori qismi qora panel - "Qadam N. Sarlavha", katta ikonka yoki
// ro'yxat va izoh; pastki qismida gapiruvchi ko'rinib turadi.
// props: step, title, icon, caption, items (ro'yxat, ikonka o'rniga), panel (balandlik ulushi, 0.5), theme
import {AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {parseRich, THEME} from './fonts';

const Rich = ({text, accent}) => parseRich(text).map((p, i) =>
  <span key={i} style={{color: p.accent ? accent : undefined}}>{p.text}</span>);

export const StepCard = ({step, title, icon, caption, items, panel = 0.5, theme = {}}) => {
  const frame = useCurrentFrame();
  const {fps, width, height, durationInFrames} = useVideoConfig();
  const th = {...THEME, ...theme};
  const ph = height * panel;
  const pop = (delay, cfg = {damping: 14, mass: 0.7}) => spring({frame: frame - delay * fps, fps, config: cfg});
  // panel yuqoridan tushadi, oxirida yuqoriga qaytadi
  const inP = spring({frame, fps, config: {damping: 20, mass: 0.8}});
  const outP = interpolate(frame, [durationInFrames - 0.3 * fps, durationInFrames], [0, 1],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const y = (inP - 1 - outP) * ph;
  const s = width / 1080;

  return (
    <AbsoluteFill>
      <div style={{position: 'absolute', left: 0, top: y, width, height: ph, overflow: 'hidden',
        background: `radial-gradient(120% 80% at 50% 30%, #262626 0%, ${th.panel} 60%, #0b0b0b 100%)`,
        boxShadow: '0 18px 50px rgba(0,0,0,.55)', fontFamily: 'Montserrat'}}>
        <div style={{position: 'absolute', top: ph * 0.12, width: '100%', textAlign: 'center', fontWeight: 800,
          fontSize: 54 * s, color: th.text, opacity: pop(0.1), transform: `translateY(${(1 - pop(0.1)) * 30}px)`}}>
          {step != null && <span style={{color: th.accent}}>Qadam {step}. </span>}{title}
        </div>
        {items ? (
          <div style={{position: 'absolute', top: ph * 0.3, left: width * 0.12, width: width * 0.76}}>
            {items.map((it, i) => {
              const p = pop(0.35 + i * 0.28);
              return (
                <div key={i} style={{display: 'flex', alignItems: 'center', gap: 22 * s, marginBottom: 22 * s,
                  padding: `${18 * s}px ${28 * s}px`, borderRadius: 22 * s, background: 'rgba(255,255,255,.07)',
                  border: '1px solid rgba(255,255,255,.12)', fontSize: 44 * s, fontWeight: 800, color: th.text,
                  opacity: p, transform: `translateX(${(1 - p) * -80}px)`}}>
                  <span style={{color: th.accent}}>✓</span><span><Rich text={it} accent={th.accent} /></span>
                </div>
              );
            })}
          </div>
        ) : (
          <div style={{position: 'absolute', top: ph * 0.3, width: '100%', display: 'flex', justifyContent: 'center'}}>
            <div style={{width: 230 * s, height: 230 * s, borderRadius: 52 * s, display: 'flex', alignItems: 'center',
              justifyContent: 'center', fontSize: 140 * s, background: 'rgba(255,255,255,.06)',
              border: `3px solid ${th.accent}`, boxShadow: `0 0 60px ${th.accent}55`,
              transform: `scale(${pop(0.3, {damping: 9, mass: 0.6})}) rotate(${interpolate(frame, [0, durationInFrames], [-4, 4])}deg)`}}>
              {icon}
            </div>
          </div>
        )}
        {caption && (
          <div style={{position: 'absolute', top: ph * 0.8, width: '100%', textAlign: 'center', fontWeight: 600,
            fontSize: 46 * s, color: th.text, opacity: pop(0.6), transform: `translateY(${(1 - pop(0.6)) * 24}px)`}}>
            <Rich text={caption} accent={th.accent} />
          </div>
        )}
      </div>
    </AbsoluteFill>
  );
};
