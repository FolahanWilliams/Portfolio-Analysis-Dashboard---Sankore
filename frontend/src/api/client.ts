import type {
  AlertFeed,
  Attribution,
  Exposure,
  Meta,
  Risk,
  Scenario,
  ScenarioRequest,
  SnapshotAttribution,
  SnapshotRisk,
  Summary,
  WindowCode,
} from "../types/api";

// In dev, Vite proxies /api -> FastAPI (see vite.config.ts). Override with
// VITE_API_BASE for a deployed backend.
const BASE = import.meta.env.VITE_API_BASE ?? "/api";

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

async function get<T>(path: string, window: WindowCode, live = false): Promise<T> {
  const url = `${BASE}${path}?window=${window}${live ? "&live=1" : ""}`;
  let res: Response;
  try {
    res = await fetch(url);
  } catch (e) {
    throw new ApiError(0, `Cannot reach the analytics API. Is the backend running? (${url})`);
  }
  if (!res.ok) {
    throw new ApiError(res.status, `Request failed (${res.status}) for ${path}`);
  }
  return (await res.json()) as T;
}

export const api = {
  meta: async (live = false): Promise<Meta> => {
    const res = await fetch(`${BASE}/meta${live ? "?live=1" : ""}`);
    if (!res.ok) throw new ApiError(res.status, "Failed to load metadata");
    return (await res.json()) as Meta;
  },
  summary: (w: WindowCode, live = false) => get<Summary>("/summary", w, live),
  exposure: (w: WindowCode, live = false) => get<Exposure>("/exposure", w, live),
  risk: (w: WindowCode, live = false) => get<Risk | SnapshotRisk>("/risk", w, live),
  attribution: (w: WindowCode, live = false) =>
    get<Attribution | SnapshotAttribution>("/attribution", w, live),
  alerts: (w: WindowCode, live = false) => get<AlertFeed>("/alerts", w, live),
  scenario: async (req: ScenarioRequest, live = false): Promise<Scenario> => {
    const res = await fetch(`${BASE}/scenario${live ? "?live=1" : ""}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(req),
    });
    if (!res.ok) throw new ApiError(res.status, `Scenario request failed (${res.status})`);
    return (await res.json()) as Scenario;
  },
};
