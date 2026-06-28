import { describe, it, expect, beforeEach } from 'vitest'
import {
  issueLabel, issueKey, expandToSentence,
  ignoreIssue, ignoredKeys, filterIgnored,
} from './guardIssues.js'

describe('issueLabel', () => {
  it('已知类别给中文标签', () => {
    expect(issueLabel('repetition')).toBe('复读')
    expect(issueLabel('leak')).toBe('穿帮泄露')
  })
  it('未知类别兜底', () => {
    expect(issueLabel('unknown')).toBe('问题')
  })
})

describe('expandToSentence', () => {
  const prose = '他端着药碗。镇煞钉泛着冷光,他知道回不去了。然后呢。'
  it('把短语 range 扩到所属句边界', () => {
    const idx = prose.indexOf('镇煞钉')
    const [s, e] = expandToSentence(prose, [idx, idx + 3])
    expect(prose.slice(s, e)).toBe('镇煞钉泛着冷光,他知道回不去了。')
  })
  it('首句无前导标点也能扩', () => {
    const [s, e] = expandToSentence(prose, [0, 1])
    expect(prose.slice(s, e)).toBe('他端着药碗。')
  })
  it('非法 range 原样返回', () => {
    expect(expandToSentence(prose, null)).toBe(null)
  })
})

describe('忽略持久化', () => {
  beforeEach(() => localStorage.clear())
  const prose = '正文内容甲乙丙。'
  const issue = { type: 'repetition', text: '甲乙丙' }

  it('ignoreIssue 后 ignoredKeys 含该 key', () => {
    ignoreIssue(prose, issue)
    expect(ignoredKeys(prose).has(issueKey(issue))).toBe(true)
  })

  it('filterIgnored 过滤掉已忽略的 issue', () => {
    ignoreIssue(prose, issue)
    const issues = [issue, { type: 'leak', text: '别的' }]
    const left = filterIgnored(prose, issues)
    expect(left).toHaveLength(1)
    expect(left[0].type).toBe('leak')
  })

  it('prose 变化后忽略失效(绑定到 prose 指纹)', () => {
    ignoreIssue(prose, issue)
    expect(ignoredKeys('完全不同的另一段正文').has(issueKey(issue))).toBe(false)
  })
})
