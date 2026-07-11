import { describe, it, expect, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { ContextSnapshotProvider, useContextSnapshot, DEFAULT_CAPABILITIES } from './ContextSnapshotContext'

// Task 16-B:前端能力以后端 /capabilities 为准(不靠 localStorage 开服务端能力)。
const apiMock = vi.hoisted(() => ({
  getWork: () => 'demo',
  createContextSession: vi.fn(() => Promise.reject(new Error('降级'))),   // 走本地直通,不影响能力拉取
  fetchCapabilities: vi.fn(),
}))
vi.mock('../api', () => ({ api: apiMock }))

function Probe() {
  const { capabilities } = useContextSnapshot()
  return <div data-testid="caps">{JSON.stringify(capabilities.flags)}</div>
}

describe('ContextSnapshotProvider capabilities', () => {
  it('后端开启的开关下发到前端,未列出的保持默认全关', async () => {
    apiMock.fetchCapabilities.mockResolvedValueOnce({
      flags: { context_inspector_v1: true },   // 只列一个开的
      versions: { retrieval_policy: '1' },
    })
    render(<ContextSnapshotProvider work="demo"><Probe /></ContextSnapshotProvider>)
    await waitFor(() => {
      const flags = JSON.parse(screen.getByTestId('caps').textContent)
      expect(flags.context_inspector_v1).toBe(true)
      expect(flags.memory_fabric_v1).toBe(false)      // 未列出 → 默认全关
      expect(flags.snapshot_v1).toBe(false)
    })
  })

  it('拉取失败时保持默认全关(fail-soft,前端不越权开启)', async () => {
    apiMock.fetchCapabilities.mockRejectedValueOnce(new Error('网络错误'))
    render(<ContextSnapshotProvider work="demo"><Probe /></ContextSnapshotProvider>)
    await waitFor(() => {
      const flags = JSON.parse(screen.getByTestId('caps').textContent)
      expect(flags).toEqual(DEFAULT_CAPABILITIES.flags)
    })
  })
})
