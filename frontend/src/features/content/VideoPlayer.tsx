import { useRef } from "react";

import { contentApi, type VideoItem } from "./api";

/**
 * In-app secure player: per-student moving watermark, no-download controls,
 * resume from last position, and ≥80%-watched progress tracking.
 */
export function VideoPlayer({ video, watermark }: { video: VideoItem; watermark: string }) {
  const ref = useRef<HTMLVideoElement>(null);
  const lastSent = useRef(0);

  const send = (percent: number, position: number) => {
    contentApi
      .postProgress(video.id, {
        percent,
        watched_seconds: Math.round(position),
        last_position: Math.round(position),
      })
      .catch(() => undefined);
  };

  const onLoaded = () => {
    const v = ref.current;
    if (v && video.progress?.last_position) {
      v.currentTime = video.progress.last_position;
    }
  };

  const onTimeUpdate = () => {
    const v = ref.current;
    if (!v || !v.duration) return;
    const now = Date.now();
    if (now - lastSent.current < 8000) return;
    lastSent.current = now;
    send(Math.round((v.currentTime / v.duration) * 100), v.currentTime);
  };

  const onEnded = () => {
    const v = ref.current;
    if (v) send(100, v.duration || v.currentTime);
  };

  return (
    <div className="relative overflow-hidden rounded-lg bg-black">
      {/* Faculty-uploaded lessons carry no caption files today; a captions pipeline is a
          content-team item, not something the player can synthesise. */}
      {/* eslint-disable-next-line jsx-a11y/media-has-caption */}
      <video
        ref={ref}
        src={video.play_url}
        controls
        controlsList="nodownload noremoteplayback"
        disablePictureInPicture
        onContextMenu={(e) => e.preventDefault()}
        onLoadedMetadata={onLoaded}
        onTimeUpdate={onTimeUpdate}
        onEnded={onEnded}
        className="block max-h-[60vh] w-full"
      />
      <div className="pointer-events-none absolute inset-0">
        <span className="ap-watermark">{watermark}</span>
        <span className="absolute right-2 top-2 text-xs text-white/30">{watermark}</span>
      </div>
    </div>
  );
}
