/**
 * F-05: 护栏可操作性 — GuardDecoration
 *
 * 提供两个核心能力:
 * 1. proseOffsetToPm(doc, target) — prose 字符 offset → ProseMirror 位置
 *    口径必须与 ProseEditor.jsx 的 toText/pmPosToProseOffset 完全一致:
 *    顶层块以 \n\n 相连,sceneBreak 序列化为 '* * *',段落内文本始于 nodeStart+1。
 * 2. focusIssue(editor, issue) — 把编辑器滚动到 issue.range 对应的句,并闪烁高亮 1.2s。
 *    MVP 只做点击定位 + flash,不做常驻波浪线 decoration(进阶再做)。
 */

/**
 * prose 字符串 offset → ProseMirror 文档位置。
 * 逆 pmPosToProseOffset,口径完全照抄 ProseEditor.jsx:
 * - 顶层块间 +2 (对应 '\n\n')
 * - sceneBreak: 序列化为 '* * *' (5字符),内部位置落到块起
 * - 段落: 文本始于 nodeStart+1
 *
 * @param {import('prosemirror-model').Node} doc
 * @param {number} target  prose 字符串中的字符偏移
 * @returns {number} ProseMirror 位置
 */
export function proseOffsetToPm(doc, target) {
  let acc = 0    // 已走过的 prose 字符数(含块间 \n\n)
  let pos = 0    // 每个顶层节点前的 PM 位置
  let result = null

  doc.forEach((node) => {
    if (result !== null) {
      pos += node.nodeSize
      return
    }
    const serialized = node.type.name === 'sceneBreak' ? '* * *' : node.textContent
    const len = serialized.length

    if (target <= acc + len) {
      // target 落在本块内
      if (node.type.name === 'sceneBreak') {
        result = pos  // atom 块:落到块起
      } else {
        const inBlock = Math.max(0, Math.min(len, target - acc))
        result = pos + 1 + inBlock  // +1 跳过段落开标记
      }
    } else {
      // target 在本块之后:累加本块长度 + \n\n
      acc += len + 2
      pos += node.nodeSize
    }
  })

  return result === null ? pos : result
}

/**
 * prose 字符串 [from, to) → PM 位置 { pmFrom, pmTo }
 * 失败(跨界 / pmTo <= pmFrom)返回 null。
 */
export function proseRangeToPm(doc, from, to) {
  const pmFrom = proseOffsetToPm(doc, from)
  const pmTo = proseOffsetToPm(doc, to)
  if (pmFrom == null || pmTo == null || pmTo <= pmFrom) return null
  return { pmFrom, pmTo }
}

/**
 * 点护栏面板一条 issue → 编辑器滚动定位 + 临时 flash 高亮(1.2s 消失)。
 * MVP:不做常驻波浪线 decoration,只做点击滚动 + flash。
 *
 * @param {import('@tiptap/react').Editor} editor  TipTap editor 实例
 * @param {{ range: [number, number] | null, text?: string }} issue
 * @returns {boolean} 是否成功定位
 */
export function focusIssue(editor, issue) {
  if (!editor || !issue) return false
  const range = issue.range
  if (!Array.isArray(range) || range.length < 2) return false

  const doc = editor.state.doc
  const pm = proseRangeToPm(doc, range[0], range[1])
  if (!pm) {
    // 失配兜底:用 issue.text 在 toText 里 indexOf 重算
    if (!issue.text) return false
    const prose = _docToText(doc)
    const idx = prose.indexOf(issue.text)
    if (idx < 0) return false
    const pmFb = proseRangeToPm(doc, idx, idx + issue.text.length)
    if (!pmFb) return false
    return _scrollAndFlash(editor, pmFb)
  }
  return _scrollAndFlash(editor, pm)
}

/** 与 ProseEditor.jsx toText 同口径:段落 \n\n 隔,sceneBreak → '* * *' */
function _docToText(doc) {
  const parts = []
  doc.forEach((node) => {
    parts.push(node.type.name === 'sceneBreak' ? '* * *' : node.textContent)
  })
  return parts.join('\n\n')
}

/**
 * 滚动到 pmFrom..pmTo 并插入 guard-flash 的 DOM span,1200ms 后清除。
 * MVP 不用 ProseMirror decoration plugin,直接操作 DOM(简单可靠)。
 */
function _scrollAndFlash(editor, { pmFrom, pmTo }) {
  try {
    // 设置选区到目标范围起点,再滚动进视野
    editor.chain()
      .setTextSelection({ from: pmFrom, to: pmTo })
      .scrollIntoView()
      .run()

    // 用 coordsAtPos 拿到 DOM 坐标,插入临时 flash span
    const view = editor.view
    if (!view) return true

    const coords = view.coordsAtPos(pmFrom)
    if (!coords) return true

    // 找到 PM 对应的 DOM 节点,给范围内 DOM 加 class
    // 简化:直接在编辑器根节点上创建一个绝对定位的 flash overlay
    const dom = view.dom
    const editorRect = dom.getBoundingClientRect()
    const toCoords = view.coordsAtPos(Math.min(pmTo, editor.state.doc.content.size - 1))

    const flashEl = document.createElement('div')
    flashEl.className = 'guard-flash-overlay'
    flashEl.style.cssText = [
      'position:absolute',
      `top:${coords.top - editorRect.top + dom.scrollTop}px`,
      `left:${Math.min(coords.left, toCoords.left) - editorRect.left}px`,
      `width:${Math.max(Math.abs(toCoords.left - coords.left), 60)}px`,
      `height:${(toCoords.bottom - coords.top) || 20}px`,
      'background:color-mix(in srgb, #f59e0b 25%, transparent)',
      'border-radius:3px',
      'pointer-events:none',
      'transition:opacity 0.4s',
      'z-index:10',
    ].join(';')

    // 挂到编辑器容器上(需要 position:relative)
    const shell = dom.closest('.tiptap-shell') || dom.parentElement
    if (shell) {
      shell.style.position = 'relative'
      shell.appendChild(flashEl)
      setTimeout(() => {
        flashEl.style.opacity = '0'
        setTimeout(() => flashEl.remove(), 400)
      }, 800)
    }

    return true
  } catch (_) {
    return false
  }
}
