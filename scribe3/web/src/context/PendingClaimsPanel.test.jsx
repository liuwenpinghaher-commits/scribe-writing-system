import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'

const ctx = vi.hoisted(() => ({
  value: {
    snapshot: null,
    restoring: false,
    error: null,
    capabilities: {
      flags: {
        snapshot_v1: true,
        editorial_thread_v1: false,
        memory_fabric_v1: true,
        context_inspector_v1: true,
        assembler_v1: true,
      },
      versions: {},
    },
  },
}))
vi.mock('./ContextSnapshotContext', () => ({
  useContextSnapshot: () => ctx.value,
}))

const apiMock = vi.hoisted(() => ({
  listPendingClaims: vi.fn(),
  resolvePendingClaim: vi.fn(),
}))
vi.mock('../api', () => ({ api: apiMock }))
vi.mock('../ui/Toast.jsx', () => ({ showToast: vi.fn() }))

import { PendingClaimsPanel } from './PendingClaimsPanel'
import { showToast } from '../ui/Toast.jsx'

beforeEach(() => {
  vi.clearAllMocks()
  ctx.value.capabilities.flags.memory_fabric_v1 = true
  apiMock.listPendingClaims.mockResolvedValue({
    claims: [{
      id: 'claim-1',
      text: '己真实身份是细作',
      entity: 'role:己',
      attribute: '身份',
      value: '细作',
    }],
  })
  apiMock.resolvePendingClaim.mockResolvedValue({
    status: 'approved',
    fact_id: 'fact:x',
  })
})

describe('PendingClaimsPanel', () => {
  it('fabric 开时列出待审并调用 shipped list API', async () => {
    render(<PendingClaimsPanel />)
    await waitFor(() => expect(apiMock.listPendingClaims).toHaveBeenCalledWith('pending'))
    expect(screen.getByTestId('pending-claims-panel')).toBeTruthy()
    expect(screen.getByTestId('pending-claims-count').textContent).toBe('1')
    expect(screen.getByText('己真实身份是细作')).toBeTruthy()
  })

  it('批准走 resolvePendingClaim(approve)', async () => {
    render(<PendingClaimsPanel />)
    await waitFor(() => screen.getByTestId('pending-claim-approve'))
    fireEvent.click(screen.getByTestId('pending-claim-approve'))
    await waitFor(() => expect(apiMock.resolvePendingClaim).toHaveBeenCalledWith(
      'claim-1',
      expect.objectContaining({ decision: 'approve' }),
    ))
    expect(showToast).toHaveBeenCalled()
  })

  it('拒绝走 resolvePendingClaim(reject)', async () => {
    apiMock.resolvePendingClaim.mockResolvedValueOnce({ status: 'rejected' })
    render(<PendingClaimsPanel />)
    await waitFor(() => screen.getByTestId('pending-claim-reject'))
    fireEvent.click(screen.getByTestId('pending-claim-reject'))
    await waitFor(() => expect(apiMock.resolvePendingClaim).toHaveBeenCalledWith(
      'claim-1',
      expect.objectContaining({ decision: 'reject' }),
    ))
  })

  it('fabric 关时不渲染', () => {
    ctx.value.capabilities.flags.memory_fabric_v1 = false
    render(<PendingClaimsPanel />)
    expect(screen.queryByTestId('pending-claims-panel')).toBeNull()
    expect(apiMock.listPendingClaims).not.toHaveBeenCalled()
  })
})
