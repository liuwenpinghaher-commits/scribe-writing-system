import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'

const apiMock = vi.hoisted(() => ({
  settings: vi.fn(), putSetting: vi.fn(), resetSetting: vi.fn(),
  settingsAudit: vi.fn(() => Promise.resolve({ rows: [] })),
  gatewayStatus: vi.fn(() => Promise.resolve({ gateways: [] })),
  gatewayFiles: vi.fn(() => Promise.resolve({ files: [] })),
}))
vi.mock('../../api', () => ({ api: apiMock }))
import { SettingsView } from '../SettingsView'

const ITEMS = [
  { key: 'SCRIBE3_DAILY_CALL_CAP', category: 'llm', type: 'int', label: '每日 LLM 调用日帽',
    value: 500, default: 500, source: 'default', effect: 'hot', danger: true, pending_restart: false },
  { key: 'SCRIBE3_SURREAL_URL', category: 'connection', type: 'str', label: 'SurrealDB 地址',
    value: 'ws://x', default: 'ws://127.0.0.1:8001/rpc', source: 'db', effect: 'restart', danger: false, pending_restart: true },
  { key: 'SCRIBE3_MEMORY_FABRIC_V1', category: 'flags', type: 'bool', label: '记忆织网检索 v1',
    value: false, default: false, source: 'default', effect: 'hot', danger: true, pending_restart: false },
]

beforeEach(() => {
  vi.clearAllMocks()
  apiMock.settings.mockResolvedValue({ settings: ITEMS, categories: ['connection', 'llm', 'craft', 'flags', 'gateway'] })
  apiMock.putSetting.mockResolvedValue({})
  apiMock.resetSetting.mockResolvedValue({})
})

describe('SettingsView', () => {
  it('元数据驱动渲染:分区导航 + 项 + 待重启黄标 + 来源徽章', async () => {
    render(<SettingsView work="demo" />)
    await waitFor(() => expect(screen.getByText('每日 LLM 调用日帽')).toBeTruthy())
    expect(screen.getByText('连接与服务')).toBeTruthy()
    fireEvent.click(screen.getByText('连接与服务'))
    expect(screen.getByText('重启后生效')).toBeTruthy()   // pending_restart 黄标
    expect(screen.getByText('已自定义')).toBeTruthy()      // source=db 徽章
  })

  it('danger 项修改需二次确认后才 PUT', async () => {
    render(<SettingsView work="demo" />)
    await waitFor(() => expect(screen.getByText('灰度开关')).toBeTruthy())
    fireEvent.click(screen.getByText('灰度开关'))
    fireEvent.click(screen.getByRole('switch', { name: '记忆织网检索 v1' }))
    expect(apiMock.putSetting).not.toHaveBeenCalled()      // 先确认
    fireEvent.click(screen.getByRole('button', { name: '确认' }))
    await waitFor(() => expect(apiMock.putSetting).toHaveBeenCalledWith('SCRIBE3_MEMORY_FABRIC_V1', true))
  })

  it('恢复默认按钮走确认后调 resetSetting 并重拉', async () => {
    render(<SettingsView work="demo" />)
    await waitFor(() => expect(screen.getByText('连接与服务')).toBeTruthy())
    fireEvent.click(screen.getByText('连接与服务'))
    fireEvent.click(screen.getByRole('button', { name: '恢复默认:SurrealDB 地址' }))
    fireEvent.click(screen.getByRole('button', { name: '确认' }))
    await waitFor(() => expect(apiMock.resetSetting).toHaveBeenCalledWith('SCRIBE3_SURREAL_URL'))
  })

  it('拉取失败显示错误态与重试', async () => {
    apiMock.settings.mockRejectedValueOnce(new Error('boom'))
    render(<SettingsView work="demo" />)
    await waitFor(() => expect(screen.getByText(/设置加载失败/)).toBeTruthy())
    fireEvent.click(screen.getByText('重试'))
    await waitFor(() => expect(screen.getByText('每日 LLM 调用日帽')).toBeTruthy())
  })
})
