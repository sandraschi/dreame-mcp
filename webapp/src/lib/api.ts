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

export interface ConnectionInfo {
  mode: string;
  connected: boolean;
  configured: boolean;
  ip: string | null;
  did: string | null;
  user: string | null;
  user_set: boolean;
  password_set: boolean;
  country: string;
  cloud_error: string | null;
  startup_error: string | null;
}

export interface ConnectionUpdate {
  ip?: string;
  user?: string;
  password?: string;
  country?: string;
}

export interface ConnectionUpdateResult {
  updated: string[];
  env_file: string;
  connection: ConnectionInfo;
}

export interface ConnectionTestResult {
  success: boolean;
  mode?: string;
  error?: string;
  did?: string | null;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, init);
  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const body = (await res.json()) as {
        error?: string;
        detail?: string;
        message?: string;
      };
      detail = body.error ?? body.detail ?? body.message ?? detail;
    } catch {
      /* non-JSON error body — keep HTTP status */
    }
    throw new Error(detail);
  }
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
  getConnection: () => request<ConnectionInfo>("/api/v1/connection"),
  updateConnection: (update: ConnectionUpdate) =>
    request<ConnectionUpdateResult>("/api/v1/connection", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(update),
    }),
  testConnection: (update: ConnectionUpdate) =>
    request<ConnectionTestResult>("/api/v1/connection/test", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(update),
    }),
  shutdown: () =>
    request<ControlResponse>("/api/v1/shutdown", { method: "POST" }),
};
