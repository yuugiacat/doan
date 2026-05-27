// VITE_BACKEND_URL=https://your-backend.onrender.com (production)
// Nếu không set → dùng relative URL, Vite proxy sẽ forward sang localhost (dev)
const BACKEND = import.meta.env.VITE_BACKEND_URL ?? ''
const BASE = `${BACKEND}/api/v1`

async function request<T>(path: string, opts?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...opts,
  })
  if (!res.ok) throw new Error(`API error ${res.status}`)
  return res.json()
}

export const api = {
  createSession: () => request<{ session_id: string; started_at: number }>('/sessions/', { method: 'POST' }),

  listSessions: () => request<any[]>('/sessions/'),

  endSession: (id: string) => request<any>(`/sessions/${id}/end`, { method: 'POST' }),

  getReport: (id: string) => request<any>(`/sessions/${id}/report`),

  getScores: (id: string) => request<any[]>(`/analytics/${id}/scores`),

  getAlerts: (id: string) => request<any[]>(`/analytics/${id}/alerts`),
}
