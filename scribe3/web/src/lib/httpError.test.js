import { describe, expect, it } from 'vitest'
import { guideMissingLine, httpErrorMessage } from './httpError.js'

describe('httpErrorMessage', () => {
  it('reads message from unified detail object', () => {
    expect(httpErrorMessage({ body: { detail: { code: 'stage_gone', message: '这一站拆了' } } })).toBe('这一站拆了')
  })
  it('keeps string detail', () => {
    expect(httpErrorMessage({ body: { detail: '接受失败' } }, 'x')).toBe('接受失败')
  })
})

describe('guideMissingLine', () => {
  it('renders empty recall for the author', () => {
    expect(guideMissingLine({ payload: { name: 'codex_recall_empty' } })).toBe('本章没对上设定条目')
    expect(guideMissingLine({ summary: '别的' })).toBe('')
  })
  it('does not fire when recall hit', () => {
    expect(guideMissingLine({ payload: { name: 'ok' }, summary: '有设定' })).toBe('')
  })
})
