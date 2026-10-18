/** Typed API client for Vector Hub backend. */

import type {
  Project,
  ProjectCreate,
  Worktree,
  WorktreeCreate,
  AgentRun,
  AgentRunCreate,
  User,
} from '../types'

const API_BASE = import.meta.env.VITE_API_URL || '/api/v1'

async function fetchJson<T>(url: string, options?: RequestInit): Promise<T> {
  const headers = new Headers(options?.headers)
  if (!headers.has('Content-Type')) headers.set('Content-Type', 'application/json')
  const method = (options?.method || 'GET').toUpperCase()
  const requiresCsrf = !['GET', 'HEAD', 'OPTIONS'].includes(method)
    && url !== `${API_BASE}/auth/demo-login`
  if (requiresCsrf) {
    // Fetch the current session token for each write; never reuse one across logins.
    const tokenResponse = await fetch(`${API_BASE}/auth/csrf`, { credentials: 'include' })
    if (!tokenResponse.ok) throw new Error('Unable to verify the current session; sign in again')
    const token = await tokenResponse.json()
    if (typeof token.csrf_token !== 'string' || !token.csrf_token) {
      throw new Error('The current session has no CSRF token')
    }
    headers.set('X-CSRF-Token', token.csrf_token)
  }
  const res = await fetch(url, {
    ...options,
    headers,
    credentials: 'include',
  })

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(error.detail || `HTTP ${res.status}`)
  }

  if (res.status === 204) {
    return undefined as T
  }

  return res.json()
}

export const api = {
  // Projects
  projects: {
    clone: (id: string) => fetchJson<Project>(`${API_BASE}/projects/${id}/clone`, { method: 'POST' }),
    list: (params?: { skip?: number; limit?: number; status?: string; search?: string }) => {
      const q = new URLSearchParams(params as Record<string, string>).toString()
      return fetchJson<Project[]>(`${API_BASE}/projects${q ? `?${q}` : ''}`)
    },
    create: (data: ProjectCreate) =>
      fetchJson<Project>(`${API_BASE}/projects`, {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    get: (id: string) => fetchJson<Project>(`${API_BASE}/projects/${id}`),
    update: (id: string, data: Partial<ProjectCreate>) =>
      fetchJson<Project>(`${API_BASE}/projects/${id}`, {
        method: 'PATCH',
        body: JSON.stringify(data),
      }),
    delete: (id: string) => fetchJson<Project>(`${API_BASE}/projects/${id}`, {
      method: 'DELETE',
    }),
  },

  // Worktrees
  worktrees: {
    list: (params?: { skip?: number; limit?: number; status?: string; project_id?: string; search?: string }) => {
      const q = new URLSearchParams(params as Record<string, string>).toString()
      return fetchJson<Worktree[]>(`${API_BASE}/worktrees${q ? `?${q}` : ''}`)
    },
    create: (projectId: string, data: WorktreeCreate) =>
      fetchJson<Worktree>(`${API_BASE}/worktrees/${projectId}`, {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    get: (id: string) => fetchJson<Worktree>(`${API_BASE}/worktrees/${id}`),
    delete: (id: string) => fetchJson<Worktree>(`${API_BASE}/worktrees/${id}`, {
      method: 'DELETE',
    }),
    diff: (id: string) => fetchJson<{
      worktree_id: string
      diff_stat: string
      diff: string
      start_ref: string
    }>(`${API_BASE}/worktrees/${id}/diff`),
  },

  // Agent Runs
  agents: {
    list: (params?: { skip?: number; limit?: number; worktree_id?: string; status?: string; agent_name?: string }) => {
      const q = new URLSearchParams(params as Record<string, string>).toString()
      return fetchJson<AgentRun[]>(`${API_BASE}/agent-runs${q ? `?${q}` : ''}`)
    },
    create: (worktreeId: string, data: AgentRunCreate) =>
      fetchJson<AgentRun>(`${API_BASE}/agent-runs?worktree_id=${worktreeId}`, {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    get: (id: string) => fetchJson<AgentRun>(`${API_BASE}/agent-runs/${id}`),
    update: (id: string, data: Partial<AgentRunCreate>) =>
      fetchJson<AgentRun>(`${API_BASE}/agent-runs/${id}`, {
        method: 'PATCH',
        body: JSON.stringify(data),
      }),
    start: (id: string) =>
      fetchJson<AgentRun>(`${API_BASE}/agent-runs/${id}/start`, { method: 'POST' }),
    stop: (id: string) =>
      fetchJson<AgentRun>(`${API_BASE}/agent-runs/${id}/stop`, { method: 'POST' }),
    complete: (id: string) =>
      fetchJson<AgentRun>(`${API_BASE}/agent-runs/${id}/complete`, { method: 'POST' }),
    logs: (id: string) => fetchJson<Record<string, unknown>>(`${API_BASE}/agent-runs/${id}/logs`),
  },

  // Auth
  auth: {
    me: () => fetchJson<User>(`${API_BASE}/auth/me`),
    login: () => fetchJson<{ auth_url: string; state: string }>(`${API_BASE}/auth/login`),
    demoLogin: () =>
      fetchJson<{ message: string }>(`${API_BASE}/auth/demo-login`, {
        method: 'POST',
        body: JSON.stringify({}),
      }),
    logout: () =>
      fetchJson<{ message: string }>(`${API_BASE}/auth/logout`, { method: 'POST' }),
    csrf: () => fetchJson<{ csrf_token: string }>(`${API_BASE}/auth/csrf`),
  },
}