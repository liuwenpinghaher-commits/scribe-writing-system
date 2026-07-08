import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { AppRail } from '../AppRail'

describe('AppRail 顶栏分组', () => {
  it('章阶段 tab 左对齐,并用分隔线与全局视图区分开', () => {
    render(
      <AppRail
        current={{ slug: 'demo', title: '示例作品' }}
        view={null}
        onView={vi.fn()}
        onOpenLibrary={vi.fn()}
        theme="light"
        onTheme={vi.fn()}
        extra={<div data-testid="chapter-phase-topbar"><button>大纲</button><button>正文</button></div>}
      />,
    )

    const workTabs = screen.getByTestId('topbar-work-tabs')
    const separator = screen.getByTestId('topbar-view-separator')
    const globalViews = screen.getByTestId('topbar-global-views')
    const theme = screen.getByTestId('topbar-theme')

    expect(workTabs.contains(screen.getByTestId('chapter-phase-topbar'))).toBe(true)
    expect(workTabs.className).not.toContain('ml-auto')
    expect(theme.className).toContain('ml-auto')
    expect(workTabs.compareDocumentPosition(separator) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
    expect(separator.compareDocumentPosition(globalViews) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
    expect(globalViews.compareDocumentPosition(theme) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
  })
})
