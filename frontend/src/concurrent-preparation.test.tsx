import { vi, it, expect } from 'vitest'
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { ProjectsPage } from './pages/ProjectsPage'
import { api } from './api/client'
import type { Project } from './types'
vi.mock('./api/client', () => ({api: {projects: {list: vi.fn(), clone: vi.fn()}}}))
it('preserves both results when two repositories finish preparing independently', async () => {
 const projects = ['first', 'second'].map(id => ({id, name: id, git_url: 'https://example.invalid/repo.git', base_ref: 'main', status: 'pending', created_at: '2026-10-18T00:00:00Z', updated_at: '2026-10-18T00:00:00Z'})) as Project[]
 const finish: Record<string, (p: Project) => void> = {}
 vi.mocked(api.projects.list).mockResolvedValue(projects)
 vi.mocked(api.projects.clone).mockImplementation(id => new Promise(resolve => {finish[id] = resolve}))
 render(<MemoryRouter><ProjectsPage /></MemoryRouter>)
 const buttons = await screen.findAllByRole('button', {name: 'Prepare repository'})
 fireEvent.click(buttons[0]); fireEvent.click(buttons[1])
 await waitFor(() => expect(api.projects.clone).toHaveBeenCalledTimes(2))
 await act(async () => finish.first({...projects[0], status: 'ready'}))
 expect(screen.getAllByRole('link', {name: 'New Worktree'})).toHaveLength(1)
 await act(async () => finish.second({...projects[1], status: 'ready'}))
 expect(screen.getAllByRole('link', {name: 'New Worktree'})).toHaveLength(2)
 expect(screen.queryByRole('button', {name: 'Prepare repository'})).not.toBeInTheDocument()
})
