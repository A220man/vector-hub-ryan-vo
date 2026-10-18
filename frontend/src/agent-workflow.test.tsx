import { vi, it, expect } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { App } from './App'
import { api } from './api/client'
vi.mock('./api/client', () => ({ api: {
 auth: { me: vi.fn(), login: vi.fn(), logout: vi.fn() },
 projects: { list: vi.fn() }, worktrees: { list: vi.fn() },
 agents: { list: vi.fn(), create: vi.fn(), get: vi.fn(), start: vi.fn(), stop: vi.fn(), complete: vi.fn() },
}}))
vi.mock('react-router-dom', async () => {
 const real = await vi.importActual<typeof import('react-router-dom')>('react-router-dom')
 return { ...real, BrowserRouter: ({children}: {children: React.ReactNode}) => <real.MemoryRouter initialEntries={['/agents']}>{children}</real.MemoryRouter> }
})
it.each([['stop', 'Stop', 'stopped'], ['complete', 'Complete', 'completed']] as const)('creates and starts a run, then uses %s through visible controls', async (action, label, finalStatus) => {
 vi.clearAllMocks()
 const run = { id: 'run-qa', worktree_id: 'worktree-qa', agent_name: 'claude-code', prompt: 'QA task', status: 'pending', created_at: new Date().toISOString(), updated_at: new Date().toISOString(), started_at: null, finished_at: null }
 vi.mocked(api.auth.me).mockResolvedValue({ sub: 'test', name: 'Test', email: 'test@example.com', roles: ['admin'] })
 vi.mocked(api.agents.list).mockResolvedValue([])
 vi.mocked(api.worktrees.list).mockResolvedValue([{ id: 'worktree-qa', name: 'QA worktree', status: 'ready' }] as never)
 vi.mocked(api.agents.create).mockResolvedValue(run as never)
 vi.mocked(api.agents.get).mockImplementation(async () => ({...run}) as never)
 vi.mocked(api.agents.start).mockImplementation(async () => { run.status = 'running'; return {...run} as never })
 vi.mocked(api.agents[action]).mockImplementation(async () => { run.status = finalStatus; return {...run} as never })
 render(<App />)
 fireEvent.click(await screen.findByRole('link', {name: 'New Agent Run'}))
 await screen.findByRole('option', {name: /QA worktree/})
 fireEvent.change(screen.getByRole('textbox'), {target: {value: 'QA task'}})
 fireEvent.click(screen.getByRole('button', {name: 'Create'}))
 expect(await screen.findByRole('heading', {name: 'claude-code'})).toBeInTheDocument()
 expect(api.agents.create).toHaveBeenCalledWith('worktree-qa', expect.objectContaining({prompt: 'QA task'}))
 fireEvent.click(screen.getByRole('button', {name: 'Start'}))
 await waitFor(() => expect(api.agents.start).toHaveBeenCalledWith('run-qa'))
 expect(await screen.findByText('running', {exact: true})).toBeInTheDocument()
 fireEvent.click(screen.getByRole('button', {name: label}))
 await waitFor(() => expect(api.agents[action]).toHaveBeenCalledWith('run-qa'))
 expect(await screen.findByText(finalStatus, {exact: true})).toBeInTheDocument()
 expect(screen.getByRole('button', {name: 'Start'})).toBeDisabled()
})
