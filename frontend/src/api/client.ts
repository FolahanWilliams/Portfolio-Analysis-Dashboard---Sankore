import type {
  Attribution,
  Exposure,
  Meta,
  Risk,
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

async function get<T>(path: string, window: WindowCode): Promise<T> {
  const url = `${BASE}${path}?window=${window}`;
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
  meta: async (): Promise<Meta> => {
    const res = await fetch(`${BASE}/meta`);
    if (!res.ok) throw new ApiError(res.status, "Failed to load metadata");
    return (await res.json()) as Meta;
  },
  summary: (w: WindowCode) => get<Summary>("/summary", w),
  exposure: (w: WindowCode) => get<Exposure>("/exposure", w),
  risk: (w: WindowCode) => get<Risk>("/risk", w),
  attribution: (w: WindowCode) => get<Attribution>("/attribution", w),
};
