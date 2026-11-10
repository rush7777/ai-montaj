// Kichik tugma-yorliq: "🔖 Saqlab qo'ying" (oq), "Obuna bo'ling" (ko'k) - kadr tepasida prujina bilan chiqadi.
// props: text, icon, at (s), y (markaz, 0.075), bg ('#FFFFFF'), color ('#111'), size (30)
import {AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {clamp, uz} from './StoryKit';

export const PillTag = ({text = '', icon = '', at = 0, y = 0.075, bg = '#FFFFFF', color = '#111111', size = 30}) => {
  const frame = useCurrentFrame();
  const {fps, width, durationInFrames} = useVideoConfig();
  const s = width / 1080;
  if (frame < at * fps) return null;
  const p = spring({frame: frame - at * fps, fps, config: {damping: 12, mass: 0.6}});
  const out = interpolate(frame, [durationInFrames - 0.25 * fps, durationInFrames], [1, 0], clamp);
  return (
    <AbsoluteFill>
      <div style={{position: 'absolute', left: 0, right: 0, top: y * 1920 * s, display: 'flex', justifyContent: 'center',
        transform: `translateY(-50%) scale(${0.6 + 0.4 * p})`, opacity: Math.min(1, p * 1.5) * out}}>
        <div style={{background: bg, color, fontFamily: 'Montserrat', fontWeight: 700, fontSize: size * s, borderRadius: 999,
          padding: `${12 * s}px ${30 * s}px`, boxShadow: '0 8px 24px rgba(0,0,0,.3)', display: 'flex', gap: 10 * s, alignItems: 'center'}}>
          {icon ? <span>{icon}</span> : null}{uz(text)}
        </div>
      </div>
    </AbsoluteFill>
  );
};
