import { describe, expect, it, vi } from 'vitest'
import { entryPatch } from '../../context/contextSnapshot'
import { isSynopsisHall } from '../entrySelection'
import { landSynopsisHall, shouldExitHubForSynopsis } from '../synopsisHall'

describe('isSynopsisHall', () => {
  it('手稿空选和 manuscript_root 是门厅', () => {
    expect(isSynopsisHall('manuscript', { mode: 'node', node: null })).toBe(true)
    expect(isSynopsisHall('manuscript', { mode: 'node', node: { type: 'manuscript_root' } })).toBe(true)
  })

  it('设定库/伏笔空选不是门厅', () => {
    expect(isSynopsisHall('codex', { mode: 'node', node: null })).toBe(false)
    expect(isSynopsisHall('promise', { mode: 'node', node: null })).toBe(false)
    expect(isSynopsisHall(undefined, { mode: 'node', node: null })).toBe(false)
  })

  it('横切 view 不是门厅', () => {
    expect(isSynopsisHall('manuscript', { mode: 'view', viewKey: 'journey' })).toBe(false)
  })
})

describe('landSynopsisHall', () => {
  it('三步：setTab manuscript + 空 sel + entryPatch，不走 planEntryChange', () => {
    const setTab = vi.fn()
    const onSelectNode = vi.fn()
    const navigate = vi.fn()
    const expandDirectory = vi.fn()
    landSynopsisHall({
      setTab,
      onSelectNode,
      navigate,
      directoryCollapsed: true,
      expandDirectory,
    })
    expect(setTab).toHaveBeenCalledWith('manuscript')
    expect(onSelectNode).toHaveBeenCalledWith(null)
    expect(navigate).toHaveBeenCalledWith(entryPatch('manuscript'))
    expect(expandDirectory).toHaveBeenCalled()
  })
})

describe('shouldExitHubForSynopsis', () => {
  it('系统中心/设置要先退 hub', () => {
    expect(shouldExitHubForSynopsis({ mode: 'view', viewKey: 'system' })).toBe(true)
    expect(shouldExitHubForSynopsis({ mode: 'view', viewKey: 'settings' })).toBe(true)
    expect(shouldExitHubForSynopsis({ mode: 'view', viewKey: 'journey' })).toBe(false)
    expect(shouldExitHubForSynopsis({ mode: 'node', node: null })).toBe(false)
  })
})
