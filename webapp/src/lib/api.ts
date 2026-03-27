const API_BASE = (import.meta as any).env?.VITE_DREAME_API_BASE?.toString?.() || ''
const MAP_URL = (import.meta as any).env?.VITE_DREAME_MAP_URL?.toString?.() || ''

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const url = path.startsWith('http') ? path : `${API_BASE}${path}`
  const res = await fetch(url, {
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    ...options,
  })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(text || `HTTP ${res.status}`)
  }
  return res.json() as Promise<T>
}

export interface Health {
  status: string
  connected: boolean
  service?: string
  timestamp?: string
}

export interface DreameStatus {
  success: boolean
  battery?: number
  state?: string
  message?: string
  error?: string
}

export type DreameMapResponse = Record<string, unknown> & {
  image?: string
  image_url?: string
  map_data?: unknown
}

export const api = {
  getHealth: () => request<Health>('/api/v1/health'),
  getStatus: () => request<DreameStatus>('/api/v1/status'),
  getMap: () => request<DreameMapResponse>(MAP_URL || '/api/v1/map'),
  control: (cmd: string) =>
    request<{ success: boolean; message?: string }>(`/api/v1/control/${cmd}`, { method: 'POST' }),
}
