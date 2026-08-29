const UNITS: [number, string][] = [
  [60, "second"],
  [60, "minute"],
  [24, "hour"],
  [7, "day"],
  [4.345, "week"],
  [12, "month"],
  [Number.POSITIVE_INFINITY, "year"],
];

/** No date library needed for a single relative-timestamp string. */
export function formatRelativeTime(isoDate: string): string {
  const then = new Date(isoDate).getTime();
  const diffSeconds = (Date.now() - then) / 1000;

  if (diffSeconds < 5) return "just now";

  let value = diffSeconds;
  let unit = "second";
  for (const [step, name] of UNITS) {
    if (value < step) {
      unit = name;
      break;
    }
    value /= step;
    unit = name;
  }
  const rounded = Math.floor(value);
  return `${rounded} ${unit}${rounded === 1 ? "" : "s"} ago`;
}
