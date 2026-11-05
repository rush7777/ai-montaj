// Remotion kompozitsiyalari ro'yxati. Yangi kompozitsiya: shu papkaga Komponent.jsx qo'shing va shu yerda ro'yxatga oling.
// Uzunlik, fps va o'lcham har doim edit.json dan props orqali keladi (montaj/remotion_layer.py).
import {Composition} from 'remotion';
import {StepCard} from './StepCard';
import {TitleCard} from './TitleCard';

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
  </>
);
