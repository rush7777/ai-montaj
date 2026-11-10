// Devor sahnasi (Azizon uslubi): krem devor, deraza soyasi, vignette. Ustida: savol/xulosa matni, devordagi kartina
// (tilla ramka) yoki predmet (soyali), qo'lda chizilgan X/doira, oxirida brend nomi va shior "pill".
// props:
//   lines: [{text, at, kind: 'serif'|'title'|'kicker'|'brand', y, size, color, stagger}]  - "*so'z*" tik va kattaroq
//   image: {src, style: 'frame'|'object'|'plain', x, y, w, h, at}
//   mark:  {shape: 'cross'|'circle'|'check'|'underline', at, x, y, w, h, color, draw}
//   pill:  {text, at, y}
//   zoom_into: {at, x, y, dur}  - oxirida kamera kartina ichiga kirib ketadi (keyingi B-roll'ga o'tish)
//   fade_in, fade_out (s), push (devorning sekin yaqinlashishi)
import {AbsoluteFill, Img, interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import {clamp, GoldFrame, HandMark, reveal, src as media, STORY, uz, WallBg} from './StoryKit';

const KIND = {
  serif: {font: STORY.serif, italic: true, size: 64, color: STORY.ink},
  title: {font: STORY.serif, italic: false, size: 104, color: STORY.brand},
  kicker: {font: STORY.sans, italic: false, size: 34, color: STORY.muted, weight: 600},
  brand: {font: STORY.serif, italic: false, size: 132, color: '#1C1713'},
};

const Line = ({ln, frame, fps, s}) => {
  const k = {...KIND[ln.kind || 'serif'], ...(ln.size ? {size: ln.size} : {}), ...(ln.color ? {color: ln.color} : {})};
  const stagger = ln.stagger ?? 0.16;
  let i = 0;
  const parts = uz(ln.text).split(/(\*[^*]+\*)/).filter(Boolean).flatMap((p) => {
    const emph = p.startsWith('*') && p.endsWith('*');
    return (emph ? p.slice(1, -1) : p).split(/\s+/).filter(Boolean).map((w) => ({w, emph, i: i++}));
  });
  return (
    <div style={{position: 'absolute', left: 0, right: 0, top: 1920 * s * (ln.y ?? 0.4), transform: 'translateY(-50%)',
      textAlign: 'center', color: k.color, fontFamily: k.font, fontWeight: k.weight || 400, padding: `0 ${80 * s}px`}}>
      {parts.map(({w, emph, i: n}) => (
        <span key={n} style={{display: 'inline-block', margin: `0 ${0.12 * k.size * s}px`,
          fontStyle: k.italic && !emph ? 'italic' : 'normal', fontSize: (emph ? 1.3 : 1) * k.size * s, lineHeight: 1.05,
          ...reveal(frame, fps, (ln.at ?? 0) + n * stagger, 0.3, 10)}}>{w}</span>
      ))}
    </div>
  );
};

export const WallCard = ({lines = [], image = null, mark = null, pill = null, zoom_into = null, fade_in = 0,
  fade_out = 0, push = 0.03}) => {
  const frame = useCurrentFrame();
  const {fps, width, durationInFrames} = useVideoConfig();
  const s = width / 1080;
  const t = frame / fps;
  const fin = fade_in ? interpolate(frame, [0, fade_in * fps], [0, 1], clamp) : 1;
  const fout = fade_out ? interpolate(frame, [durationInFrames - fade_out * fps, durationInFrames], [1, 0], clamp) : 1;
  let cam = 'none', camBlur = 0, origin = '50% 50%';
  if (zoom_into) {
    const at = zoom_into.at ?? Math.max(0, durationInFrames / fps - 0.5);
    const p = interpolate(t, [at, at + (zoom_into.dur ?? 0.45)], [0, 1], clamp);
    const e = p * p * (3 - 2 * p);
    cam = `scale(${1 + e * (zoom_into.scale ?? 3.4)})`;
    camBlur = e * 10;
    origin = `${(zoom_into.x ?? image?.x ?? 0.5) * 100}% ${(zoom_into.y ?? image?.y ?? 0.3) * 100}%`;
  }
  let img = null;
  if (image && image.src) {
    const r = reveal(frame, fps, image.at ?? 0, 0.4, 18);
    const w = (image.w ?? 0.42) * 1080 * s;
    const h = (image.h ?? (image.style === 'frame' ? 0.21 : 0.22)) * 1920 * s;
    const pic = <Img src={media(image.src)} style={{width: '100%', height: '100%', objectFit: image.style === 'object' ? 'contain' : 'cover'}} />;
    img = (
      <div style={{position: 'absolute', left: (image.x ?? 0.5) * 1080 * s, top: (image.y ?? 0.3) * 1920 * s,
        transform: `translate(-50%, -50%) ${r.transform}`, opacity: r.opacity, filter: r.filter,
        width: w, height: h}}>
        {image.style === 'frame' ? <GoldFrame w={w} h={h} border={30 * s}>{pic}</GoldFrame>
          : <div style={{width: '100%', height: '100%',
            filter: image.style === 'object' ? 'drop-shadow(0 30px 28px rgba(50,35,20,.35))' : 'none'}}>{pic}</div>}
      </div>
    );
  }
  let pl = null;
  if (pill && pill.text) {
    const r = reveal(frame, fps, pill.at ?? 0.6, 0.35, 8);
    pl = (
      <div style={{position: 'absolute', left: 0, right: 0, top: 1920 * s * (pill.y ?? 0.555), display: 'flex',
        justifyContent: 'center', ...r}}>
        <div style={{fontFamily: STORY.sans, fontWeight: 600, fontSize: 30 * s, color: STORY.brand,
          background: 'rgba(250,246,238,.92)', borderRadius: 999, padding: `${12 * s}px ${30 * s}px`,
          boxShadow: '0 6px 18px rgba(60,40,20,.18), inset 0 0 0 1px rgba(120,90,60,.12)'}}>{uz(pill.text)}</div>
      </div>
    );
  }
  return (
    <AbsoluteFill style={{opacity: Math.min(fin, fout), overflow: 'hidden'}}>
      <div style={{position: 'absolute', inset: 0, transform: cam, transformOrigin: origin,
        filter: camBlur ? `blur(${camBlur}px)` : 'none'}}>
        <WallBg push={push} />
        {img}
        {mark ? <HandMark {...{color: STORY.red, stroke: 9, w: 0.42, h: 0.14, ...mark}} /> : null}
        {lines.map((ln, i) => <Line key={i} ln={ln} frame={frame} fps={fps} s={s} />)}
        {pl}
      </div>
    </AbsoluteFill>
  );
};
