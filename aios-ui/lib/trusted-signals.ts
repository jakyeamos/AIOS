export type TrustedSignalProvenance = "confirmed" | "inferred" | "missing" | "contradictory";

export type TrustedSignalSource = {
  label: string;
  table?: string;
  field?: string;
};

export type TrustedSignal<T> = {
  value: T;
  provenance: TrustedSignalProvenance;
  confidence: number;
  source: TrustedSignalSource;
  freshness: string;
  explanation: string;
  missingReason: string | null;
  contradiction: string | null;
};

export const trustedSignal = <T>(signal: TrustedSignal<T>): TrustedSignal<T> => signal;

export const sourceLabel = (signal: TrustedSignal<unknown>): string => {
  const field = signal.source.field ? `.${signal.source.field}` : "";
  const table = signal.source.table ? ` (${signal.source.table}${field})` : "";
  return `${signal.source.label}${table}`;
};
