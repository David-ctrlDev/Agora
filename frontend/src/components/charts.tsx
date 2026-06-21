import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  Pie,
  PieChart,
  PolarAngleAxis,
  RadialBar,
  RadialBarChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

interface Segment {
  label: string;
  value: number;
  color: string;
}

/** Anillo de progreso de un solo valor (0–100). */
export function ProgressRing({
  value,
  size = 120,
  thickness = 12,
  color = "#059669",
}: {
  value: number;
  size?: number;
  thickness?: number;
  color?: string;
}) {
  const pct = Math.max(0, Math.min(100, Math.round(value)));
  return (
    <div style={{ position: "relative", width: size, height: size }}>
      <RadialBarChart
        width={size}
        height={size}
        cx="50%"
        cy="50%"
        innerRadius={size / 2 - thickness}
        outerRadius={size / 2}
        barSize={thickness}
        data={[{ value: pct }]}
        startAngle={90}
        endAngle={-270}
      >
        <PolarAngleAxis type="number" domain={[0, 100]} tick={false} />
        <RadialBar background dataKey="value" cornerRadius={thickness / 2} fill={color} />
      </RadialBarChart>
      <div
        style={{
          position: "absolute",
          inset: 0,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontSize: size * 0.26,
          fontWeight: 600,
          color: "#0f172a",
        }}
      >
        {pct}%
      </div>
    </div>
  );
}

/** Donut multi-segmento con leyenda. */
export function Donut({
  segments,
  size = 132,
  thickness = 16,
  centerValue,
  centerLabel,
}: {
  segments: Segment[];
  size?: number;
  thickness?: number;
  centerValue?: string;
  centerLabel?: string;
}) {
  const data = segments.filter((s) => s.value > 0);
  const outer = size / 2;
  const inner = outer - thickness;
  const empty = data.length === 0;
  return (
    <div className="flex items-center gap-5">
      <div style={{ position: "relative", width: size, height: size }}>
        <PieChart width={size} height={size}>
          <Pie
            data={empty ? [{ label: "—", value: 1, color: "#f1f5f9" }] : data}
            dataKey="value"
            nameKey="label"
            cx="50%"
            cy="50%"
            innerRadius={inner}
            outerRadius={outer}
            paddingAngle={data.length > 1 ? 2 : 0}
            stroke="none"
            isAnimationActive={false}
          >
            {(empty ? [{ color: "#f1f5f9" }] : data).map((s, i) => (
              <Cell key={i} fill={s.color} />
            ))}
          </Pie>
          {!empty && <Tooltip />}
        </PieChart>
        {(centerValue !== undefined || centerLabel) && (
          <div
            style={{
              position: "absolute",
              inset: 0,
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <span style={{ fontSize: 22, fontWeight: 600, color: "#0f172a", lineHeight: 1 }}>
              {centerValue}
            </span>
            {centerLabel && <span style={{ fontSize: 11, color: "#94a3b8" }}>{centerLabel}</span>}
          </div>
        )}
      </div>
      <ul className="space-y-1.5">
        {segments.map((s, i) => (
          <li key={i} className="flex items-center gap-2 text-sm text-slate-600">
            <span className="h-2.5 w-2.5 rounded-full" style={{ background: s.color }} />
            <span className="flex-1">{s.label}</span>
            <span className="tabular-nums font-medium text-slate-800">{s.value}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

/** Barras horizontales. */
export function BarList({ items }: { items: Segment[] }) {
  const height = Math.max(44, items.length * 34);
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart layout="vertical" data={items} margin={{ top: 0, right: 12, left: 0, bottom: 0 }}>
        <XAxis type="number" hide domain={[0, "dataMax"]} />
        <YAxis
          type="category"
          dataKey="label"
          width={64}
          tickLine={false}
          axisLine={false}
          tick={{ fontSize: 12, fill: "#64748b" }}
        />
        <Tooltip cursor={{ fill: "#f8fafc" }} />
        <Bar dataKey="value" radius={[0, 4, 4, 0]} barSize={14}>
          {items.map((it, i) => (
            <Cell key={i} fill={it.color} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

/** Burndown: línea ideal (punteada) vs. restante real (sólida). */
export function BurndownChart({
  points,
  height = 180,
}: {
  points: { date: string; ideal: number; remaining: number | null }[];
  height?: number;
}) {
  const formatDay = (value: string) => {
    const parsed = new Date(value);
    return Number.isNaN(parsed.getTime()) ? value : String(parsed.getDate());
  };
  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={points} margin={{ top: 8, right: 12, left: -16, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
        <XAxis
          dataKey="date"
          tickFormatter={formatDay}
          tick={{ fontSize: 10, fill: "#94a3b8" }}
          tickLine={false}
          axisLine={{ stroke: "#e2e8f0" }}
        />
        <YAxis
          allowDecimals={false}
          tick={{ fontSize: 10, fill: "#94a3b8" }}
          tickLine={false}
          axisLine={false}
          width={28}
        />
        <Tooltip />
        <Line
          type="monotone"
          dataKey="ideal"
          name="Ideal"
          stroke="#cbd5e1"
          strokeDasharray="4 4"
          strokeWidth={2}
          dot={false}
          isAnimationActive={false}
        />
        <Line
          type="monotone"
          dataKey="remaining"
          name="Real"
          stroke="#059669"
          strokeWidth={2.5}
          dot={false}
          connectNulls
          isAnimationActive={false}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
