"use client";

import {
  Area,
  AreaChart as ReAreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

type AreaChartDatum = {
  label: string;
  value: number;
};

type AreaChartProps = {
  data: AreaChartDatum[];
  color?: string;
};

export function AreaChart({ data, color = "var(--chart-2)" }: AreaChartProps): React.JSX.Element {
  return (
    <div className="chart-card">
      <ResponsiveContainer width="100%" height={260}>
        <ReAreaChart data={data}>
          <CartesianGrid stroke="var(--border)" vertical={false} />
          <XAxis dataKey="label" stroke="var(--text-muted)" />
          <YAxis stroke="var(--text-muted)" />
          <Tooltip
            contentStyle={{
              background: "var(--surface-raised)",
              border: "1px solid var(--border)",
              borderRadius: 4,
            }}
          />
          <Area type="monotone" dataKey="value" stroke={color} fill={color} fillOpacity={0.2} strokeWidth={2} />
        </ReAreaChart>
      </ResponsiveContainer>
    </div>
  );
}
