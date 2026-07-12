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
  it('渲染 intent 并失焦保存变更字段', async () => {
    render(<BookSection work="demo" />)
    await waitFor(() => expect(screen.getByLabelText('整稿目标字数').value).toBe('100000'))
    fireEvent.change(screen.getByLabelText('整稿目标字数'), { target: { value: '120000' } })
    fireEvent.blur(screen.getByLabelText('整稿目标字数'))
    await waitFor(() => expect(apiMock.putIntent).toHaveBeenCalledWith(
      expect.objectContaining({ total_word_goal: 120000 })))
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
})

describe('AuditSection', () => {
  it('渲染审计行', async () => {
    render(<AuditSection />)
    await waitFor(() => expect(screen.getByText('craft.near_dup_sim')).toBeTruthy())
    expect(screen.getByText(/0\.7/)).toBeTruthy()
  })
})
