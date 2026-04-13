"use client";

import { Line, LineChart, ResponsiveContainer } from "recharts";

type SparklinePoint = {
  value: number;
};

type SparklineProps = {
  data: SparklinePoint[];
  color?: string;
};

export function Sparkline({ data, color = "var(--chart-1)" }: SparklineProps): React.JSX.Element {
  return (
    <div className="sparkline">
      <ResponsiveContainer width="100%" height={36}>
        <LineChart data={data}>
          <Line dataKey="value" stroke={color} strokeWidth={2} dot={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
