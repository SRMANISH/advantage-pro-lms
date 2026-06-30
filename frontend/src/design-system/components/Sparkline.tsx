/** Dependency-free SVG sparkline — light enough to drop into every KPI card. */
export function Sparkline({
  data,
  width = 120,
  height = 36,
  tone = "brand",
  className,
}: {
  data: number[];
  width?: number;
  height?: number;
  tone?: "brand" | "success" | "danger";
  className?: string;
}) {
  if (data.length < 2) return null;
  const max = Math.max(...data);
  const min = Math.min(...data);
  const range = max - min || 1;
  const step = width / (data.length - 1);
  const points = data.map((v, i) => `${i * step},${height - ((v - min) / range) * height}`);
  const stroke =
    tone === "success"
      ? "rgb(var(--color-success))"
      : tone === "danger"
        ? "rgb(var(--color-danger))"
        : "rgb(var(--color-brand))";
  return (
    <svg
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      className={className}
      preserveAspectRatio="none"
      aria-hidden
    >
      <polyline
        points={points.join(" ")}
        fill="none"
        stroke={stroke}
        strokeWidth={2}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
