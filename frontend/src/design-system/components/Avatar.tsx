import { cn } from "../utils/cn";

function initialsOf(name: string): string {
  return (
    name
      .trim()
      .split(/\s+/)
      .map((p) => p[0])
      .filter(Boolean)
      .slice(0, 2)
      .join("")
      .toUpperCase() || "?"
  );
}

type Tone = "navy" | "brand";

export function Avatar({
  name,
  size = 36,
  tone = "navy",
  className,
}: {
  name: string;
  size?: number;
  tone?: Tone;
  className?: string;
}) {
  return (
    <span
      className={cn(
        "inline-flex shrink-0 items-center justify-center rounded-full font-semibold text-white",
        tone === "navy" ? "bg-navy" : "bg-brand-strong",
        className,
      )}
      style={{ width: size, height: size, fontSize: Math.round(size * 0.36) }}
      aria-hidden
    >
      {initialsOf(name)}
    </span>
  );
}
