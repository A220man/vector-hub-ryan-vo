import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor, cleanup } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { useState } from 'react'
import { AuthProvider, useAuth } from './AuthContext'
import { api } from '../api/client'
vi.mock('../api/client', () => ({ api: { auth: { me: vi.fn(), login: vi.fn(), demoLogin: vi.fn(), logout: vi.fn() } } }))
function Entry() {
  const { login, user } = useAuth(); const [error, setError] = useState('')
  return <><button onClick={() => login().catch(e => setError(e.message))}>Enter</button><span>{user?.name}</span><p role="alert">{error}</p></>
}
const assign = vi.fn()
beforeEach(() => {
  vi.clearAllMocks(); vi.stubEnv('VITE_DEMO_MODE', 'false'); vi.stubGlobal('location', { assign })
  vi.mocked(api.auth.me).mockRejectedValue(new Error('unauthorized'))
})
afterEach(() => { cleanup(); vi.unstubAllEnvs(); vi.unstubAllGlobals() })
describe('browser login selection', () => {
  it('starts OIDC with server-created browser transaction and follows authorization URL', async () => {
    vi.mocked(api.auth.login).mockResolvedValue({ auth_url: 'https://issuer.example/authorize?state=one', state: 'one' })
    render(<AuthProvider><Entry /></AuthProvider>); await userEvent.click(screen.getByText('Enter'))
    await waitFor(() => expect(assign).toHaveBeenCalledWith('https://issuer.example/authorize?state=one'))
    expect(api.auth.demoLogin).not.toHaveBeenCalled()
  })
  it('surfaces failed login initiation without falling back to demo', async () => {
    vi.mocked(api.auth.login).mockRejectedValue(new Error('Issuer unavailable'))
    render(<AuthProvider><Entry /></AuthProvider>); await userEvent.click(screen.getByText('Enter'))
    await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent('Issuer unavailable'))
    expect(assign).not.toHaveBeenCalled(); expect(api.auth.demoLogin).not.toHaveBeenCalled()
  })
  it('rejects a non-HTTP authorization URL', async () => {
    vi.mocked(api.auth.login).mockResolvedValue({ auth_url: 'javascript:alert(1)', state: 'one' })
    render(<AuthProvider><Entry /></AuthProvider>); await userEvent.click(screen.getByText('Enter'))
    await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent('Invalid sign-in address'))
    expect(assign).not.toHaveBeenCalled()
  })
  it('uses demo only when explicitly configured and reloads the session', async () => {
    vi.stubEnv('VITE_DEMO_MODE', 'true')
    vi.mocked(api.auth.demoLogin).mockResolvedValue({ message: 'ok' })
    vi.mocked(api.auth.me).mockRejectedValueOnce(new Error('unauthorized')).mockResolvedValue({ sub: 'demo', name: 'Demo', email: null, roles: ['admin'] })
    render(<AuthProvider><Entry /></AuthProvider>); await userEvent.click(screen.getByText('Enter'))
    await waitFor(() => expect(screen.getByText('Demo')).toBeInTheDocument())
    expect(api.auth.login).not.toHaveBeenCalled(); expect(assign).not.toHaveBeenCalled()
  })
})
