// Presentation-only formatting helpers. All fund math happens on the backend;
// these just turn numbers into strings for display.

export function fmtPct(x: number | null | undefined, dp = 2): string {
  if (x === null || x === undefined || Number.isNaN(x)) return "--";
  return `${(x * 100).toFixed(dp)}%`;
}

export function fmtSignedPct(x: number | null | undefined, dp = 2): string {
  if (x === null || x === undefined || Number.isNaN(x)) return "--";
  const s = (x * 100).toFixed(dp);
  return x >= 0 ? `+${s}%` : `${s}%`;
}

export function fmtNum(x: number | null | undefined, dp = 2): string {
  if (x === null || x === undefined || Number.isNaN(x)) return "--";
  return x.toLocaleString("en-US", { minimumFractionDigits: dp, maximumFractionDigits: dp });
}

export function fmtMoney(x: number | null | undefined, currency = "USD"): string {
  if (x === null || x === undefined || Number.isNaN(x)) return "--";
  const abs = Math.abs(x);
  let scaled = x;
  let suffix = "";
  if (abs >= 1e9) {
    scaled = x / 1e9;
    suffix = "bn";
  } else if (abs >= 1e6) {
    scaled = x / 1e6;
    suffix = "m";
  } else if (abs >= 1e3) {
    scaled = x / 1e3;
    suffix = "k";
  }
  const sym = currency === "USD" ? "$" : "";
  return `${x < 0 ? "-" : ""}${sym}${Math.abs(scaled).toLocaleString("en-US", {
    minimumFractionDigits: suffix ? 2 : 0,
    maximumFractionDigits: 2,
  })}${suffix}`;
}

export function signClass(x: number | null | undefined): string {
  if (x === null || x === undefined || Number.isNaN(x)) return "text-slate-500";
  if (x > 0) return "text-positive";
  if (x < 0) return "text-negative";
  return "text-slate-600";
}

// Map a value in [-1, 1]-ish to a heat colour. Blue for positive weight,
// diverging red/green for active weights.
export function heatBlue(v: number, max: number): string {
  const t = max > 0 ? Math.min(v / max, 1) : 0;
  // very light -> brand blue
  const l = 97 - t * 58;
  return `hsl(217, 72%, ${l}%)`;
}

export function diverging(v: number, max: number): string {
  const t = max > 0 ? Math.max(-1, Math.min(v / max, 1)) : 0;
  if (t >= 0) return `hsl(158, 55%, ${93 - t * 42}%)`;
  return `hsl(2, 62%, ${93 - -t * 42}%)`;
}
