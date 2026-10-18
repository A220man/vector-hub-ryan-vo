/** Worktree detail page. */
import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import { StatusBadge } from '../components/StatusBadge'
import type { Worktree } from '../types'

export function WorktreeDetailPage() {
  const { id } = useParams<{ id: string }>()
  const [worktree, setWorktree] = useState<Worktree | null>(null)
  const [error, setError] = useState('')
  const navigate = useNavigate()

  useEffect(() => {
    let active = true
    setWorktree(null); setError('')
    if (!id) { setError('Worktree ID is missing'); return }
    api.worktrees.get(id).then(value => {
      if (active) setWorktree(value)
    }).catch(() => {
      if (active) setError('Unable to load this worktree. It may have been removed.')
    })
    return () => { active = false }
  }, [id])

  async function handleDelete() {
    if (!confirm('Are you sure you want to archive this worktree?')) return
    try {
      await api.worktrees.delete(id!)
      navigate('/worktrees')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete worktree')
    }
  }

  async function handleViewDiff() {
    navigate(`/worktrees/${id}/diff`)
  }

  return (
    <section className="space-y-4">
      <button onClick={() => navigate('/worktrees')} className="text-sm text-blue-600 hover:underline">← Back to worktrees</button>
      {error ? <p role="alert">{error}</p> : !worktree ? <p role="status">Loading worktree…</p> : <>
        <h1 className="text-2xl font-bold">{worktree.name} ({worktree.branch})</h1>
        <dl className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <dt>Project ID</dt><dd>{worktree.project_id}</dd>
          <dt>Start reference</dt><dd>{worktree.start_ref}</dd>
          <dt>Status</dt><dd><StatusBadge status={worktree.status} /></dd>
          <dt>Path</dt><dd className="font-mono text-sm">{worktree.path || '—'}</dd>
        </dl>
        <div className="flex space-x-4 pt-4">
          <button
            onClick={handleViewDiff}
            disabled={worktree.status !== 'ready'}
            className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 disabled:opacity-50"
          >
            View Diff
          </button>
          <button
            onClick={handleDelete}
            className="px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-md hover:bg-red-700"
          >
            Archive
          </button>
        </div>
      </>}
    </section>
  )
}