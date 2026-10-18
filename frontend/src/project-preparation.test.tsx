import { vi, it, expect } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { App } from './App'
import { api } from './api/client'
vi.mock('./api/client', () => ({ api: {
 auth: { me: vi.fn(), login: vi.fn(), logout: vi.fn() },
 projects: { list: vi.fn(), create: vi.fn(), get: vi.fn(), clone: vi.fn() },
 worktrees: { list: vi.fn() }, agents: { list: vi.fn() },
}}))
vi.mock('react-router-dom', async () => {
 const real = await vi.importActual<typeof import('react-router-dom')>('react-router-dom')
 return { ...real, BrowserRouter: ({children}: {children: React.ReactNode}) => <real.MemoryRouter initialEntries={['/projects']}>{children}</real.MemoryRouter> }
})
it('prepares a new project through the UI, recovers from a failure and reaches worktree creation', async () => {
 const project = { id: 'project-qa', name: 'QA Project', git_url: 'https://example.com/repo.git', base_ref: 'main', status: 'pending', created_at: new Date().toISOString(), updated_at: new Date().toISOString() }
 vi.mocked(api.auth.me).mockResolvedValue({ sub: 'test', name: 'Test', email: 'test@example.com', roles: ['admin'] })
 vi.mocked(api.projects.list).mockResolvedValueOnce([]).mockResolvedValue([project] as never)
 vi.mocked(api.projects.create).mockResolvedValue(project as never)
 vi.mocked(api.projects.get).mockResolvedValue(project as never)
 vi.mocked(api.projects.clone).mockRejectedValueOnce(new Error('Temporary clone failure')).mockImplementation(async () => { project.status = 'ready'; return {...project} as never })
 vi.mocked(api.worktrees.list).mockResolvedValue([])
 vi.mocked(api.agents.list).mockResolvedValue([])
 const {container} = render(<App />)
 fireEvent.click(await screen.findByRole('button', {name: 'New Project'}))
 const inputs = container.querySelectorAll('form input')
 fireEvent.change(inputs[0], {target: {value: project.name}})
 fireEvent.change(inputs[1], {target: {value: project.git_url}})
 fireEvent.click(screen.getByRole('button', {name: /^Create$/}))
 await waitFor(() => expect(api.projects.create).toHaveBeenCalled())
 expect(await screen.findByText(project.name)).toBeInTheDocument()
 expect(screen.queryByRole('link', {name: 'Create worktree'})).not.toBeInTheDocument()
 fireEvent.click(screen.getByRole('button', {name: 'Prepare repository'}))
 expect(await screen.findByRole('alert')).toHaveTextContent('Temporary clone failure')
 await waitFor(() => expect(screen.getByRole('button', {name: 'Prepare repository'})).toBeEnabled())
 fireEvent.click(screen.getByRole('button', {name: 'Prepare repository'}))
 fireEvent.click(await screen.findByRole('link', {name: 'Create worktree'}))
 expect(await screen.findByRole('heading', {name: 'New Worktree'})).toBeInTheDocument()
 expect(api.projects.clone).toHaveBeenCalledTimes(2)
 expect(api.projects.clone).toHaveBeenLastCalledWith(project.id)
})
