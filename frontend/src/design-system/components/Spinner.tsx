import { cn } from "../utils/cn";

export function Spinner({ size = 18, className }: { size?: number; className?: string }) {
  return (
    <span
      role="status"
      aria-label="Loading"
      className={cn(
        "inline-block animate-spin rounded-full border-2 border-brand/30 border-t-brand",
        className,
      )}
      style={{ width: size, height: size }}
    />
  );
}
