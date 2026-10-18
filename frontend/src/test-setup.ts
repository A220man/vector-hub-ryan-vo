/** Test setup for vitest. */
import '@testing-library/jest-dom'
import { vi } from 'vitest'

// Reset mocks before each test
beforeEach(() => {
  vi.clearAllMocks()
})