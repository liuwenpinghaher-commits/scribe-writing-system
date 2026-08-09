import { describe, it, expect } from 'vitest'
import {
  pickLatestActiveThread,
  partitionThreadList,
  shouldArchivePreviousOnNew,
  sortThreadsByRecency,
} from '../sessionThreadOps.js'

describe('sessionThreadOps', () => {
  it('pickLatestActiveThread 按 updated_at 取最新且排除 id', () => {
    const next = pickLatestActiveThread([
      { thread_id: 'a', status: 'active', updated_at: '2024-01-01' },
      { thread_id: 'b', status: 'active', updated_at: '2024-06-01' },
      { thread_id: 'c', status: 'archived', updated_at: '2025-01-01' },
    ], 'a')
    expect(next.thread_id).toBe('b')
  })

  it('shouldArchivePreviousOnNew 仅当新旧不同', () => {
    expect(shouldArchivePreviousOnNew('t1', 't2')).toBe(true)
    expect(shouldArchivePreviousOnNew('t1', 't1')).toBe(false)
    expect(shouldArchivePreviousOnNew(null, 't2')).toBe(false)
  })

  it('partitionThreadList 当前置顶、其余 active/归档分离', () => {
    const { current, otherActive, archived } = partitionThreadList([
      { thread_id: 't1', title: '当前', status: 'active', updated_at: '2024-01-01' },
      { thread_id: 't2', title: '旧活', status: 'active', updated_at: '2024-06-01' },
      { thread_id: 't3', title: '档', status: 'archived', updated_at: '2025-01-01' },
    ], 't1')
    expect(current.thread_id).toBe('t1')
    expect(otherActive.map((t) => t.thread_id)).toEqual(['t2'])
    expect(archived.map((t) => t.thread_id)).toEqual(['t3'])
  })

  it('sortThreadsByRecency 新在前', () => {
    const s = sortThreadsByRecency([
      { thread_id: 'a', updated_at: '2020-01-01' },
      { thread_id: 'b', updated_at: '2024-01-01' },
    ])
    expect(s[0].thread_id).toBe('b')
  })
})
