/**
 * ui_directive 总线 · 与后端 apply_ui_directive_events 契约对齐。
 * 程序化跟焦，不依赖模型自觉。
 */

/**
 * @param {Array<{type:string, detail?:object}>} events
 * @param {{ onSel?: Function }} [opts]
 */
export function applyUiEvents(events, opts = {}) {
  if (!Array.isArray(events)) return
  for (const ev of events) {
    if (!ev || !ev.type) continue
    const detail = ev.detail
    try {
      if (ev.type === 'selection' && opts.onSel) {
        opts.onSel(detail)
        continue
      }
      if (ev.type === 's3-right-tab') {
        window.dispatchEvent(new CustomEvent('s3-right-tab', { detail }))
        continue
      }
      if (ev.type === 's3-chapter-phase') {
        window.dispatchEvent(new CustomEvent('s3-chapter-phase', { detail }))
        continue
      }
      if (ev.type === 's3-open-capability') {
        window.dispatchEvent(new CustomEvent('s3-open-capability', { detail }))
        continue
      }
      if (ev.type === 's3-ui-directive') {
        window.dispatchEvent(new CustomEvent('s3-ui-directive', { detail }))
      }
    } catch { /* */ }
  }
}

/**
 * 将后端 package.ui_directive 规范为事件列表（前端兜底，与 Python 对齐的最小实现）。
 * 优先使用服务端返回的 ui_events。
 */
export function uiDirectiveToEvents(directive) {
  if (!directive || typeof directive !== 'object') return []
  const events = []
  events.push({ type: 's3-right-tab', detail: directive.right_tab || 'chief' })
  const node = directive.node
  const phase = directive.phase
  const entry = directive.entry
  if (entry && entry !== 'manuscript') {
    events.push({ type: 's3-open-capability', detail: { capability: entry, focus: true } })
  } else if (entry === 'manuscript') {
    events.push({ type: 's3-open-capability', detail: { capability: 'manuscript', focus: true } })
  }
  if (node && node.type === 'chapter' && node.ref != null) {
    const seq = Number(node.ref)
    events.push({
      type: 'selection',
      detail: {
        mode: 'node',
        node: {
          id: node.id || `ch:${seq}`,
          type: 'chapter',
          ref: seq,
          label: node.label || String(seq),
        },
      },
    })
    if (phase) {
      events.push({ type: 's3-chapter-phase', detail: { phase, seq } })
    }
  } else if (node && node.type === 'character') {
    events.push({
      type: 'selection',
      detail: {
        mode: 'node',
        node: {
          id: node.id || 'character',
          type: 'character',
          ref: node.id,
          label: node.label || '',
        },
      },
    })
    events.push({ type: 's3-open-capability', detail: { capability: 'codex', focus: true } })
  } else if (node && node.type === 'promise') {
    events.push({
      type: 'selection',
      detail: {
        mode: 'node',
        node: {
          id: node.id || 'promise:focus',
          type: 'promise',
          ref: node.id,
          label: node.label || '伏笔',
        },
      },
    })
  }
  return events
}
