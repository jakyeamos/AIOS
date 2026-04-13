import { formatNumber } from "@/lib/format";

type StatCardProps = {
  label: string;
  value: string | number;
  delta?: number;
  trend?: "up" | "down" | "flat";
  status?: "healthy" | "warning" | "error";
};

const renderDelta = (delta: number, trend: "up" | "down" | "flat" | undefined): string => {
  const sign = delta > 0 ? "+" : "";
  const arrow = trend === "up" ? "▲" : trend === "down" ? "▼" : "■";

  return `${arrow} ${sign}${delta.toFixed(1)}%`;
};

export function StatCard({ label, value, delta, trend, status }: StatCardProps): React.JSX.Element {
  const renderedValue = typeof value === "number" ? formatNumber(value) : value;

  return (
    <article className="stat-card">
      <p className="stat-label">{label}</p>
      <p className="stat-value">{renderedValue}</p>
      {delta !== undefined ? (
        <p className={`stat-delta ${status ? `text-${status}` : ""}`}>{renderDelta(delta, trend)}</p>
      ) : null}
    </article>
  );
}
