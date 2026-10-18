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
it('keeps the created project visible and allows cloning through the UI', async () => {
 const pendingProject = { id: 'project-qa', name: 'QA Project', git_url: 'https://example.com/repo.git', base_ref: 'main', status: 'pending', created_at: new Date().toISOString(), updated_at: new Date().toISOString() }
 const readyProject = { ...pendingProject, status: 'ready', base_path: '/data/vectorhub/project-qa', updated_at: new Date().toISOString() }
 vi.mocked(api.auth.me).mockResolvedValue({ sub: 'test', name: 'Test', email: 'test@example.com', roles: ['admin'] })
 vi.mocked(api.projects.list).mockResolvedValueOnce([]).mockResolvedValue([readyProject] as never)
 vi.mocked(api.projects.create).mockResolvedValue(pendingProject as never)
 vi.mocked(api.projects.get).mockResolvedValue(pendingProject as never)
 vi.mocked(api.projects.clone).mockResolvedValue(readyProject as never)
 vi.mocked(api.worktrees.list).mockResolvedValue([])
 vi.mocked(api.agents.list).mockResolvedValue([])
 const {container} = render(<App />)
 fireEvent.click(await screen.findByRole('button', {name: 'New Project'}))
 const inputs = container.querySelectorAll('form input')
 fireEvent.change(inputs[0], {target: {value: pendingProject.name}})
 fireEvent.change(inputs[1], {target: {value: pendingProject.git_url}})
 fireEvent.click(screen.getByRole('button', {name: /^Create$/}))
 await waitFor(() => expect(api.projects.create).toHaveBeenCalled())
 // After creation, we're on the project detail page
 expect(await screen.findByRole('heading', {name: pendingProject.name})).toBeInTheDocument()
 // On detail page, prepare the repository
 expect(await screen.findByRole('button', {name: 'Prepare repository'})).toBeInTheDocument()
 fireEvent.click(screen.getByRole('button', {name: 'Prepare repository'}))
 await waitFor(() => expect(api.projects.clone).toHaveBeenCalledWith(pendingProject.id))
 // After clone, the project should be ready and show "Create worktree" link
 expect(await screen.findByRole('link', {name: 'Create worktree'})).toBeInTheDocument()
})
