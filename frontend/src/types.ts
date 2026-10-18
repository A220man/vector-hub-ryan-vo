/** Shared type definitions matching backend schemas. */

export type ProjectStatus = 'cloning' | 'pending' | 'ready' | 'error' | 'archived'
export type WorktreeStatus = 'creating' | 'ready' | 'error' | 'archived'
export type AgentRunStatus = 'pending' | 'running' | 'completed' | 'failed' | 'stopped'

export interface Project {
  id: string
  name: string
  git_url: string
  base_ref: string
  base_path: string | null
  status: ProjectStatus
  error_message: string | null
  created_at: string
  updated_at: string
}

export interface ProjectCreate {
  name: string
  git_url: string
  base_ref?: string
}

export interface Worktree {
  id: string
  project_id: string
  name: string
  branch: string
  start_ref: string
  path: string | null
  status: WorktreeStatus
  error_message: string | null
  created_at: string
  updated_at: string
}

export interface WorktreeCreate {
  name: string
  branch: string
  start_ref?: string
}

export interface AgentRun {
  id: string
  worktree_id: string
  agent_name: string
  prompt: string | null
  command: string | null
  status: AgentRunStatus
  started_at: string | null
  finished_at: string | null
  input_tokens: number | null
  output_tokens: number | null
  cost_cents: number | null
  metrics: Record<string, unknown> | null
  created_at: string
  updated_at: string
}

export interface AgentRunCreate {
  agent_name: string
  prompt?: string | null
}

export interface User {
  sub: string
  email: string | null
  name: string | null
  roles: string[]
}

export interface AuthLoginResponse {
  auth_url: string
  state: string
}
