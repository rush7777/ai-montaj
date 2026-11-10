// B-roll: rasm yoki video butun kadrni qoplaydi (gapirayotgan odam ovozi davom etadi).
// Ken Burns (sekin zoom/siljish), oq-qora (o'tmish) rejimi, kirish/chiqishda xiralik bilan erish.
// props: src ("media/..."), zoom [1.0, 1.08], x/y (zoom markazi 0-1), pan [dx, dy] (kadr ulushi), bw (bool),
//        fade_in / fade_out (s), blur (o'tishdagi xiralik, px), warm (0-1, iliq tus), fit ('cover'|'contain'),
//        video_start (video B-roll boshlanish nuqtasi, s), muted
import {AbsoluteFill, interpolate, Img, OffthreadVideo, useCurrentFrame, useVideoConfig} from 'remotion';
import {clamp, isVideo, src as media} from './StoryKit';

export const Broll = ({src, zoom = [1.0, 1.08], x = 0.5, y = 0.5, pan = [0, 0], bw = false, fade_in = 0.3,
  fade_out = 0.3, blur = 14, warm = 0, fit = 'cover', video_start = 0}) => {
  const frame = useCurrentFrame();
  const {fps, durationInFrames} = useVideoConfig();
  const p = frame / Math.max(1, durationInFrames - 1);
  const z = zoom[0] + (zoom[1] - zoom[0]) * p;
  const fin = fade_in > 0 ? interpolate(frame, [0, fade_in * fps], [0, 1], clamp) : 1;
  const fout = fade_out > 0 ? interpolate(frame, [durationInFrames - fade_out * fps, durationInFrames], [1, 0], clamp) : 1;
  const vis = Math.min(fin, fout);
  const filters = [];
  if (bw) filters.push('grayscale(1) contrast(1.12) brightness(0.95)');
  if (warm) filters.push(`sepia(${warm * 0.35}) saturate(${1 + warm * 0.15})`);
  if (vis < 1) filters.push(`blur(${(1 - vis) * blur}px)`);
  const style = {position: 'absolute', inset: 0, width: '100%', height: '100%', objectFit: fit,
    transformOrigin: `${x * 100}% ${y * 100}%`,
    transform: `translate(${pan[0] * p * 100}%, ${pan[1] * p * 100}%) scale(${z})`};
  return (
    <AbsoluteFill style={{opacity: vis, filter: filters.join(' ') || 'none', background: fit === 'contain' ? '#000' : 'transparent'}}>
      {isVideo(src)
        ? <OffthreadVideo src={media(src)} muted startFrom={Math.round(video_start * fps)} style={style} />
        : <Img src={media(src)} style={style} />}
    </AbsoluteFill>
  );
};
