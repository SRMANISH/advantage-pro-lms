import { cn } from "../utils/cn";

type Tone = "brand" | "success" | "danger" | "warning";

const tones: Record<Tone, string> = {
  brand: "bg-brand-strong",
  success: "bg-success",
  danger: "bg-danger",
  warning: "bg-warning",
};

export function Progress({
  value,
  tone = "brand",
  className,
}: {
  value: number;
  tone?: Tone;
  className?: string;
}) {
  const pct = Math.max(0, Math.min(100, value));
  return (
    <div className={cn("h-2 w-full overflow-hidden rounded-full bg-sky", className)}>
      <div
        className={cn("h-full rounded-full transition-[width] duration-700 ease-out", tones[tone])}
        style={{ width: `${pct}%` }}
      />
    </div>
  );
}
