/** Dashboard page - overview of projects, worktrees, and agent runs. */
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import { StatusBadge } from '../components/StatusBadge'
import type { Project, Worktree, AgentRun } from '../types'

export function Dashboard() {
  const [projects, setProjects] = useState<Project[]>([])
  const [worktrees, setWorktrees] = useState<Worktree[]>([])
  const [agentRuns, setAgentRuns] = useState<AgentRun[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadData()
  }, [])

  async function loadData() {
    try {
      const [projectsData, worktreesData, runsData] = await Promise.all([
        api.projects.list({ limit: 5 }),
        api.worktrees.list({ limit: 5 }),
        api.agents.list({ limit: 5 }),
      ])
      setProjects(projectsData)
      setWorktrees(worktreesData)
      setAgentRuns(runsData)
    } catch (error) {
      console.error('Failed to load dashboard data:', error)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-4 border-blue-600 border-t-transparent"></div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Dashboard</h1>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <StatCard
          title="Projects"
          value={projects.length}
          icon="📁"
          link="/projects"
        />
        <StatCard
          title="Worktrees"
          value={worktrees.length}
          icon="🌳"
          link="/worktrees"
        />
        <StatCard
          title="Agent Runs"
          value={agentRuns.length}
          icon="🤖"
          link="/agents"
        />
      </div>

      {/* Recent Projects */}
      <section className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Recent Projects</h2>
          <Link to="/projects" className="text-sm text-blue-600 hover:text-blue-800 dark:text-blue-400">
            View all →
          </Link>
        </div>
        <div className="divide-y divide-gray-200 dark:divide-gray-700">
          {projects.length === 0 ? (
            <div className="p-8 text-center text-gray-500 dark:text-gray-400">
              No projects yet. <Link to="/projects/new" className="text-blue-600 hover:underline">Create one</Link>
            </div>
          ) : (
            projects.map((project) => (
              <Link
                key={project.id}
                to={`/projects/${project.id}`}
                className="flex items-center justify-between p-4 hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors"
              >
                <div>
                  <p className="font-medium text-gray-900 dark:text-white">{project.name}</p>
                  <p className="text-sm text-gray-500 dark:text-gray-400">{project.git_url}</p>
                </div>
                <StatusBadge status={project.status} />
              </Link>
            ))
          )}
        </div>
      </section>

      {/* Recent Worktrees */}
      <section className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Recent Worktrees</h2>
          <Link to="/worktrees" className="text-sm text-blue-600 hover:text-blue-800 dark:text-blue-400">
            View all →
          </Link>
        </div>
        <div className="divide-y divide-gray-200 dark:divide-gray-700">
          {worktrees.length === 0 ? (
            <div className="p-8 text-center text-gray-500 dark:text-gray-400">
              No worktrees yet. <Link to="/worktrees/new" className="text-blue-600 hover:underline">Create one</Link>
            </div>
          ) : (
            worktrees.map((wt) => (
              <Link
                key={wt.id}
                to={`/worktrees/${wt.id}`}
                className="flex items-center justify-between p-4 hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors"
              >
                <div>
                  <p className="font-medium text-gray-900 dark:text-white">{wt.name} ({wt.branch})</p>
                  <p className="text-sm text-gray-500 dark:text-gray-400">Project: {wt.project_id}</p>
                </div>
                <StatusBadge status={wt.status} />
              </Link>
            ))
          )}
        </div>
      </section>

      {/* Recent Agent Runs */}
      <section className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Recent Agent Runs</h2>
          <Link to="/agents" className="text-sm text-blue-600 hover:text-blue-800 dark:text-blue-400">
            View all →
          </Link>
        </div>
        <div className="divide-y divide-gray-200 dark:divide-gray-700">
          {agentRuns.length === 0 ? (
            <div className="p-8 text-center text-gray-500 dark:text-gray-400">
              No agent runs yet. <Link to="/agents/new" className="text-blue-600 hover:underline">Start one</Link>
            </div>
          ) : (
            agentRuns.map((run) => (
              <Link
                key={run.id}
                to={`/agents/${run.id}`}
                className="flex items-center justify-between p-4 hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors"
              >
                <div>
                  <p className="font-medium text-gray-900 dark:text-white">
                    {run.agent_name} - {run.prompt?.slice(0, 50) || 'No prompt'}
                  </p>
                  <p className="text-sm text-gray-500 dark:text-gray-400">
                    Worktree: {run.worktree_id.slice(0, 16)}...
                  </p>
                </div>
                <StatusBadge status={run.status} />
              </Link>
            ))
          )}
        </div>
      </section>
    </div>
  )
}

function StatCard({ title, value, icon, link }: { title: string; value: number; icon: string; link: string }) {
  return (
    <Link to={link} className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-6 hover:shadow-md transition-shadow">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-medium text-gray-500 dark:text-gray-400">{title}</p>
          <p className="text-3xl font-bold text-gray-900 dark:text-white mt-1">{value}</p>
        </div>
        <span className="text-4xl">{icon}</span>
      </div>
    </Link>
  )
}