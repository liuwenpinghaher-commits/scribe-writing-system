import { describe, expect, it } from 'vitest'
import {
  hasFiveLayerHeadings,
  isStaleDeduction,
  normalizeRoleId,
  softGateIssues,
  softGateSummary,
} from './deduceGate.js'

describe('deduceGate', () => {
  it('normalizeRoleId unifies bare and role: prefix', () => {
    expect(normalizeRoleId('沈砚')).toBe('role:沈砚')
    expect(normalizeRoleId('role:沈砚')).toBe('role:沈砚')
    expect(normalizeRoleId('')).toBe('')
  })

  it('isStaleDeduction compares based_on_truth_rev', () => {
    expect(isStaleDeduction({ prose: 'x', based_on_truth_rev: 1 }, 1)).toBe(false)
    expect(isStaleDeduction({ prose: 'x', based_on_truth_rev: 1 }, 2)).toBe(true)
    expect(isStaleDeduction({ prose: 'x' }, 2)).toBe(true)
    expect(isStaleDeduction({ prose: '' }, 2)).toBe(false)
  })

  it('softGateIssues reports missing and stale', () => {
    const issues = softGateIssues({
      scene_truth: '真相',
      scene_truth_revision: 2,
      involved_characters: ['role:a', 'b'],
      deductions: [
        { character_id: 'a', prose: '旧', based_on_truth_rev: 1 },
      ],
    })
    expect(issues.missing).toEqual(['role:b'])
    expect(issues.stale).toEqual(['role:a'])
    expect(issues.needsAttention).toBe(true)
    expect(softGateSummary(issues)).toMatch(/未演绎|过期/)
  })

  it('hasFiveLayerHeadings requires all five ### titles', () => {
    const full = [
      '### 看到/听到', 'a',
      '### 知道', 'b',
      '### 以为(误读)', 'c',
      '### 做了/说了', 'd',
      '### 没察觉的', 'e',
    ].join('\n')
    expect(hasFiveLayerHeadings(full)).toBe(true)
    expect(hasFiveLayerHeadings('### 看到/听到\nonly')).toBe(false)
  })
})
