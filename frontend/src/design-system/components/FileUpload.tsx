import { UploadCloud } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { cn } from "../utils/cn";

interface FileUploadProps {
  file: File | null;
  onFile: (file: File | null) => void;
  accept?: string;
  hint?: string;
  className?: string;
}

/** Drag-and-drop upload zone with a selected-file chip. Controlled by `file`. */
export function FileUpload({ file, onFile, accept, hint, className }: FileUploadProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [drag, setDrag] = useState(false);

  // Keep the hidden input in sync so re-selecting the same file after a reset still fires.
  useEffect(() => {
    if (!file && inputRef.current) inputRef.current.value = "";
  }, [file]);

  return (
    <div className={className}>
      <div
        role="button"
        tabIndex={0}
        onClick={() => inputRef.current?.click()}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            inputRef.current?.click();
          }
        }}
        onDragOver={(e) => {
          e.preventDefault();
          setDrag(true);
        }}
        onDragLeave={() => setDrag(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDrag(false);
          const f = e.dataTransfer.files?.[0];
          if (f) onFile(f);
        }}
        className={cn(
          "flex cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-dashed px-6 py-8 text-center transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-brand/40",
          drag
            ? "border-brand bg-brand/5"
            : "border-brdr bg-surfaceSoft hover:border-brand/50 hover:bg-sky/40",
        )}
      >
        <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-white text-brand-strong shadow-sm">
          <UploadCloud size={20} />
        </span>
        <p className="mt-3 text-sm font-medium text-ink">
          Drag a file here, or <span className="text-brand-strong">browse</span>
        </p>
        {hint && <p className="mt-1 text-xs text-muted">{hint}</p>}
      </div>

      <input
        ref={inputRef}
        type="file"
        accept={accept}
        className="hidden"
        onChange={(e) => onFile(e.target.files?.[0] ?? null)}
      />

      {file && (
        <div className="mt-3 flex items-center justify-between rounded-xl border border-brdr bg-surface px-4 py-2.5">
          <div className="min-w-0">
            <div className="truncate text-sm font-medium text-ink">{file.name}</div>
            <div className="text-xs text-muted">{(file.size / 1024).toFixed(0)} KB</div>
          </div>
          <button
            onClick={() => onFile(null)}
            className="rounded-lg px-2 py-1 text-xs font-medium text-danger hover:bg-danger/10"
          >
            Remove
          </button>
        </div>
      )}
    </div>
  );
}
