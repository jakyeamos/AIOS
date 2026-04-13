type HeatmapCalendarProps = {
  values: number[];
};

const levelClass = (value: number): string => {
  if (value > 8) {
    return "heat-4";
  }

  if (value > 5) {
    return "heat-3";
  }

  if (value > 2) {
    return "heat-2";
  }

  if (value > 0) {
    return "heat-1";
  }

  return "heat-0";
};

export function HeatmapCalendar({ values }: HeatmapCalendarProps): React.JSX.Element {
  return (
    <div className="heatmap-grid">
      {values.map((value, index) => (
        <div key={`${index}-${value}`} className={`heat-cell ${levelClass(value)}`} title={`${value} events`} />
      ))}
    </div>
  );
}
