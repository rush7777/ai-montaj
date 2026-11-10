// Qadamma-qadam gaid paneli (referens: ruscha "ИИ-монтажёр за 4 шага"): kadrning yuqori yarmi to'q panel,
// tepada "Qadam N." (aksent) + sarlavha, o'rtada sxema elementlari nutq bilan birga birma-bir yig'iladi.
// Pastki yarmida gapiruvchi (A-roll bo'lagida "shift_y" bilan yuz pastga suriladi).
// props:
//   step, title, panel (0.5), accent ('#F5A623'), enter (true - panel tepadan tushadi), exit (true)
//   elements: [{kind, at, until, ...}]  (at/until - blok boshidan soniya)
//     icon:   {icons: [{emoji | src | folder: true, label, at}], y}
//     window: {title, text, cps (28), y, h}                - oq ilova oynasi, matn harfma-harf yoziladi
//     tree:   {root, children: [..], times: [..], y}        - papka daraxti: ildiz + shoxlar
//     chips:  {items: [{text, at, kind: 'ask'|'reply'}]}    - sariq so'rov va oq javob pufakchalari
//     list:   {items: [{text, at}], y}                      - belgili ro'yxat
//     card:   {title, rows: [[nom, qiymat]], colors: [..]}  - brendbuk kartochkasi
import {AbsoluteFill, Img, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {clamp, src as media, uz} from './StoryKit';

const F = 'Montserrat';

const Folder = ({w = 120, color = '#5AB8F5'}) => (
  <svg width={w} height={w * 0.78} viewBox="0 0 100 78">
    <path d="M4 10 Q4 4 10 4 L36 4 Q40 4 43 8 L48 14 L90 14 Q96 14 96 20 L96 70 Q96 76 90 76 L10 76 Q4 76 4 70 Z" fill={color} />
    <path d="M4 24 L96 24 L96 70 Q96 76 90 76 L10 76 Q4 76 4 70 Z" fill="#7CCBFA" />
  </svg>
);

const useIn = (frame, fps, at, until, total) => {
  const p = spring({frame: frame - at * fps, fps, config: {damping: 15, mass: 0.6}});
  const end = until ?? total;
  const o = interpolate(frame, [end * fps - 6, end * fps], [1, 0], clamp);
  return {p: frame < at * fps ? 0 : p, o};
};

const Icon = ({it, frame, fps, s}) => {
  const p = spring({frame: frame - (it.at ?? 0) * fps, fps, config: {damping: 13, mass: 0.6}});
  if (frame < (it.at ?? 0) * fps) return null;
  return (
    <div style={{display: 'flex', flexDirection: 'column', alignItems: 'center', margin: `0 ${26 * s}px`,
      transform: `scale(${0.5 + 0.5 * p})`, opacity: Math.min(1, p * 1.5)}}>
      {it.folder ? <Folder w={130 * s} /> : it.src
        ? <Img src={media(it.src)} style={{width: 130 * s, height: 130 * s, borderRadius: 30 * s, objectFit: 'cover'}} />
        : <div style={{width: 130 * s, height: 130 * s, borderRadius: 30 * s, background: it.bg || '#E8643B',
          display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 76 * s}}>{it.emoji}</div>}
      {it.label ? <div style={{marginTop: 14 * s, fontFamily: F, fontWeight: 600, fontSize: 26 * s, color: '#E8E8E8'}}>{uz(it.label)}</div> : null}
      {it.note ? <div style={{marginTop: 6 * s, fontFamily: F, fontWeight: 600, fontSize: 22 * s, color: '#F5A623'}}>{uz(it.note)}</div> : null}
    </div>
  );
};

const Element = ({el, frame, fps, s, W, ph, accent, total}) => {
  const {p, o} = useIn(frame, fps, el.at ?? 0, el.until, total);
  if (p <= 0 || o <= 0) return null;
  const cy = (el.y ?? 0.52) * ph;
  const box = {position: 'absolute', left: 0, right: 0, top: cy, transform: `translateY(-50%) scale(${0.85 + 0.15 * p})`,
    opacity: Math.min(1, p * 1.4) * o, display: 'flex', justifyContent: 'center'};
  const t = frame / fps - (el.at ?? 0);
  if (el.kind === 'icon') {
    return <div style={box}>{(el.icons || []).map((it, i) => <Icon key={i} it={{...it, at: (el.at ?? 0) + (it.at ?? 0)}} frame={frame} fps={fps} s={s} />)}</div>;
  }
  if (el.kind === 'window') {
    const n = Math.max(0, Math.floor((t - 0.3) * (el.cps ?? 28)));
    const text = uz(el.text || '');
    return (
      <div style={box}>
        <div style={{width: W * 0.86, minHeight: (el.h ?? 0.42) * ph, background: '#FAF8F5', borderRadius: 26 * s,
          boxShadow: '0 20px 60px rgba(0,0,0,.5)', padding: `${22 * s}px ${30 * s}px`, boxSizing: 'border-box'}}>
          <div style={{display: 'flex', alignItems: 'center', gap: 10 * s, marginBottom: 18 * s}}>
            {['#FF5F57', '#FEBC2E', '#28C840'].map((c) => <div key={c} style={{width: 16 * s, height: 16 * s, borderRadius: 99, background: c}} />)}
            <div style={{flex: 1, textAlign: 'center', fontFamily: F, fontWeight: 600, fontSize: 24 * s, color: '#333'}}>{uz(el.title || '')}</div>
          </div>
          <div style={{fontFamily: F, fontWeight: 500, fontSize: (el.size ?? 30) * s, lineHeight: 1.35, color: '#1d1d1d', whiteSpace: 'pre-wrap'}}>
            {text.slice(0, n)}<span style={{opacity: n < text.length && Math.floor(t * 2) % 2 ? 1 : 0}}>|</span>
          </div>
        </div>
      </div>
    );
  }
  if (el.kind === 'tree') {
    const kids = el.children || [];
    const times = el.times || kids.map((_, i) => 0.6 + i * 0.6);
    return (
      <div style={{...box, flexDirection: 'column', alignItems: 'center'}}>
        <Folder w={130 * s} />
        <div style={{fontFamily: F, fontWeight: 600, fontSize: 26 * s, color: '#EEE', margin: `${8 * s}px 0 ${20 * s}px`}}>{uz(el.root)}</div>
        <div style={{display: 'flex', gap: 60 * s, borderTop: kids.length ? `2px solid rgba(255,255,255,.35)` : 'none', paddingTop: 22 * s}}>
          {kids.map((k, i) => {
            const q = spring({frame: frame - ((el.at ?? 0) + times[i]) * fps, fps, config: {damping: 13}});
            return (
              <div key={i} style={{display: 'flex', flexDirection: 'column', alignItems: 'center', opacity: frame < ((el.at ?? 0) + times[i]) * fps ? 0 : q,
                transform: `translateY(${(1 - q) * 30}px)`}}>
                <Folder w={96 * s} />
                <div style={{fontFamily: F, fontWeight: 600, fontSize: 24 * s, color: '#DDD', marginTop: 8 * s}}>{uz(k)}</div>
              </div>
            );
          })}
        </div>
      </div>
    );
  }
  if (el.kind === 'chips') {
    return (
      <div style={{...box, flexDirection: 'column', alignItems: 'center', gap: 26 * s}}>
        {(el.items || []).map((it, i) => {
          const a = (el.at ?? 0) + (it.at ?? i * 0.8);
          const q = spring({frame: frame - a * fps, fps, config: {damping: 14}});
          if (frame < a * fps) return null;
          const ask = (it.kind ?? (i % 2 ? 'reply' : 'ask')) === 'ask';
          return (
            <div key={i} style={{alignSelf: ask ? 'center' : 'flex-start', marginLeft: ask ? 0 : W * 0.08, transform: `scale(${0.7 + 0.3 * q})`, opacity: q,
              background: ask ? accent : '#FFFFFF', color: '#151515', fontFamily: F, fontWeight: ask ? 700 : 500,
              fontSize: 28 * s, padding: `${14 * s}px ${26 * s}px`, borderRadius: ask ? 14 * s : 18 * s, maxWidth: W * 0.8,
              boxShadow: '0 10px 30px rgba(0,0,0,.4)'}}>{uz(it.text)}</div>
          );
        })}
      </div>
    );
  }
  if (el.kind === 'list') {
    return (
      <div style={{...box, flexDirection: 'column', alignItems: 'flex-start', paddingLeft: W * 0.2}}>
        {(el.items || []).map((it, i) => {
          const a = (el.at ?? 0) + (it.at ?? i * 0.6);
          const q = spring({frame: frame - a * fps, fps, config: {damping: 14}});
          if (frame < a * fps) return null;
          return <div key={i} style={{fontFamily: F, fontWeight: 600, fontSize: 36 * s, color: '#F2F2F2', margin: `${10 * s}px 0`,
            opacity: q, transform: `translateX(${(1 - q) * -40}px)`}}><span style={{color: accent, marginRight: 16 * s}}>{it.icon || '•'}</span>{uz(it.text)}</div>;
        })}
      </div>
    );
  }
  if (el.kind === 'card') {
    return (
      <div style={box}>
        <div style={{width: W * 0.86, background: '#FAF8F5', borderRadius: 24 * s, padding: `${26 * s}px ${32 * s}px`, boxSizing: 'border-box',
          boxShadow: '0 20px 60px rgba(0,0,0,.5)', fontFamily: F, color: '#1b1b1b'}}>
          <div style={{fontWeight: 800, fontSize: 32 * s, marginBottom: 16 * s}}>{uz(el.title || '')}</div>
          {el.colors ? <div style={{display: 'flex', gap: 12 * s, marginBottom: 14 * s}}>{el.colors.map((c) =>
            <div key={c} style={{width: 34 * s, height: 34 * s, borderRadius: 99, background: c, boxShadow: 'inset 0 0 0 1px rgba(0,0,0,.15)'}} />)}</div> : null}
          {(el.rows || []).map(([k, v], i) => (
            <div key={i} style={{display: 'flex', fontSize: 25 * s, padding: `${7 * s}px 0`, borderTop: '1px solid #e6e1da'}}>
              <div style={{width: '32%', color: '#888', fontWeight: 600}}>{uz(k)}</div><div style={{fontWeight: 600}}>{uz(v)}</div>
            </div>
          ))}
        </div>
      </div>
    );
  }
  return null;
};

export const GuidePanel = ({step = 1, title = '', panel = 0.5, accent = '#F5A623', elements = [], enter = true, exit = true,
  label = 'Qadam'}) => {
  const frame = useCurrentFrame();
  const {fps, width, height, durationInFrames} = useVideoConfig();
  const s = width / 1080;
  const ph = height * panel;
  const total = durationInFrames / fps;
  const inP = enter ? spring({frame, fps, config: {damping: 20, mass: 0.8}}) : 1;
  const outP = exit ? interpolate(frame, [durationInFrames - 0.3 * fps, durationInFrames], [0, 1], clamp) : 0;
  return (
    <AbsoluteFill>
      <div style={{position: 'absolute', left: 0, top: (inP - 1 - outP) * ph, width, height: ph, overflow: 'hidden',
        background: 'radial-gradient(ellipse at 50% 55%, #26211d 0%, #141210 55%, #0d0c0b 100%)'}}>
        <div style={{position: 'absolute', top: 0.075 * ph, left: 0, right: 0, textAlign: 'center', fontFamily: F,
          fontWeight: 700, fontSize: 40 * s, color: '#F4F4F4'}}>
          <span style={{color: accent}}>{uz(label)} {step}.</span> {uz(title)}
        </div>
        {elements.map((el, i) => <Element key={i} el={el} frame={frame} fps={fps} s={s} W={width} ph={ph} accent={accent} total={total} />)}
      </div>
    </AbsoluteFill>
  );
};
