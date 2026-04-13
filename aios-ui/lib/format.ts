export const formatNumber = (value: number): string =>
  new Intl.NumberFormat("en-US").format(value);

export const formatTokens = (value: number): string => `${formatNumber(value)} tok`;

export const formatPercent = (value: number): string => `${(value * 100).toFixed(1)}%`;

export const formatDateTime = (isoValue: string): string =>
  new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(new Date(isoValue));

export const formatDuration = (durationMs: number | null): string => {
  if (durationMs === null) {
    return "-";
  }

  const totalSeconds = Math.floor(durationMs / 1000);
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;

  if (minutes === 0) {
    return `${seconds}s`;
  }

  return `${minutes}m ${seconds}s`;
};
