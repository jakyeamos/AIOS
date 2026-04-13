"use client";

import { Bar, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis, BarChart as ReBarChart } from "recharts";

type BarChartDatum = {
  label: string;
  value: number;
};

type BarChartProps = {
  data: BarChartDatum[];
  color?: string;
};

export function BarChart({ data, color = "var(--chart-1)" }: BarChartProps): React.JSX.Element {
  return (
    <div className="chart-card">
      <ResponsiveContainer width="100%" height={260}>
        <ReBarChart data={data}>
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
          <Bar dataKey="value" fill={color} radius={2} />
        </ReBarChart>
      </ResponsiveContainer>
    </div>
  );
}
