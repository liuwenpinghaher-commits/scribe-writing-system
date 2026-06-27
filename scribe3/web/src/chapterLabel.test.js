import { describe, it, expect } from 'vitest'
import { chapterLabel } from './chapterLabel.js'
describe('chapterLabel', () => {
  it('title 与 第N章 同义 → 只显示一次', () => {
    expect(chapterLabel(1, '第1章')).toBe('第1章')
    expect(chapterLabel(1, '')).toBe('第1章')
    expect(chapterLabel(1, null)).toBe('第1章')
    expect(chapterLabel(1, '  第1章  ')).toBe('第1章')
  })
  it('真实小标题 → 第N章 · 小标题', () => {
    expect(chapterLabel(2, '谷口')).toBe('第2章 · 谷口')
  })
})
