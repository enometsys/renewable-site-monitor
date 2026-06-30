import {
  CartesianGrid,
  Line,
  ComposedChart,
  ResponsiveContainer,
  Scatter,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"

import type { Point } from "@/lib/api"

interface Props {
  series: Point[]
  unit: string
  label: string
}

function fmtTime(ts: string) {
  const d = new Date(ts)
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric" })
}

export function TimeSeriesChart({ series, unit, label }: Props) {
  // Recharts needs anomalies as their own keyed field to render as points.
  const data = series.map((p) => ({
    ts: p.timestamp,
    value: p.value,
    anomaly: p.isAnomaly ? p.value : null,
  }))

  return (
    <ResponsiveContainer width="100%" height={380}>
      <ComposedChart data={data} margin={{ top: 8, right: 16, bottom: 8, left: 8 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
        <XAxis
          dataKey="ts"
          tickFormatter={fmtTime}
          minTickGap={48}
          stroke="var(--muted-foreground)"
          fontSize={12}
        />
        <YAxis
          stroke="var(--muted-foreground)"
          fontSize={12}
          width={48}
          label={{ value: unit, angle: -90, position: "insideLeft", fontSize: 11 }}
        />
        <Tooltip
          labelFormatter={(ts) => new Date(ts as string).toLocaleString()}
          formatter={(v) => [
            typeof v === "number" ? v.toFixed(1) : "—",
            label,
          ]}
          contentStyle={{
            background: "var(--popover)",
            border: "1px solid var(--border)",
            borderRadius: 8,
            fontSize: 12,
          }}
        />
        <Line
          type="monotone"
          dataKey="value"
          stroke="#2563eb"
          strokeWidth={1.5}
          dot={false}
          isAnimationActive={false}
          connectNulls
        />
        <Scatter dataKey="anomaly" fill="#dc2626" isAnimationActive={false} />
      </ComposedChart>
    </ResponsiveContainer>
  )
}
