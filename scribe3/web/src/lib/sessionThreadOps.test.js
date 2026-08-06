import { describe, expect, it } from 'vitest'
import { pickLatestActiveThread } from './sessionThreadOps.js'

describe('pickLatestActiveThread', () => {
  it('picks active with latest updated_at, not earliest created', () => {
    const threads = [
      { thread_id: 'old', status: 'active', created_at: '2020-01-01T00:00:00Z', updated_at: '2020-01-01T00:00:00Z' },
      { thread_id: 'mid', status: 'active', created_at: '2021-01-01T00:00:00Z', updated_at: '2024-06-01T00:00:00Z' },
      { thread_id: 'new', status: 'active', created_at: '2024-01-01T00:00:00Z', updated_at: '2023-01-01T00:00:00Z' },
      { thread_id: 'arch', status: 'archived', created_at: '2025-01-01T00:00:00Z', updated_at: '2025-06-01T00:00:00Z' },
    ]
    const next = pickLatestActiveThread(threads, 'current')
    expect(next.thread_id).toBe('mid')
  })

  it('excludes the archived/current id', () => {
    const threads = [
      { thread_id: 'a', status: 'active', updated_at: '2024-01-02T00:00:00Z' },
      { thread_id: 'b', status: 'active', updated_at: '2024-01-03T00:00:00Z' },
    ]
    expect(pickLatestActiveThread(threads, 'b').thread_id).toBe('a')
  })

  it('returns null when no other active', () => {
    expect(pickLatestActiveThread(
      [{ thread_id: 'only', status: 'active', updated_at: '2024-01-01T00:00:00Z' }],
      'only',
    )).toBe(null)
  })
})
