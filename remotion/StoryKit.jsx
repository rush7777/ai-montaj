// "Hikoya" (Azizon) uslubi uchun umumiy bo'laklar: devor foni, so'zlarning yumshoq chiqishi, qo'lda chizilgan belgilar.
import {interpolate, random, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';

export const STORY = {
  wall: '#DCD3C6',          // iliq krem devor
  ink: '#241D18',           // devordagi to'q matn
  brand: '#7A2E22',         // to'q qizil-jigarrang sarlavha
  muted: '#6E645B',         // kichik sans matn
  gold: '#E2B93B',          // tagiga chizish, yorliq qutisi
  red: '#C8352B',           // X belgisi
  serif: 'Instrument Serif',
  sans: 'Montserrat',
};

export const clamp = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'};

// O'zbekcha oʻ/gʻ belgilari (U+02BB, U+02BC) Instrument Serif va Bebas Neue'da yo'q - shriftda bor ‘ ’ ga almashtiramiz
export const uz = (t) => String(t ?? '').replace(/ʻ/g, '‘').replace(/ʼ/g, '’');
const ease = (p) => 1 - Math.pow(1 - p, 3);

// Loyiha fayllari remotion_layer.py tomonidan public/media ga ko'chiriladi; "media/..." yoki to'liq URL
export const src = (s) => (!s ? null : /^(https?:|data:)/.test(s) ? s : staticFile(s));
export const isVideo = (s) => /\.(mp4|mov|webm|mkv)$/i.test(s || '');

// So'z paydo bo'lishi: shaffoflik + xiralik + biroz pastdan. t0 - soniya, dur - soniya
export const reveal = (frame, fps, t0, dur = 0.22, rise = 10) => {
  const p = ease(interpolate(frame, [t0 * fps, (t0 + dur) * fps], [0, 1], clamp));
  return {opacity: p, filter: `blur(${(1 - p) * 7}px)`, transform: `translateY(${(1 - p) * rise}px)`};
};

// Krem devor: deraza soyasi diagonal tushadi, chetlari qoraygan (vignette), yengil plyonka donasi
export const WallBg = ({tone = STORY.wall, push = 0.03}) => {
  const frame = useCurrentFrame();
  const {width, height, durationInFrames} = useVideoConfig();
  const z = 1 + push * (frame / Math.max(1, durationInFrames));
  const panes = [];
  for (let r = 0; r < 3; r++) {
    for (let c = 0; c < 2; c++) {
      panes.push(<rect key={`${r}${c}`} x={c * 290} y={r * 400} width={262} height={370} rx={4} />);
    }
  }
  return (
    <div style={{position: 'absolute', inset: 0, overflow: 'hidden', background: tone}}>
      <div style={{position: 'absolute', inset: 0, transform: `scale(${z})`}}>
        <div style={{position: 'absolute', inset: 0,
          background: `radial-gradient(ellipse at 38% 30%, rgba(255,252,244,.95) 0%, rgba(255,250,240,0) 62%)`}} />
        <svg viewBox="0 0 1080 1920" style={{position: 'absolute', inset: 0, width: '100%', height: '100%'}}>
          <defs>
            <filter id="soft"><feGaussianBlur stdDeviation="16" /></filter>
            <mask id="win">
              <rect width="1080" height="1920" fill="black" />
              <g transform="translate(10 -80) skewY(16) skewX(-12)" fill="white">{panes}</g>
            </mask>
          </defs>
          {/* deraza yorug'ligi: oynalar yorug', ramka - soya */}
          <rect width="1080" height="1920" fill="rgba(255,250,238,.80)" mask="url(#win)" filter="url(#soft)" />
          <g transform="translate(-40 -60) skewY(18) skewX(-14)" fill="none" stroke="rgba(70,55,40,.10)"
            strokeWidth="34" filter="url(#soft)">
            <rect x={-20} y={-20} width={480} height={1030} />
          </g>
        </svg>
      </div>
      <div style={{position: 'absolute', inset: 0,
        background: 'radial-gradient(ellipse at 50% 48%, rgba(0,0,0,0) 45%, rgba(40,28,18,.42) 100%)'}} />
      <svg style={{position: 'absolute', inset: 0, width: '100%', height: '100%', opacity: 0.09, mixBlendMode: 'multiply'}}>
        <filter id="grain"><feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="2" seed={frame % 7} />
          <feColorMatrix type="saturate" values="0" /></filter>
        <rect width={width} height={height} filter="url(#grain)" />
      </svg>
    </div>
  );
};

// Qo'lda chizilgandek notekis chiziqlar (piksel, 1080x1920 tizimida)
export const roughPaths = (shape, cx, cy, w, h, seed = 1) => {
  const j = (k, a) => (random(`${seed}-${k}`) - 0.5) * 2 * a;
  const rx = w / 2, ry = h / 2;
  if (shape === 'circle') {
    const pts = [];
    const a0 = random(`${seed}a`) * Math.PI * 2;
    for (let k = 0; k <= 72; k++) {
      const p = k / 72, a = a0 - Math.PI * 2 * 1.1 * p, r = 1 + 0.035 * Math.sin(3 * a + seed) + 0.07 * p;
      pts.push([cx + rx * r * Math.cos(a), cy + ry * r * Math.sin(a)]);
    }
    return ['M' + pts.map(([x, y]) => `${x.toFixed(1)} ${y.toFixed(1)}`).join(' L')];
  }
  if (shape === 'cross') {
    return [`M${cx - rx + j(1, 8)} ${cy - ry + j(2, 8)} Q${cx + j(3, 20)} ${cy + j(4, 20)} ${cx + rx + j(5, 8)} ${cy + ry + j(6, 8)}`,
      `M${cx + rx + j(7, 8)} ${cy - ry + j(8, 8)} Q${cx + j(9, 20)} ${cy + j(10, 20)} ${cx - rx + j(11, 8)} ${cy + ry + j(12, 8)}`];
  }
  if (shape === 'underline') {
    return [`M${cx - rx} ${cy + j(1, 3)} Q${cx} ${cy + h * 0.6 + j(2, 3)} ${cx + rx} ${cy - h * 0.2 + j(3, 3)}`];
  }
  if (shape === 'check') {
    return [`M${cx - rx} ${cy} L${cx - rx * 0.25} ${cy + ry} L${cx + rx} ${cy - ry}`];
  }
  return [`M${cx - rx} ${cy - ry} L${cx + rx} ${cy - ry} L${cx + rx} ${cy + ry} L${cx - rx} ${cy + ry} Z`];
};

// Chiziq chizilishi: at - boshlanish (s), draw - chizish davomiyligi (s)
export const HandMark = ({shape = 'circle', x = 0.5, y = 0.5, w = 0.5, h = 0.2, at = 0, draw = 0.5,
  color = '#FFFFFF', stroke = 9, seed = 3}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const ds = roughPaths(shape, x * 1080, y * 1920, w * 1080, h * 1920, seed);
  return (
    <svg viewBox="0 0 1080 1920" style={{position: 'absolute', inset: 0, width: '100%', height: '100%'}}>
      {ds.map((d, i) => {
        const t0 = at + (draw / ds.length) * i;
        const p = ease(interpolate(frame, [t0 * fps, (t0 + draw / ds.length) * fps], [0, 1], clamp));
        return <path key={i} d={d} pathLength={1} fill="none" stroke={color} strokeWidth={stroke}
          strokeLinecap="round" strokeLinejoin="round" strokeDasharray={1} strokeDashoffset={1 - p}
          style={{opacity: p > 0 ? 1 : 0}} />;
      })}
    </svg>
  );
};

// Tilla ramka (devordagi kartina)
export const GoldFrame = ({children, w, h, border = 34}) => (
  <div style={{position: 'relative', width: w, height: h, padding: border, boxSizing: 'border-box',
    background: 'linear-gradient(135deg,#7a5414 0%,#e9c46a 22%,#a5741f 45%,#f3d98b 62%,#8a5d17 82%,#d9ab4a 100%)',
    boxShadow: '0 28px 60px rgba(40,25,10,.45), inset 0 0 0 3px rgba(255,235,170,.5), inset 0 0 18px rgba(60,35,5,.7)'}}>
    <div style={{position: 'absolute', inset: border * 0.38, border: '3px solid rgba(90,60,15,.6)',
      boxShadow: 'inset 0 0 0 2px rgba(255,230,160,.45)'}} />
    <div style={{position: 'relative', width: '100%', height: '100%', overflow: 'hidden',
      boxShadow: 'inset 0 0 22px rgba(0,0,0,.7)'}}>{children}</div>
  </div>
);
