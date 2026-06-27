import { describe, it, expect } from 'vitest'
import { verifyIssues } from './verifyIssues.js'
describe('verifyIssues', () => {
  it('类目数 0–3,再多也封顶 3', () => {
    expect(verifyIssues({ leaks: 0, qcN: 0, causal: 0 })).toBe(0)
    expect(verifyIssues({ leaks: 5, qcN: 99, causal: 200 })).toBe(3)
    expect(verifyIssues({ leaks: 0, qcN: 1, causal: 0 })).toBe(1)
    expect(verifyIssues({ leaks: 2, qcN: 0, causal: 3 })).toBe(2)
  })
})
