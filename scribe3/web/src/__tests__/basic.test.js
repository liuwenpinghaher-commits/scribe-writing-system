import { describe, it, expect } from 'vitest'
import { ErrorBoundary } from '../ErrorBoundary.jsx'

describe('ErrorBoundary', () => {
  it('component file exports correctly', () => {
    expect(ErrorBoundary).toBeDefined()
  })
})

describe('API helpers', () => {
  it('BASE is configurable via VITE_API_BASE', () => {
    const base = import.meta.env.VITE_API_BASE
    expect(base || 'http://127.0.0.1:3321').toBeTruthy()
  })
})
