/** Tests for the App component. */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { App } from './App'
import { api } from './api/client'

// Mock the API client
vi.mock('./api/client', () => ({
  api: {
    auth: {
      me: vi.fn(),
      demoLogin: vi.fn(),
      login: vi.fn(),
      logout: vi.fn(),
    },
    projects: {
      list: vi.fn(),
    },
    worktrees: {
      list: vi.fn(),
    },
    agents: {
      list: vi.fn(),
    },
  },
}))

// Replace BrowserRouter with MemoryRouter for tests
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom')
  return {
    ...actual,
    BrowserRouter: ({ children }: { children: React.ReactNode }) => (
      <actual.MemoryRouter initialEntries={['/']}>{children}</actual.MemoryRouter>
    ),
  }
})

function renderApp() {
  return render(<App />)
}

describe('App', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('shows login page when not authenticated', async () => {
    vi.mocked(api.auth.me).mockRejectedValue(new Error('Unauthorized'))

    renderApp()
    await waitFor(() => {
      expect(screen.getByText('Vector Hub')).toBeInTheDocument()
    })
    expect(screen.getByText('Sign in')).toBeInTheDocument()
  })

  it('shows dashboard after successful auth check', async () => {
    vi.mocked(api.auth.me).mockResolvedValue({
      sub: 'demo-user',
      email: 'demo@vectorhub.local',
      name: 'Demo User',
      roles: ['admin'],
    } as const)
    vi.mocked(api.projects.list).mockResolvedValue([])
    vi.mocked(api.worktrees.list).mockResolvedValue([])
    vi.mocked(api.agents.list).mockResolvedValue([])

    renderApp()
    await waitFor(() => {
      expect(screen.getByText('Dashboard')).toBeInTheDocument()
    })
  })

  it('renders login page with correct elements', async () => {
    vi.mocked(api.auth.me).mockRejectedValue(new Error('Unauthorized'))

    renderApp()
    await waitFor(() => {
      expect(screen.getByText('Vector Hub')).toBeInTheDocument()
    })
    expect(screen.getByText('Sign in to manage your agent fleet')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Sign in' })).toBeInTheDocument()
  })
})