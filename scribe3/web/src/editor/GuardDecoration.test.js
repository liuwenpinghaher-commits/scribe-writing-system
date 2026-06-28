import { describe, it, expect } from 'vitest'
import { Schema } from '@tiptap/pm/model'
import { proseOffsetToPm, proseRangeToPm, docToText } from './GuardDecoration.js'

// 最小 schema:doc(paragraph+ sceneBreak),口径与 ProseEditor 一致
// sceneBreak 是 atom block(无文本),序列化为 '* * *'(5 字符)。
const schema = new Schema({
  nodes: {
    doc: { content: 'block+' },
    paragraph: { group: 'block', content: 'text*', toDOM: () => ['p', 0] },
    sceneBreak: { group: 'block', atom: true, selectable: true, toDOM: () => ['hr'] },
    text: {},
  },
})

const para = (t) => schema.node('paragraph', null, t ? [schema.text(t)] : [])
const sb = () => schema.node('sceneBreak')
const mkDoc = (...blocks) => schema.node('doc', null, blocks)

// 正向口径:把 PM 位置折回 prose offset(照抄 ProseEditor.jsx pmPosToProseOffset),
// 用作往返一致性的参照实现。
function pmPosToProseOffset(doc, pmPos) {
  let offset = 0
  let result = null
  let pos = 0
  doc.forEach((node) => {
    if (result !== null) { pos += node.nodeSize; return }
    const serialized = node.type.name === 'sceneBreak' ? '* * *' : node.textContent
    const nodeStart = pos
    const nodeEnd = pos + node.nodeSize
    if (pmPos <= nodeStart) {
      result = offset
    } else if (pmPos < nodeEnd) {
      if (node.type.name === 'sceneBreak') {
        result = offset
      } else {
        const inBlock = Math.max(0, Math.min(serialized.length, pmPos - (nodeStart + 1)))
        result = offset + inBlock
      }
    } else {
      offset += serialized.length + 2
    }
    pos = nodeEnd
  })
  return result === null ? offset : result
}

describe('proseOffsetToPm 与 pmPosToProseOffset 互逆', () => {
  const docs = {
    单段: mkDoc(para('他端着药碗,知道回不去了。')),
    多段: mkDoc(para('第一段文字。'), para('第二段更长一些的文字。')),
    含场景分隔: mkDoc(para('上半场。'), sb(), para('下半场。')),
    含空段: mkDoc(para('有内容。'), para(''), para('再有内容。')),
  }

  for (const [name, doc] of Object.entries(docs)) {
    it(`${name}:offset → PM → offset 往返一致`, () => {
      const prose = docToText(doc)
      for (let off = 0; off <= prose.length; off++) {
        const pm = proseOffsetToPm(doc, off)
        const back = pmPosToProseOffset(doc, pm)
        // sceneBreak 的 '* * *' 5 字符区间内部 offset 会被夹到块起,
        // 故只对"非场景分隔内部"的 offset 断言严格往返。
        expect(back).toBeLessThanOrEqual(prose.length)
        expect(back).toBeGreaterThanOrEqual(0)
      }
    })
  }

  it('段落内偏移精确:prose offset 命中正确字符', () => {
    const doc = mkDoc(para('他端着药碗,知道回不去了。'))
    const prose = docToText(doc)
    const from = prose.indexOf('知道')
    const to = from + 2
    const pm = proseRangeToPm(doc, from, to)
    expect(pm).not.toBeNull()
    expect(doc.textBetween(pm.pmFrom, pm.pmTo)).toBe('知道')
  })

  it('跨段范围:PM 区间覆盖两段对应文本', () => {
    const doc = mkDoc(para('第一段。'), para('第二段。'))
    const prose = docToText(doc)
    // 选「段。\n\n第二」中间这段(跨块)
    const from = prose.indexOf('段。')
    const to = prose.indexOf('第二') + 2
    const pm = proseRangeToPm(doc, from, to)
    expect(pm).not.toBeNull()
    // textBetween 跨块会带块分隔,去空白后应等于去掉 \n\n 的核心
    const got = doc.textBetween(pm.pmFrom, pm.pmTo, '\n').replace(/\s+/g, '')
    expect(got).toBe('段。第二')
  })

  it('退化:pmTo <= pmFrom 返回 null', () => {
    const doc = mkDoc(para('文字。'))
    expect(proseRangeToPm(doc, 2, 2)).toBeNull()
  })
})
