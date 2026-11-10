// Katta so'z (Azizon: "GO'SHT", "KO'CHADAN"): baland ingichka qalin harflar, kadr tepasida.
// edit.json da "layer": "behind" bo'lsa, odam (boshi, yelkasi) so'z USTIDA turadi - render.py MediaPipe niqobi bilan.
// props: text, at (s), y (markaz, kadr ulushi), size (px, 1080 kenglikda), color, spacing, font ('Bebas Neue'|'Montserrat')
import {AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import {clamp, uz} from './StoryKit';

export const BigWord = ({text = '', at = 0, y = 0.2, size = 300, color = '#F4EFE6', spacing = 0.01,
  font = 'Bebas Neue', out = 0.3, fit = 0.94}) => {
  const frame = useCurrentFrame();
  const {fps, width, durationInFrames} = useVideoConfig();
  const s = width / 1080;
  const em = font === 'Bebas Neue' && !/[Ѐ-ӿ]/.test(text) ? 0.40 : 0.62;
  const fs = Math.min(size, (fit * 1080) / Math.max(1, uz(text).length * (em + spacing)));
  const p = interpolate(frame, [at * fps, (at + 0.35) * fps], [0, 1], clamp);
  const e = 1 - Math.pow(1 - p, 3);
  const fo = interpolate(frame, [durationInFrames - out * fps, durationInFrames], [1, 0], clamp);
  return (
    <AbsoluteFill>
      <div style={{position: 'absolute', left: 0, right: 0, top: y * 1920 * s, transform: `translateY(-50%) scale(${1.06 - 0.06 * e})`,
        textAlign: 'center', fontFamily: font, fontWeight: font === 'Montserrat' ? 900 : 400, fontSize: fs * s,
        lineHeight: 0.9, letterSpacing: `${spacing}em`, color, opacity: e * fo, filter: `blur(${(1 - e) * 10}px)`,
        whiteSpace: 'nowrap', textShadow: '0 10px 40px rgba(0,0,0,.18)'}}>
        {uz(text)}
      </div>
    </AbsoluteFill>
  );
};
