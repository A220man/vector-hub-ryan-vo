/** Agent run detail page. */
import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import { StatusBadge } from '../components/StatusBadge'
import type { AgentRun } from '../types'

export function AgentRunDetailPage() {
  const { id } = useParams<{ id: string }>()
  const [run, setRun] = useState<AgentRun | null>(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  useEffect(() => {
    let active = true
    setRun(null); setError('')
    if (!id) { setError('Agent run ID is missing'); return }
    api.agents.get(id).then(value => {
      if (active) setRun(value)
    }).catch(() => {
      if (active) setError('Unable to load this agent run. It may have been removed.')
    })
    return () => { active = false }
  }, [id])

  async function handleAction(action: 'start' | 'stop' | 'complete') {
    if (!run) return
    setLoading(true)
    try {
      if (action === 'start') await api.agents.start(id!)
      else if (action === 'stop') await api.agents.stop(id!)
      else if (action === 'complete') await api.agents.complete(id!)
      const updated = await api.agents.get(id!)
      setRun(updated)
    } catch (err) {
      setError(err instanceof Error ? err.message : `Failed to ${action} agent run`)
    } finally {
      setLoading(false)
    }
  }

  const canStart = run?.status === 'pending'
  const canStop = run?.status === 'running' || run?.status === 'pending'
  const canComplete = run?.status === 'running'

  return (
    <section className="space-y-4">
      <button onClick={() => navigate('/agents')} className="text-sm text-blue-600 hover:underline">← Back to agent runs</button>
      {error ? <p role="alert">{error}</p> : !run ? <p role="status">Loading agent run…</p> : <>
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-bold">{run.agent_name}</h1>
          <StatusBadge status={run.status} />
        </div>
        <dl className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <dt>Worktree ID</dt><dd>{run.worktree_id}</dd>
          <dt>Prompt</dt><dd className="whitespace-pre-wrap">{run.prompt || 'No prompt'}</dd>
          <dt>Command</dt><dd className="font-mono text-sm">{run.command || '—'}</dd>
          <dt>Created</dt><dd>{new Date(run.created_at).toLocaleString()}</dd>
          <dt>Started</dt><dd>{run.started_at ? new Date(run.started_at).toLocaleString() : '—'}</dd>
          <dt>Finished</dt><dd>{run.finished_at ? new Date(run.finished_at).toLocaleString() : '—'}</dd>
        </dl>
        <div className="flex space-x-4 pt-4">
          <button
            onClick={() => handleAction('start')}
            disabled={!canStart || loading}
            className="px-4 py-2 text-sm font-medium text-white bg-green-600 rounded-md hover:bg-green-700 disabled:opacity-50"
          >
            Start
          </button>
          <button
            onClick={() => handleAction('stop')}
            disabled={!canStop || loading}
            className="px-4 py-2 text-sm font-medium text-white bg-orange-600 rounded-md hover:bg-orange-700 disabled:opacity-50"
          >
            Stop
          </button>
          <button
            onClick={() => handleAction('complete')}
            disabled={!canComplete || loading}
            className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 disabled:opacity-50"
          >
            Complete
          </button>
        </div>
        {loading && <p className="text-sm text-gray-500">Processing...</p>}
      </>}
    </section>
  )
}