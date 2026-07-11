import { describe, it, expect, vi, beforeEach } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { LeftDock } from '../studioDocks'
import { SelectionProvider } from '../selectionContext'

const apiMock = vi.hoisted(() => ({
  promisesLedger: vi.fn(),
  motifs: vi.fn(),
  qc: vi.fn(),
  chapter: vi.fn(),
  motifInstances: vi.fn(),
}))

vi.mock('../api', () => ({ api: apiMock }))

describe('LeftDock 母题台账', () => {
  beforeEach(() => {
    apiMock.promisesLedger.mockResolvedValue({})
    apiMock.motifs.mockResolvedValue([{ id: 11, name: '回声', theme: '重复出现的误认' }])
    apiMock.qc.mockResolvedValue({})
    apiMock.chapter.mockResolvedValue({ focalizer: '小翠' })
    apiMock.motifInstances.mockResolvedValue([{ motif_id: 11, evidence: '铜铃又响了一次' }])
  })

  it('点击母题行会选中对应设定叶,让栏3可渲染母题详情', async () => {
    const onSelect = vi.fn()
    render(
      <SelectionProvider>
        <LeftDock tree={null} selId={null} expanded={new Set()} onSelect={onSelect} seq={3} />
      </SelectionProvider>,
    )

    fireEvent.click(screen.getByRole('button', { name: '母题' }))
    await waitFor(() => expect(screen.getByRole('button', { name: /回声/ })).toBeTruthy())

    fireEvent.click(screen.getByRole('button', { name: /回声/ }))

    expect(onSelect).toHaveBeenCalledWith({ id: 'motif:11', type: 'motif', ref: 11, label: '回声' })
  })
})
