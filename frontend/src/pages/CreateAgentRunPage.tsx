/** Create agent run page. */
import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import type { AgentRunCreate, Worktree } from '../types'

export function CreateAgentRunPage() {
  const { id: worktreeIdFromUrl } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [worktrees, setWorktrees] = useState<Worktree[]>([])
  const [loadingWorktrees, setLoadingWorktrees] = useState(true)
  const [formData, setFormData] = useState<AgentRunCreate>({ agent_name: 'claude-code', prompt: '' })
  const [selectedWorktree, setSelectedWorktree] = useState<string>(worktreeIdFromUrl || '')
  const [creating, setCreating] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadWorktrees()
  }, [])

  async function loadWorktrees() {
    try {
      const data = await api.worktrees.list({ limit: 100 })
      const readyWorktrees = data.filter(w => w.status === 'ready')
      setWorktrees(readyWorktrees)
      if (!selectedWorktree && readyWorktrees.length > 0) {
        setSelectedWorktree(readyWorktrees[0].id)
      }
    } catch (err) {
      setError('Failed to load worktrees')
    } finally {
      setLoadingWorktrees(false)
    }
  }

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault()
    if (!selectedWorktree) {
      setError('Please select a worktree')
      return
    }
    setCreating(true)
    setError(null)
    try {
      const run = await api.agents.create(selectedWorktree, formData)
      navigate(`/agents/${run.id}`)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create agent run')
    } finally {
      setCreating(false)
    }
  }

  if (loadingWorktrees) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-4 border-blue-600 border-t-transparent"></div>
      </div>
    )
  }

  return (
    <div className="space-y-6 max-w-2xl mx-auto">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">New Agent Run</h1>
      </div>

      {error && (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-400 p-4 rounded-lg">
          {error}
        </div>
      )}

      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6">
        <form onSubmit={handleCreate} className="space-y-6">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Worktree</label>
            {worktreeIdFromUrl ? (
              <>
                <input
                  type="text"
                  value={worktrees.find(w => w.id === selectedWorktree)?.name || 'Loading...'}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-gray-100 dark:bg-gray-700"
                  disabled
                />
                <input type="hidden" value={selectedWorktree} onChange={e => setSelectedWorktree(e.target.value)} />
              </>
            ) : (
              <select
                value={selectedWorktree}
                onChange={e => setSelectedWorktree(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 dark:bg-gray-700 dark:text-white"
                required
              >
                <option value="">Select a worktree</option>
                {worktrees.map(w => (
                  <option key={w.id} value={w.id}>{w.name} ({w.branch})</option>
                ))}
              </select>
            )}
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Agent</label>
            <select
              value={formData.agent_name}
              onChange={e => setFormData({ ...formData, agent_name: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 dark:bg-gray-700 dark:text-white"
              required
            >
              <option value="claude-code">Claude Code</option>
              <option value="codex">Codex</option>
              <option value="opencode">OpenCode</option>
              <option value="custom">Custom</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Prompt</label>
            <textarea
              value={formData.prompt || ''}
              onChange={e => setFormData({ ...formData, prompt: e.target.value })}
              rows={4}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 dark:bg-gray-700 dark:text-white"
              placeholder="Describe the task for the agent..."
            />
          </div>
          <div className="flex justify-end space-x-3 pt-4">
            <button
              type="button"
              onClick={() => navigate('/agents')}
              className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 dark:text-gray-300 dark:bg-gray-700 dark:border-gray-600"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={creating}
              className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 disabled:opacity-50"
            >
              {creating ? 'Creating...' : 'Create'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}