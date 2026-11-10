// Remotion kompozitsiyalari ro'yxati. Yangi kompozitsiya: shu papkaga Komponent.jsx qo'shing va shu yerda ro'yxatga oling.
// Uzunlik, fps va o'lcham har doim edit.json dan props orqali keladi (montaj/remotion_layer.py).
import {Composition} from 'remotion';
import {StepCard} from './StepCard';
import {TitleCard} from './TitleCard';
import {StorySubs} from './StorySubs';
import {Broll} from './Broll';
import {WallCard} from './WallCard';
import {LabelBox} from './LabelBox';
import {BigWord} from './BigWord';
import {GuidePanel} from './GuidePanel';
import {PillTag} from './PillTag';

const meta = ({props}) => {
  const fps = props.fps ?? 30;
  return {
    fps,
    durationInFrames: Math.max(1, Math.round((props.duration ?? 3) * fps)),
    width: props.width ?? 1080,
    height: props.height ?? 1920,
  };
};

const base = {durationInFrames: 90, fps: 30, width: 1080, height: 1920, calculateMetadata: meta};

export const Root = () => (
  <>
    <Composition id="StepCard" component={StepCard} {...base}
      defaultProps={{step: 1, title: 'Tayyorgarlik', icon: '📁', caption: "Kompyuterda papka oching", duration: 3}} />
    <Composition id="TitleCard" component={TitleCard} {...base}
      defaultProps={{text: "O'z *AI montajchingiz*\n4 qadamda", duration: 3}} />
    {/* "Hikoya" (Azizon) uslubi */}
    <Composition id="StorySubs" component={StorySubs} {...base} defaultProps={{chunks: [], duration: 3}} />
    <Composition id="Broll" component={Broll} {...base} defaultProps={{src: null, duration: 3}} />
    <Composition id="WallCard" component={WallCard} {...base}
      defaultProps={{lines: [], duration: 3}} />
    <Composition id="LabelBox" component={LabelBox} {...base}
      defaultProps={{text: '', duration: 3}} />
    <Composition id="BigWord" component={BigWord} {...base} defaultProps={{text: '', duration: 3}} />
    {/* Qadamma-qadam gaid uslubi */}
    <Composition id="GuidePanel" component={GuidePanel} {...base} defaultProps={{step: 1, title: '', elements: [], duration: 3}} />
    <Composition id="PillTag" component={PillTag} {...base} defaultProps={{text: '', duration: 3}} />
  </>
);
