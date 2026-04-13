import { formatTokens } from "@/lib/format";
import type { CostBreakdownPoint } from "@/lib/types";

type CostBreakdownProps = {
  title: string;
  rows: CostBreakdownPoint[];
};

export function CostBreakdown({ title, rows }: CostBreakdownProps): React.JSX.Element {
  return (
    <section className="panel-card">
      <h3 className="panel-title">{title}</h3>
      <div className="table-head">
        <span>Group</span>
        <span>Tokens</span>
      </div>
      {rows.map((row) => (
        <div key={row.key} className="table-row">
          <span>{row.label}</span>
          <span className="mono">{formatTokens(row.tokens)}</span>
        </div>
      ))}
    </section>
  );
}
