// Loyihadagi shriftlar (assets/fonts -> public/fonts) kadr chizilishidan oldin yuklanadi.
import {continueRender, delayRender, staticFile} from 'remotion';

const FACES = [
  ['Montserrat', 'Montserrat-Black.ttf', '900'],
  ['Montserrat', 'Montserrat-ExtraBold.ttf', '800'],
  ['Montserrat', 'Montserrat-SemiBold.ttf', '600'],
  ['Bebas Neue', 'BebasNeue-Regular.ttf', '400'],
  ['Instrument Serif', 'InstrumentSerif-Regular.ttf', '400', 'normal'],
  ['Instrument Serif', 'InstrumentSerif-Italic.ttf', '400', 'italic'],
];

if (typeof document !== 'undefined' && !window.__montajFonts) {
  window.__montajFonts = true;
  const handle = delayRender('shriftlar');
  Promise.all(FACES.map(([family, file, weight, style = 'normal']) =>
    new FontFace(family, `url(${staticFile('fonts/' + file)})`, {weight, style}).load()
      .then((f) => document.fonts.add(f))))
    .catch(() => {})
    .then(() => continueRender(handle));
}

// "*so'z*" -> aksent rangidagi bo'lak; qaytaradi: [{text, accent}]
export const parseRich = (s) => String(s).split(/(\*[^*]+\*)/).filter(Boolean)
  .map((p) => (p.startsWith('*') && p.endsWith('*') ? {text: p.slice(1, -1), accent: true} : {text: p, accent: false}));

export const THEME = {accent: '#FFD400', text: '#FFFFFF', dark: '#111111', panel: '#141414'};
