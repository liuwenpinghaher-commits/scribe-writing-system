import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'

const apiMock = vi.hoisted(() => ({
  intent: vi.fn(() => Promise.resolve({ total_word_goal: 100000, red_lines: '不写穿越' })),
  putIntent: vi.fn(() => Promise.resolve({})),
  settingsAudit: vi.fn(() => Promise.resolve({ rows: [
    { ts: '2026-07-12T10:00:00', key: 'craft.near_dup_sim', old: '0.7', new: '0.8' },
  ] })),
}))
vi.mock('../../api', () => ({ api: apiMock }))
import { BookSection } from '../BookSection'
import { PrefsSection } from '../PrefsSection'
import { AuditSection } from '../AuditSection'

beforeEach(() => {
  vi.clearAllMocks()
  apiMock.intent.mockResolvedValue({ total_word_goal: 100000, red_lines: '不写穿越' })
  apiMock.putIntent.mockResolvedValue({})
  apiMock.settingsAudit.mockResolvedValue({ rows: [
    { ts: '2026-07-12T10:00:00', key: 'craft.near_dup_sim', old: '0.7', new: '0.8' },
  ] })
})

describe('BookSection', () => {
  it('数字配额失焦可 putIntent;叙事字段只读走主编种子', async () => {
    const seeds = []
    window.addEventListener('s3-chief-seed', (e) => seeds.push(e.detail))
    render(<BookSection work="demo" />)
    await waitFor(() => expect(screen.getByLabelText('整稿目标字数').value).toBe('100000'))
    fireEvent.change(screen.getByLabelText('整稿目标字数'), { target: { value: '120000' } })
    fireEvent.blur(screen.getByLabelText('整稿目标字数'))
    await waitFor(() => expect(apiMock.putIntent).toHaveBeenCalledWith(
      expect.objectContaining({ total_word_goal: 120000 })))

    apiMock.putIntent.mockClear()
    fireEvent.click(screen.getByRole('button', { name: /让主编写入红线/ }))
    expect(seeds.some((s) => /红线|red_lines/.test(s))).toBe(true)
    expect(apiMock.putIntent).not.toHaveBeenCalled()
  })

  it('数字字段清空失焦:不发 PUT,恢复旧值并提示不支持清空', async () => {
    render(<BookSection work="demo" />)
    await waitFor(() => expect(screen.getByLabelText('整稿目标字数').value).toBe('100000'))
    fireEvent.change(screen.getByLabelText('整稿目标字数'), { target: { value: '' } })
    fireEvent.blur(screen.getByLabelText('整稿目标字数'))
    expect(apiMock.putIntent).not.toHaveBeenCalled()
    expect(screen.getByLabelText('整稿目标字数').value).toBe('100000')
    expect(screen.getByRole('alert').textContent).toMatch(/不支持清空/)
  })
})

describe('PrefsSection', () => {
  beforeEach(() => localStorage.clear())
  it('护栏默认开;切换写 localStorage 并派发事件', () => {
    const seen = []
    window.addEventListener('s3-pref-changed', (e) => seen.push(e.detail?.key), { once: true })
    render(<PrefsSection work="demo" />)
    const sw = screen.getByRole('switch', { name: '写作护栏默认开启' })
    expect(sw.getAttribute('aria-checked')).toBe('true')
    fireEvent.click(sw)
    expect(localStorage.getItem('scribe3:guardOn')).toBe('0')
    expect(seen).toContain('scribe3:guardOn')
  })
  it('脉搏静音清单可逐条解除', () => {
    localStorage.setItem('s3.pulse.mute.demo.promise', '1')
    render(<PrefsSection work="demo" />)
    fireEvent.click(screen.getByRole('button', { name: /解除静音/ }))
    expect(localStorage.getItem('s3.pulse.mute.demo.promise')).toBeNull()
  })
  it('guardOn/serif 项带「切书或刷新后生效」提示(消费点是 useState 初始化读取,同书内不热生效)', () => {
    render(<PrefsSection work="demo" />)
    expect(screen.getAllByText(/切书或刷新后生效/).length).toBe(2)
  })
})

describe('AuditSection', () => {
  it('渲染审计行', async () => {
    render(<AuditSection />)
    await waitFor(() => expect(screen.getByText('craft.near_dup_sim')).toBeTruthy())
    expect(screen.getByText(/0\.7/)).toBeTruthy()
  })

  it('「加载更多」失败后重试:重放失败那次的 offset+append,不回退成首页整替', async () => {
    const page = (n, off) => Array.from({ length: n }, (_, i) => (
      { ts: `2026-07-12T10:${String(i).padStart(2, '0')}:00`, key: `k.${off + i}`, old: 'a', new: 'b' }))
    apiMock.settingsAudit
      .mockResolvedValueOnce({ rows: page(50, 0) })                       // 首页整页 → 显示加载更多
      .mockRejectedValueOnce(new Error('network'))                        // 翻页失败
      .mockResolvedValueOnce({ rows: [{ ts: '2026-07-12T11:00:00', key: 'k.retry', old: 'x', new: 'y' }] })
    render(<AuditSection />)
    await waitFor(() => expect(screen.getByText('k.0')).toBeTruthy())
    fireEvent.click(screen.getByRole('button', { name: /加载更多/ }))
    await waitFor(() => expect(screen.getByRole('alert')).toBeTruthy())
    fireEvent.click(screen.getByRole('button', { name: '重试' }))
    await waitFor(() => expect(screen.getByText('k.retry')).toBeTruthy())
    expect(apiMock.settingsAudit).toHaveBeenLastCalledWith(50)   // 重放失败请求的 offset
    expect(screen.getByText('k.0')).toBeTruthy()                 // append 语义:首页行仍在
  })
})
