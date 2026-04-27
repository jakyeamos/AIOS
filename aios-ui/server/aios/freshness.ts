const DAY_MS = 86_400_000;
const STALE_AFTER_DAYS = 45;

export const formatFreshnessLabel = (
  isoValue: string | null,
  fallback = "Unknown freshness",
): string => {
  if (!isoValue) {
    return fallback;
  }

  const timestamp = new Date(isoValue).getTime();
  if (Number.isNaN(timestamp)) {
    return isoValue;
  }

  const deltaDays = Math.max(0, Math.floor((Date.now() - timestamp) / DAY_MS));
  if (deltaDays <= 1) {
    return "Updated in the last day";
  }
  if (deltaDays < STALE_AFTER_DAYS) {
    return `Updated ${deltaDays} days ago`;
  }
  return `Stale for ${deltaDays} days`;
};

export const scoreFreshnessLabel = (freshness: string): number => {
  if (freshness.includes("last day")) {
    return 1;
  }
  if (freshness.includes("Updated") && freshness.includes("days ago")) {
    return 0.7;
  }
  if (freshness.includes("Stale")) {
    return 0.3;
  }
  return 0.5;
};
