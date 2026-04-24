/**
 * Dreame MCP — Frontend API client with timeout + abort support.
 *
 * All requests are guarded by AbortController with a per-request timeout.
 * Map requests get a longer timeout since the cloud fetch can be slow.
 */

const API_BASE = import.meta.env.VITE_DREAME_API_BASE?.toString() ?? "";
const MAP_URL = import.meta.env.VITE_DREAME_MAP_URL?.toString() ?? "";

/** Default request timeout (ms) */
const REQUEST_TIMEOUT_MS = 15_000;
/** Map requests get a longer timeout — cloud fetch is multi-step */
const MAP_TIMEOUT_MS = 50_000;

async function request<T>(
  path: string,
  options?: RequestInit & { timeoutMs?: number },
): Promise<T> {
  const url = path.startsWith("http") ? path : `${API_BASE}${path}`;
  const timeoutMs = options?.timeoutMs ?? REQUEST_TIMEOUT_MS;

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const res = await fetch(url, {
      headers: { "Content-Type": "application/json", ...options?.headers },
      ...options,
      signal: controller.signal,
    });
    if (!res.ok) {
      const text = await res.text();
      throw new Error(text || `HTTP ${res.status}`);
    }
    return res.json() as Promise<T>;
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") {
      throw new Error(`Request timed out after ${timeoutMs / 1000}s: ${url}`);
    }
    throw err;
  } finally {
    clearTimeout(timer);
  }
}

export interface Health {
  status: string;
  connected: boolean;
  /** True after local UDP miio discover succeeds (not just DREAME_IP set). */
  local_miot?: boolean;
  did?: string | null;
  mode?: string;
  service?: string;
  timestamp?: string;
}

export interface DreameStatus {
  success: boolean;
  battery?: number;
  state?: string;
  message?: string;
  error?: string;
}

export interface Point {
  x: number;
  y: number;
}

export interface MapData {
  rooms: number;
  robot_position?: Point;
  charger_position?: Point;
  path?: Point[];
  virtual_walls?: { p1: Point; p2: Point }[];
  no_go_areas?: { p1: Point; p2: Point; p3: Point; p4: Point }[];
  no_mop_areas?: { p1: Point; p2: Point; p3: Point; p4: Point }[];
  dimensions?: {
    top: number;
    left: number;
    height: number;
    width: number;
    grid_size: number;
  };
}

export type DreameMapResponse = {
  image?: string;
  image_url?: string;
  map_data?: MapData;
  timeout?: boolean;
  error?: string;
  success?: boolean;
};

export const api = {
  getHealth: () => request<Health>("/api/v1/health"),
  getStatus: () => request<DreameStatus>("/api/v1/status"),
  getMap: () =>
    request<DreameMapResponse>(MAP_URL || "/api/v1/map", {
      timeoutMs: MAP_TIMEOUT_MS,
    }),
  control: (cmd: string) =>
    request<{ success: boolean; message?: string }>(`/api/v1/control/${cmd}`, {
      method: "POST",
    }),
};
