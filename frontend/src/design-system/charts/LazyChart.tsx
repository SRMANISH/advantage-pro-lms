import { lazy, Suspense } from "react";

import type { ChartProps } from "./Chart";

// Type-only import above is erased at build, so Recharts loads only when a chart renders.
const Chart = lazy(() => import("./Chart"));

export function LazyChart(props: ChartProps) {
  const height = props.height ?? 260;
  return (
    <Suspense
      fallback={<div style={{ height }} className="w-full animate-pulse rounded-xl bg-sky/60" />}
    >
      <Chart {...props} />
    </Suspense>
  );
}
