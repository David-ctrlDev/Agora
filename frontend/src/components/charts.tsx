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
  color = "#4f46e5",
}: {
  value: number;
  size?: number;
  thickness?: number;
  color?: string;
}) {
  const r = (size - thickness) / 2;
  const c = 2 * Math.PI * r;
  const pct = Math.max(0, Math.min(100, value));
  const len = (pct / 100) * c;
  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="shrink-0">
      <g transform={`rotate(-90 ${size / 2} ${size / 2})`}>
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="#f1f5f9" strokeWidth={thickness} />
        {len > 0 && (
          <circle
            cx={size / 2}
            cy={size / 2}
            r={r}
            fill="none"
            stroke={color}
            strokeWidth={thickness}
            strokeDasharray={`${len} ${c - len}`}
            strokeLinecap="round"
          />
        )}
      </g>
      <text
        x={size / 2}
        y={size / 2}
        textAnchor="middle"
        dominantBaseline="middle"
        style={{ fontSize: size * 0.26, fontWeight: 600, fill: "#0f172a" }}
      >
        {pct}%
      </text>
    </svg>
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
  const r = (size - thickness) / 2;
  const c = 2 * Math.PI * r;
  const total = segments.reduce((sum, s) => sum + s.value, 0);
  let offset = 0;
  return (
    <div className="flex items-center gap-5">
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="shrink-0">
        <g transform={`rotate(-90 ${size / 2} ${size / 2})`}>
          <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="#f1f5f9" strokeWidth={thickness} />
          {total > 0 &&
            segments.map((s, i) => {
              if (s.value <= 0) return null;
              const len = (s.value / total) * c;
              const node = (
                <circle
                  key={i}
                  cx={size / 2}
                  cy={size / 2}
                  r={r}
                  fill="none"
                  stroke={s.color}
                  strokeWidth={thickness}
                  strokeDasharray={`${len} ${c - len}`}
                  strokeDashoffset={-offset}
                />
              );
              offset += len;
              return node;
            })}
        </g>
        {(centerValue !== undefined || centerLabel) && (
          <>
            <text
              x={size / 2}
              y={centerLabel ? size / 2 - 4 : size / 2}
              textAnchor="middle"
              dominantBaseline="middle"
              style={{ fontSize: 22, fontWeight: 600, fill: "#0f172a" }}
            >
              {centerValue}
            </text>
            {centerLabel && (
              <text
                x={size / 2}
                y={size / 2 + 16}
                textAnchor="middle"
                style={{ fontSize: 11, fill: "#94a3b8" }}
              >
                {centerLabel}
              </text>
            )}
          </>
        )}
      </svg>
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

/** Barras horizontales simples. */
export function BarList({ items }: { items: Segment[] }) {
  const max = Math.max(1, ...items.map((i) => i.value));
  return (
    <div className="space-y-2">
      {items.map((it, i) => (
        <div key={i} className="flex items-center gap-3 text-sm">
          <span className="w-16 shrink-0 text-slate-500">{it.label}</span>
          <div className="h-2 flex-1 rounded-full bg-slate-100">
            <div
              className="h-2 rounded-full"
              style={{ width: `${(it.value / max) * 100}%`, background: it.color }}
            />
          </div>
          <span className="w-6 text-right tabular-nums text-slate-700">{it.value}</span>
        </div>
      ))}
    </div>
  );
}

/** Burndown: línea ideal (punteada) vs. restante real (sólida). */
export function BurndownChart({
  points,
  height = 170,
}: {
  points: { date: string; ideal: number; remaining: number | null }[];
  height?: number;
}) {
  const width = 480;
  const pad = { l: 26, r: 12, t: 12, b: 24 };
  const n = points.length;
  const maxY = Math.max(1, ...points.map((p) => Math.max(p.ideal, p.remaining ?? 0)));
  const xAt = (i: number) => pad.l + (n <= 1 ? 0 : (i / (n - 1)) * (width - pad.l - pad.r));
  const yAt = (v: number) => pad.t + (1 - v / maxY) * (height - pad.t - pad.b);
  const idealPts = points.map((p, i) => `${xAt(i)},${yAt(p.ideal)}`).join(" ");
  const realPts = points
    .map((p, i) => (p.remaining == null ? null : `${xAt(i)},${yAt(p.remaining)}`))
    .filter((v): v is string => v !== null)
    .join(" ");
  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="w-full">
      <line x1={pad.l} y1={pad.t} x2={pad.l} y2={height - pad.b} stroke="#e2e8f0" />
      <line x1={pad.l} y1={height - pad.b} x2={width - pad.r} y2={height - pad.b} stroke="#e2e8f0" />
      <text
        x={pad.l - 6}
        y={yAt(maxY)}
        textAnchor="end"
        dominantBaseline="middle"
        style={{ fontSize: 10, fill: "#94a3b8" }}
      >
        {maxY}
      </text>
      <text
        x={pad.l - 6}
        y={yAt(0)}
        textAnchor="end"
        dominantBaseline="middle"
        style={{ fontSize: 10, fill: "#94a3b8" }}
      >
        0
      </text>
      <polyline fill="none" stroke="#cbd5e1" strokeWidth={2} strokeDasharray="4 4" points={idealPts} />
      {realPts && <polyline fill="none" stroke="#4f46e5" strokeWidth={2.5} points={realPts} />}
    </svg>
  );
}
