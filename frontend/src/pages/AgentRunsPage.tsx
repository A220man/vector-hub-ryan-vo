/** Agent runs page. */
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import { StatusBadge } from '../components/StatusBadge'
import type { AgentRun } from '../types'

export function AgentRunsPage() {
  const [runs, setRuns] = useState<AgentRun[]>([])
  const [loading, setLoading] = useState(true)
  const [actionLoading, setActionLoading] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadRuns()
  }, [])

  async function loadRuns() {
    try {
      const data = await api.agents.list({ limit: 100 })
      setRuns(data)
    } catch (err) {
      setError('Failed to load agent runs')
    } finally {
      setLoading(false)
    }
  }

  async function handleAction(run: AgentRun, action: 'start' | 'stop' | 'complete') {
    setActionLoading(run.id)
    try {
      if (action === 'start') await api.agents.start(run.id)
      else if (action === 'stop') await api.agents.stop(run.id)
      else if (action === 'complete') await api.agents.complete(run.id)
      loadRuns()
    } catch (err) {
      setError(err instanceof Error ? err.message : `Failed to ${action} agent run`)
    } finally {
      setActionLoading(null)
    }
  }

  if (loading) {
    return <div className="flex items-center justify-center h-64"><div className="animate-spin rounded-full h-12 w-12 border-4 border-blue-600 border-t-transparent"></div></div>
  }

  const canStart = (run: AgentRun) => run.status === 'pending'
  const canStop = (run: AgentRun) => run.status === 'running' || run.status === 'pending'
  const canComplete = (run: AgentRun) => run.status === 'running'

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Agent Runs</h1>
        <Link
          to="/agents/new"
          className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700"
        >
          New Agent Run
        </Link>
      </div>

      {error && (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-400 p-4 rounded-lg">
          {error}
        </div>
      )}

      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 overflow-hidden">
        <table className="w-full">
          <thead className="bg-gray-50 dark:bg-gray-700/50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Agent</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Prompt</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Status</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Started</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Duration</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
            {runs.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-6 py-12 text-center text-gray-500 dark:text-gray-400">
                  No agent runs yet.
                </td>
              </tr>
            ) : (
              runs.map((run) => (
                <tr key={run.id} className="hover:bg-gray-50 dark:hover:bg-gray-700/50">
                  <td className="px-6 py-4">
                    <Link to={`/agents/${run.id}`} className="font-medium text-gray-900 dark:text-white hover:text-blue-600">
                      {run.agent_name}
                    </Link>
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-500 dark:text-gray-400 truncate max-w-xs">
                    {run.prompt?.slice(0, 60) || 'No prompt'}
                  </td>
                  <td className="px-6 py-4"><StatusBadge status={run.status} /></td>
                  <td className="px-6 py-4 text-sm text-gray-500 dark:text-gray-400">
                    {run.started_at ? new Date(run.started_at).toLocaleString() : '—'}
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-500 dark:text-gray-400">
                    {formatDuration(run.started_at, run.finished_at)}
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex items-center space-x-2">
                      {canStart(run) && (
                        <button
                          onClick={() => handleAction(run, 'start')}
                          disabled={actionLoading === run.id}
                          className="px-3 py-1 text-xs text-white bg-green-600 rounded hover:bg-green-700 disabled:opacity-50"
                        >
                          Start
                        </button>
                      )}
                      {canStop(run) && (
                        <button
                          onClick={() => handleAction(run, 'stop')}
                          disabled={actionLoading === run.id}
                          className="px-3 py-1 text-xs text-white bg-orange-600 rounded hover:bg-orange-700 disabled:opacity-50"
                        >
                          Stop
                        </button>
                      )}
                      {canComplete(run) && (
                        <button
                          onClick={() => handleAction(run, 'complete')}
                          disabled={actionLoading === run.id}
                          className="px-3 py-1 text-xs text-white bg-blue-600 rounded hover:bg-blue-700 disabled:opacity-50"
                        >
                          Complete
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function formatDuration(startedAt: string | null, finishedAt: string | null): string {
  if (!startedAt) return '—'
  const start = new Date(startedAt).getTime()
  const end = finishedAt ? new Date(finishedAt).getTime() : Date.now()
  const seconds = Math.floor((end - start) / 1000)
  if (seconds < 60) return `${seconds}s`
  const minutes = Math.floor(seconds / 60)
  const remaining = seconds % 60
  return `${minutes}m ${remaining}s`
}