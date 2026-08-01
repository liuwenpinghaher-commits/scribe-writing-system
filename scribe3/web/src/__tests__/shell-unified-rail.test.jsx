import { describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, within } from '@testing-library/react'
import { Rail } from '../shell'

const primary = [
  { key: 'manuscript', label: '手稿', group: 'content' },
  { key: 'review', label: '校验', group: 'inspect' },
]
const secondary = [
  { key: 'chief', label: '主编', scope: 'object' },
  { key: 'versions', label: '存档', scope: 'chapter' },
  { key: 'inbox', label: '收件箱 · 等你决策', scope: 'global', badge: 3 },
]

describe('统一入口竖轨', () => {
  it('在单一 56px 左轨内分隔主入口与底部协作入口', () => {
    render(<Rail side="left" caps={primary} active="manuscript" onActive={() => {}}
      secondaryCaps={secondary} secondaryActive="chief" onSecondaryClick={() => {}} />)

    const rail = screen.getByTestId('unified-entry-rail')
    expect(rail.className).toContain('w-[56px]')
    expect(within(screen.getByTestId('primary-rail-scroll')).getByRole('button', { name: '手稿' })).toBeTruthy()
    expect(within(screen.getByTestId('collaboration-rail')).getByRole('button', { name: '主编' })).toBeTruthy()
    expect(within(screen.getByTestId('collaboration-rail')).getByText('3')).toBeTruthy()
    expect(screen.getAllByTestId('unified-entry-rail')).toHaveLength(1)
  })

  it('协作按钮重复点击仍上报原始 key，由 FourPaneShell 决定折叠或展开', () => {
    const onSecondaryClick = vi.fn()
    render(<Rail side="left" caps={primary} active="manuscript" onActive={() => {}}
      secondaryCaps={secondary} secondaryActive="chief" onSecondaryClick={onSecondaryClick} />)

    fireEvent.click(screen.getByRole('button', { name: '主编' }))
    fireEvent.click(screen.getByRole('button', { name: '主编' }))
    expect(onSecondaryClick.mock.calls).toEqual([['chief'], ['chief']])
  })
})
