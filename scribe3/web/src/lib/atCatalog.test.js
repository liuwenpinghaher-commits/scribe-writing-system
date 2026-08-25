import { describe, expect, it } from 'vitest'
import {
  AT_DOMAIN_LABEL,
  buildAtCatalog,
  detectAtQuery,
  filterAtCatalog,
  insertAtMention,
} from './atCatalog.js'
import {
  AT_DOMAIN_LABEL as ClipLabel,
  buildAtCatalog as clipBuild,
  detectAtQuery as clipDetect,
} from './sessionClip.js'

describe('@ 目录独立于会话剪藏', () => {
  it('atCatalog 导出检测与目录，sessionClip 只再导出同一引用', () => {
    expect(detectAtQuery).toBe(clipDetect)
    expect(buildAtCatalog).toBe(clipBuild)
    expect(AT_DOMAIN_LABEL).toBe(ClipLabel)
    expect(detectAtQuery('看 @霜', 4)?.query).toBe('霜')
    const cat = buildAtCatalog({
      materials: [{ id: '1', title: '霜白', kind: 'snippet' }],
    })
    expect(filterAtCatalog(cat, '霜')[0].domain).toBe('material')
    const out = insertAtMention('结合 @霜', 5, cat[0])
    expect(out.token).toMatch(/material:1/)
  })
})
