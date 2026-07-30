import { FileText, Lock } from "lucide-react";

import type { MaterialItem } from "./api";

/**
 * View-only viewer for notes & materials (req 2). Notes are meant to be *read in the app*,
 * not downloaded: we embed them with the download chrome suppressed, block the
 * right-click "Save as" menu, and lay a per-student watermark over the top. This is a
 * strong deterrent against casual redistribution — the same honest framing as the video
 * watermark, not a cryptographic guarantee (a determined user can still screenshot).
 */
export function MaterialViewer({
  material,
  watermark,
}: {
  material: MaterialItem;
  watermark: string;
}) {
  const type = material.content_type || "";
  const isImage = type.startsWith("image/");
  const isPdf = type === "application/pdf";

  return (
    <div className="grid gap-2">
      <div
        className="relative overflow-hidden rounded-lg border border-brdr bg-black/90"
        onContextMenu={(e) => e.preventDefault()}
      >
        {isImage ? (
          <img
            src={material.view_url}
            alt={material.title}
            className="mx-auto block max-h-[68vh] w-full select-none object-contain"
            draggable={false}
          />
        ) : isPdf ? (
          // #toolbar=0 hides the built-in PDF download/print bar in most browsers.
          <iframe
            title={material.title}
            src={`${material.view_url}#toolbar=0&navpanes=0&scrollbar=1`}
            className="block h-[68vh] w-full bg-white"
          />
        ) : (
          <div className="flex flex-col items-center gap-2 px-6 py-16 text-center text-white/80">
            <FileText size={30} aria-hidden />
            <p className="text-sm">This file type can&apos;t be previewed in the browser.</p>
            <p className="text-xs text-white/50">
              Ask your faculty to re-upload it as a PDF or image to keep it view-only.
            </p>
          </div>
        )}
        <div className="pointer-events-none absolute inset-0">
          <span className="ap-watermark">{watermark}</span>
          <span className="absolute right-2 top-2 text-xs text-white/30">{watermark}</span>
        </div>
      </div>
      <p className="flex items-center gap-1.5 text-xs text-muted">
        <Lock size={12} aria-hidden />
        View-only — this material opens in the app and isn&apos;t downloadable.
      </p>
    </div>
  );
}
