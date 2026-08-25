import { describe, expect, it, vi } from 'vitest'

vi.mock('../MaterialImport', () => ({ MaterialImport: () => null }))
vi.mock('../MaterialNetwork', () => ({ MaterialNetwork: () => null }))

import {
  MaterialDetail as BarrelDetail,
  MaterialList as BarrelList,
  MaterialNew as BarrelNew,
  MATERIAL_KINDS,
} from '../Materials'
import { MaterialList } from '../MaterialList'
import { MaterialDetail } from '../MaterialDetail'
import { MaterialNew } from '../MaterialNew'

describe('素材工作台模块边界', () => {
  it('list/detail/new 是独立模块，barrel 只再导出同一引用', () => {
    expect(MaterialList).toBe(BarrelList)
    expect(MaterialDetail).toBe(BarrelDetail)
    expect(MaterialNew).toBe(BarrelNew)
    expect(MATERIAL_KINDS.some((k) => k.key === 'note')).toBe(true)
  })
})
