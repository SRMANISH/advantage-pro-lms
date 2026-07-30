import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

// Default export so consumers can `lazy(() => import(".../charts/Chart"))` and keep
// Recharts out of the main bundle (loaded only on dashboards / performance).

export const CHART_PALETTE = ["#00A0E0", "#163A8C", "#6E2EA0", "#1E8E5A", "#B46E14"];

interface Series {
  key: string;
  label?: string;
  color?: string;
}

export interface ChartProps {
  kind: "line" | "area" | "bar" | "donut";
  data: Array<Record<string, string | number>>;
  xKey?: string;
  series?: Series[];
  nameKey?: string;
  valueKey?: string;
  height?: number;
  colors?: string[];
}

const tooltipStyle = {
  borderRadius: 12,
  border: "1px solid rgb(214 235 248)",
  boxShadow: "0 10px 28px rgb(15 31 58 / 0.10)",
  fontSize: 12,
};
const axisProps = { stroke: "#9aa7bd", fontSize: 12, tickLine: false, axisLine: false } as const;

export default function Chart({
  kind,
  data,
  xKey = "label",
  series = [],
  nameKey = "name",
  valueKey = "value",
  height = 260,
  colors = CHART_PALETTE,
}: ChartProps) {
  if (kind === "donut") {
    return (
      <ResponsiveContainer width="100%" height={height}>
        <PieChart>
          <Pie
            data={data}
            dataKey={valueKey}
            nameKey={nameKey}
            innerRadius="58%"
            outerRadius="82%"
            paddingAngle={2}
            stroke="none"
          >
            {data.map((_, i) => (
              <Cell key={i} fill={colors[i % colors.length]} />
            ))}
          </Pie>
          <Tooltip contentStyle={tooltipStyle} />
          <Legend iconType="circle" wrapperStyle={{ fontSize: 12 }} />
        </PieChart>
      </ResponsiveContainer>
    );
  }

  if (kind === "bar") {
    return (
      <ResponsiveContainer width="100%" height={height}>
        <BarChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: -16 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgb(214 235 248)" vertical={false} />
          <XAxis dataKey={xKey} {...axisProps} />
          <YAxis {...axisProps} />
          <Tooltip contentStyle={tooltipStyle} cursor={{ fill: "rgb(230 246 253 / 0.6)" }} />
          {series.map((s, i) => (
            <Bar
              key={s.key}
              dataKey={s.key}
              name={s.label ?? s.key}
              fill={s.color ?? colors[i % colors.length]}
              radius={[6, 6, 0, 0]}
              maxBarSize={42}
            />
          ))}
        </BarChart>
      </ResponsiveContainer>
    );
  }

  const ChartEl = kind === "area" ? AreaChart : LineChart;
  return (
    <ResponsiveContainer width="100%" height={height}>
      <ChartEl data={data} margin={{ top: 8, right: 8, bottom: 0, left: -16 }}>
        <defs>
          {series.map((s, i) => (
            <linearGradient key={s.key} id={`grad-${s.key}`} x1="0" y1="0" x2="0" y2="1">
              <stop
                offset="0%"
                stopColor={s.color ?? colors[i % colors.length]}
                stopOpacity={0.28}
              />
              <stop
                offset="100%"
                stopColor={s.color ?? colors[i % colors.length]}
                stopOpacity={0}
              />
            </linearGradient>
          ))}
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="rgb(214 235 248)" vertical={false} />
        <XAxis dataKey={xKey} {...axisProps} />
        <YAxis {...axisProps} />
        <Tooltip contentStyle={tooltipStyle} />
        {series.map((s, i) => {
          const color = s.color ?? colors[i % colors.length];
          return kind === "area" ? (
            <Area
              key={s.key}
              type="monotone"
              dataKey={s.key}
              name={s.label ?? s.key}
              stroke={color}
              strokeWidth={2.5}
              fill={`url(#grad-${s.key})`}
              dot={false}
            />
          ) : (
            <Line
              key={s.key}
              type="monotone"
              dataKey={s.key}
              name={s.label ?? s.key}
              stroke={color}
              strokeWidth={2.5}
              dot={false}
              activeDot={{ r: 4 }}
            />
          );
        })}
      </ChartEl>
    </ResponsiveContainer>
  );
}
