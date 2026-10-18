import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api } from '../api/client'
import type { Project } from '../types'

export function ProjectDetailPage() {
  const { id } = useParams<{ id: string }>()
  const [project, setProject] = useState<Project | null>(null)
  const [error, setError] = useState('')
  const [cloning, setCloning] = useState(false)
  useEffect(() => {
    let active = true
    setProject(null); setError('')
    if (!id) { setError('Project ID is missing'); return }
    api.projects.get(id).then(value => {
      if (active) setProject(value)
    }).catch(() => {
      if (active) setError('Unable to load this project. It may have been removed or your access may have changed.')
    })
    return () => { active = false }
  }, [id])
  async function prepareProject() {
    if (!id || cloning) return
    setCloning(true); setError('')
    try {
      const updated = await api.projects.clone(id)
      setProject(updated)
      if (updated.status === 'error') setError(updated.error_message || 'Repository preparation failed. You can retry.')
    } catch (error) {
      setError(error instanceof Error ? error.message : 'Unable to prepare this repository. You can retry.')
    } finally { setCloning(false) }
  }
  return (
    <section className="space-y-4">
      <Link to="/projects">Back to projects</Link>
      {error && <p role="alert">{error}</p>}
      {!project ? (!error && <p role="status">Loading project…</p>) : <>
        <h1 className="text-2xl font-bold">{project.name}</h1>
        <dl>
          <dt>Repository</dt><dd>{project.git_url}</dd>
          <dt>Base reference</dt><dd>{project.base_ref}</dd>
          <dt>Status</dt><dd>{project.status}</dd>
        </dl>
        {(project.status === 'pending' || project.status === 'error') &&
          <button type="button" onClick={prepareProject} disabled={cloning}>
            {cloning ? 'Preparing repository…' : 'Prepare repository'}
          </button>}
        {project.status === 'ready' && <Link to={`/projects/${project.id}/worktrees/new`}>Create worktree</Link>}
        <Link to="/worktrees">Manage worktrees</Link>
      </>}
    </section>
  )
}
