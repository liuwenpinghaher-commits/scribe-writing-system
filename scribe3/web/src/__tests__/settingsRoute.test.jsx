import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { AppRail } from '../AppRail'

describe('设置中心入口', () => {
  it('顶栏齿轮触发 onView(settings),当前视图时高亮', () => {
    const onView = vi.fn()
    const { rerender } = render(<AppRail current={{ slug: 'b', title: '书' }} view={null} onView={onView}
      onOpenLibrary={() => {}} theme="light" onTheme={() => {}} />)
    fireEvent.click(screen.getByRole('button', { name: '设置' }))
    expect(onView).toHaveBeenCalledWith('settings')
    rerender(<AppRail current={{ slug: 'b', title: '书' }} view="settings" onView={onView}
      onOpenLibrary={() => {}} theme="light" onTheme={() => {}} />)
    expect(screen.getByRole('button', { name: '设置' }).getAttribute('aria-current')).toBe('page')
  })
})
