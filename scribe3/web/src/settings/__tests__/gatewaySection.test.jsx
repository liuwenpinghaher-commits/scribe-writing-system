import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'

const apiMock = vi.hoisted(() => ({
  gatewayStatus: vi.fn(), gatewayFiles: vi.fn(), putGatewayFile: vi.fn(), gatewayRestart: vi.fn(),
  putSetting: vi.fn(), resetSetting: vi.fn(),
}))
vi.mock('../../api', () => ({ api: apiMock }))
import { GatewaySection } from '../GatewaySection'

beforeEach(() => {
  vi.clearAllMocks()
  apiMock.gatewayStatus.mockResolvedValue({ gateways: [
    { name: 'responses', api: 'http://127.0.0.1:8643/v1', profile: 'scribe3', online: true },
    { name: 'runs', api: 'http://127.0.0.1:8644/v1', profile: 'scribe3_write', online: false },
  ] })
  apiMock.gatewayFiles.mockResolvedValue({ files: [
    { id: 'scribe3/SOUL.md', path: '/x/SOUL.md', exists: true, content: '我是主编', sha256: 'h1' },
  ] })
  apiMock.putGatewayFile.mockResolvedValue({ sha256: 'h2' })
  apiMock.gatewayRestart.mockResolvedValue({ online: true, message: '已重启' })
})

describe('GatewaySection', () => {
  it('渲染状态灯与文件;保存走确认并带 base_sha256', async () => {
    render(<GatewaySection items={[]} />)
    await waitFor(() => expect(screen.getByText('scribe3')).toBeTruthy())
    expect(screen.getByText('在线')).toBeTruthy()
    expect(screen.getByText('离线')).toBeTruthy()
    fireEvent.click(screen.getByText('scribe3/SOUL.md'))
    const ta = await screen.findByRole('textbox')
    fireEvent.change(ta, { target: { value: '我是新主编' } })
    fireEvent.click(screen.getByRole('button', { name: '保存' }))
    fireEvent.click(screen.getByRole('button', { name: '确认' }))
    await waitFor(() => expect(apiMock.putGatewayFile).toHaveBeenCalledWith('scribe3/SOUL.md', '我是新主编', 'h1'))
  })

  it('保存 409 冲突提示重新加载', async () => {
    apiMock.putGatewayFile.mockRejectedValueOnce(Object.assign(new Error('conflict'), { status: 409, body: { detail: '文件已被外部修改,请重新加载后再编辑' } }))
    render(<GatewaySection items={[]} />)
    await waitFor(() => expect(screen.getByText('scribe3/SOUL.md')).toBeTruthy())
    fireEvent.click(screen.getByText('scribe3/SOUL.md'))
    const ta = await screen.findByRole('textbox')
    fireEvent.change(ta, { target: { value: 'x' } })
    fireEvent.click(screen.getByRole('button', { name: '保存' }))
    fireEvent.click(screen.getByRole('button', { name: '确认' }))
    await waitFor(() => expect(screen.getByText(/外部修改|重新加载/)).toBeTruthy())
  })

  it('重启走确认;结果如实显示(含失败)', async () => {
    apiMock.gatewayRestart.mockResolvedValueOnce({ online: false, message: '重启后 30s 内未探活成功,请查看日志' })
    render(<GatewaySection items={[]} />)
    await waitFor(() => expect(screen.getByText('scribe3')).toBeTruthy())
    fireEvent.click(screen.getByRole('button', { name: '重启 scribe3' }))
    fireEvent.click(screen.getByRole('button', { name: '确认' }))
    await waitFor(() => expect(apiMock.gatewayRestart).toHaveBeenCalledWith('scribe3'))
    await waitFor(() => expect(screen.getByText(/未探活成功/)).toBeTruthy())
  })
})
