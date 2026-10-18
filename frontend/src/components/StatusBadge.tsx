/** Status badge component. */
import type { ProjectStatus, WorktreeStatus, AgentRunStatus } from '../types'

type StatusValue = ProjectStatus | WorktreeStatus | AgentRunStatus

const STATUS_COLORS: Record<string, string> = {
  cloning: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400',
  pending: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400',
  ready: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400',

  error: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400',
  archived: 'bg-gray-100 text-gray-800 dark:bg-gray-900/30 dark:text-gray-400',
  creating: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400',
  running: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400',
  completed: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400',
  failed: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400',
  stopped: 'bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-400',
}

export function StatusBadge({ status }: { status: StatusValue }) {
  const colorClass = STATUS_COLORS[status] || 'bg-gray-100 text-gray-800'
  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium capitalize ${colorClass}`}
    >
      {status}
    </span>
  )
}