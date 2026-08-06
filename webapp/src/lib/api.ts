export const API_BASE = "http://127.0.0.1:10894";

// ---- Backend shapes (src/dreame_mcp/server.py + client.py) ----

export interface Health {
  status: string;
  service: string;
  connected: boolean;
  local_miot: boolean;
  mode: string;
  did: string | null;
  timestamp: string;
}

export interface DreameStatus {
  success: boolean;
  error?: string;
  message?: string;
  state?: string;
  battery?: number;
  cleaned_area?: number;
  cleaning_time?: number;
  is_charging?: boolean;
  is_cleaning?: boolean;
  fan_speed?: number;
  timestamp?: string;
}

export interface Point {
  x: number;
  y: number;
}

export interface MapQuad {
  p1: Point;
  p2: Point;
  p3: Point;
  p4: Point;
}

export interface MapData {
  rooms?: number;
  robot_position?: Point | null;
  charger_position?: Point | null;
  path?: Point[];
  virtual_walls?: { p1: Point; p2: Point }[];
  no_go_areas?: MapQuad[];
  no_mop_areas?: MapQuad[];
  dimensions?: {
    top: number;
    left: number;
    height: number;
    width: number;
    grid_size: number;
  } | null;
}

export interface DreameMapResponse {
  success: boolean;
  error?: string;
  timeout?: boolean;
  image?: string;
  image_url?: string;
  map_data?: MapData;
  render_error?: string;
  raw_b64?: string;
}

export interface ControlResponse {
  success: boolean;
  message?: string;
  error?: string;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, init);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return (await res.json()) as T;
}

export const api = {
  getHealth: () => request<Health>("/api/v1/health"),
  getStatus: () => request<DreameStatus>("/api/v1/status"),
  getMap: () => request<DreameMapResponse>("/api/v1/map"),
  control: (cmd: string) =>
    request<ControlResponse>(`/api/v1/control/${encodeURIComponent(cmd)}`, {
      method: "POST",
    }),
  getDiagnostics: () =>
    request<{
      status: string;
      server: string;
      version: string;
      tool_count: number;
    }>("/api/v1/diagnostics"),
  shutdown: () =>
    request<ControlResponse>("/api/v1/shutdown", { method: "POST" }),
};
