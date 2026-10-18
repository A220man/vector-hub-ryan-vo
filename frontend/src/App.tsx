import { useState } from 'react'
/** Main App component with routing. */
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider, useAuth } from './context/AuthContext'
import { Layout } from './components/Layout'
import { Dashboard } from './pages/Dashboard'
import { ProjectDetailPage } from './pages/ProjectDetailPage'
import { ProjectsPage } from './pages/ProjectsPage'
import { CreateProjectPage } from './pages/CreateProjectPage'
import { WorktreesPage } from './pages/WorktreesPage'
import { WorktreeDetailPage } from './pages/WorktreeDetailPage'
import { CreateWorktreePage } from './pages/CreateWorktreePage'
import { AgentRunsPage } from './pages/AgentRunsPage'
import { AgentRunDetailPage } from './pages/AgentRunDetailPage'
import { CreateAgentRunPage } from './pages/CreateAgentRunPage'

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth()

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-4 border-blue-600 border-t-transparent"></div>
      </div>
    )
  }

  if (!user) {
    return <Navigate to="/login" replace />
  }

  return <>{children}</>
}

function AppRoutes() {
  return (
    <Routes>
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        }
      >
        <Route index element={<Dashboard />} />
        <Route path="projects" element={<ProjectsPage />} />
        <Route path="projects/new" element={<CreateProjectPage />} />
        <Route path="projects/:id" element={<ProjectDetailPage />} />
        <Route path="projects/:id/worktrees/new" element={<CreateWorktreePage />} />
        <Route path="worktrees" element={<WorktreesPage />} />
        <Route path="worktrees/new" element={<CreateWorktreePage />} />
        <Route path="worktrees/:id" element={<WorktreeDetailPage />} />
        <Route path="agents" element={<AgentRunsPage />} />
        <Route path="agents/new" element={<CreateAgentRunPage />} />
        <Route path="agents/:id" element={<AgentRunDetailPage />} />
      </Route>
      <Route path="/login" element={<LoginPage />} />
    </Routes>
  )
}

function LoginPage() {
  const { login, user } = useAuth()
  const [error, setError] = useState('')
  const [signingIn, setSigningIn] = useState(false)
  if (user) return <Navigate to="/" replace />
  async function signIn() {
    setError(''); setSigningIn(true)
    try { await login() }
    catch (cause) { setError(cause instanceof Error ? cause.message : 'Unable to sign in') }
    finally { setSigningIn(false) }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900 px-4">
      <div className="max-w-md w-full bg-white dark:bg-gray-800 rounded-lg shadow-lg p-8">
        <h1 className="text-2xl font-bold text-center text-gray-900 dark:text-white mb-8">
          Vector Hub
        </h1>
        <p className="text-center text-gray-600 dark:text-gray-400 mb-8">
          Sign in to manage your agent fleet
        </p>
        <button
          onClick={signIn}
          disabled={signingIn}
          className="w-full px-4 py-3 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
        >
          {signingIn ? 'Signing in…' : import.meta.env.VITE_DEMO_MODE === 'true' ? 'Continue with Demo Mode' : 'Sign in'}
        </button>
        {error && <p role="alert">{error}</p>}
      </div>
    </div>
  )
}

export function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <AppRoutes />
      </BrowserRouter>
    </AuthProvider>
  )
}