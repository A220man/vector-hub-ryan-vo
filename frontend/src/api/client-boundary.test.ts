import { afterEach, describe, expect, it, vi } from 'vitest'
import { api } from './client'

afterEach(() => vi.unstubAllGlobals())
const reply = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })
describe('authenticated API transport', () => {
  it('gets current CSRF token with cookies before sending a mutation', async () => {
    const fetcher = vi.fn().mockResolvedValueOnce(reply({ csrf_token: 'session-bound-token' })).mockResolvedValueOnce(reply({ id: 'p1' }))
    vi.stubGlobal('fetch', fetcher)
    await api.projects.create({ name: 'Example', git_url: 'https://example.com/project.git', base_ref: 'main' })
    expect(fetcher).toHaveBeenCalledTimes(2)
    expect(fetcher.mock.calls[0]).toEqual(['/api/v1/auth/csrf', { credentials: 'include' }])
    const [url, request] = fetcher.mock.calls[1]
    expect(url).toBe('/api/v1/projects')
    expect(request.credentials).toBe('include')
    expect(new Headers(request.headers).get('X-CSRF-Token')).toBe('session-bound-token')
    expect(JSON.parse(request.body).name).toBe('Example')
  })
  it('does not send a write when the session has expired', async () => {
    const fetcher = vi.fn().mockResolvedValue(reply({ detail: 'expired' }, 401))
    vi.stubGlobal('fetch', fetcher)
    await expect(api.agents.start('r1')).rejects.toThrow()
    expect(fetcher.mock.calls.map(c => c[0])).toEqual(['/api/v1/auth/csrf'])
  })
  it('rejects an empty token before sending a write', async () => {
    const fetcher = vi.fn().mockResolvedValue(reply({ csrf_token: '' }))
    vi.stubGlobal('fetch', fetcher)
    await expect(api.projects.delete('p1')).rejects.toThrow('CSRF token')
    expect(fetcher).toHaveBeenCalledTimes(1)
  })
  it('refreshes the token between sessions instead of caching it', async () => {
    const fetcher = vi.fn().mockResolvedValueOnce(reply({ csrf_token: 'first' })).mockResolvedValueOnce(reply({})).mockResolvedValueOnce(reply({ csrf_token: 'second' })).mockResolvedValueOnce(reply({}))
    vi.stubGlobal('fetch', fetcher)
    await api.agents.start('r1'); await api.agents.stop('r1')
    expect(fetcher).toHaveBeenCalledTimes(4)
    expect(new Headers(fetcher.mock.calls[1][1].headers).get('X-CSRF-Token')).toBe('first')
    expect(new Headers(fetcher.mock.calls[3][1].headers).get('X-CSRF-Token')).toBe('second')
  })
  it('does not require a session for demo login or add probes to reads', async () => {
    const fetcher = vi.fn().mockImplementation(async () => reply({}))
    vi.stubGlobal('fetch', fetcher)
    await api.auth.demoLogin(); await api.auth.me()
    expect(fetcher.mock.calls.map(c => c[0])).toEqual(['/api/v1/auth/demo-login', '/api/v1/auth/me'])
  })
})
