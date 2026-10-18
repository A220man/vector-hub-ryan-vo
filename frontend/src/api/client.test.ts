/** Tests for the API client. */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { api } from './client'

describe('API Client', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    globalThis.fetch = vi.fn()
  })

  it('makes GET request with correct URL', async () => {
    const mockResponse = [{ id: '1', name: 'Test' }]
    vi.mocked(fetch).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockResponse),
      status: 200,
    } as Response)

    const result = await api.projects.list()

    expect(fetch).toHaveBeenCalledWith(
      '/api/v1/projects',
      expect.objectContaining({
        credentials: 'include',
      })
    )
    expect(new Headers(vi.mocked(fetch).mock.calls[0][1]?.headers).get('Content-Type')).toBe('application/json')
    expect(result).toEqual(mockResponse)
  })

  it('throws on non-ok response', async () => {
    vi.mocked(fetch).mockResolvedValue({
      ok: false,
      status: 404,
      json: () => Promise.resolve({ detail: 'Not found' }),
    } as Response)

    await expect(api.projects.list()).rejects.toThrow('Not found')
  })

  it('posts JSON for create operations', async () => {
    const mockProject = { id: '1', name: 'New', git_url: 'url', base_ref: 'main', status: 'pending', created_at: '', updated_at: '' }
    vi.mocked(fetch).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockProject),
      status: 201,
    } as Response)

    vi.mocked(fetch).mockResolvedValueOnce(new Response(JSON.stringify({ csrf_token: 'test-session-token' })))
    const result = await api.projects.create({ name: 'New', git_url: 'url' })

    expect(fetch).toHaveBeenCalledWith(
      '/api/v1/projects',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ name: 'New', git_url: 'url' }),
      })
    )
    expect(result).toEqual(mockProject)
  })

  it('handles 204 no content', async () => {
    vi.mocked(fetch).mockResolvedValue({
      ok: true,
      status: 204,
    } as Response)

    vi.mocked(fetch).mockResolvedValueOnce(new Response(JSON.stringify({ csrf_token: 'test-session-token' })))
    const result = await api.projects.delete('1')
    expect(result).toBeUndefined()
  })
})