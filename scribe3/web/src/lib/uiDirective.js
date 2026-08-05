/**
 * ui_directive 总线 · 与后端 apply_ui_directive_events 契约对齐。
 * 程序化跟焦，不依赖模型自觉。
 */

/**
 * selection detail → 选中总线 focus（无 onSel 时的回退）。
 * @param {{ mode?: string, node?: object }} detail
 * @returns {object|null}
 */
export function focusFromSelectionDetail(detail) {
  if (!detail || typeof detail !== 'object') return null
  const node = detail.node || (detail.mode === 'node' ? detail : null)
  if (!node || typeof node !== 'object') return null
  return {
    type: node.type,
    id: node.id || node.ref || node.type,
    label: node.label || String(node.ref ?? node.id ?? ''),
    payload: { ref: node.ref },
    origin: 'orchestration',
  }
}

/**
 * @param {Array<{type:string, detail?:object}>} events
 * @param {{ onSel?: Function, setFocus?: Function }} [opts]
 */
export function applyUiEvents(events, opts = {}) {
  if (!Array.isArray(events)) return
  for (const ev of events) {
    if (!ev || !ev.type) continue
    const detail = ev.detail
    try {
      if (ev.type === 'selection') {
        // 1) 显式 onSel（App setSel / 旅程 continue）
        if (typeof opts.onSel === 'function') {
          opts.onSel(detail)
        } else {
          // 2) 无 onSel 时：全局事件 + setFocus，禁止静默丢弃
          try {
            window.dispatchEvent(new CustomEvent('s3-selection', { detail }))
          } catch { /* */ }
        }
        if (typeof opts.setFocus === 'function') {
          const f = focusFromSelectionDetail(detail)
          if (f) opts.setFocus(f)
        } else if (typeof opts.onSel !== 'function') {
          // 再广播一次 focus 形状，供未持有 onSel 的 dock 订阅
          try {
            const f = focusFromSelectionDetail(detail)
            if (f) window.dispatchEvent(new CustomEvent('s3-focus', { detail: f }))
          } catch { /* */ }
        }
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
        // panel / 全量 directive：LeftDock 等可按 panel 开伏笔/母题台
        window.dispatchEvent(new CustomEvent('s3-ui-directive', { detail }))
        const panel = detail?.panel
        if (panel && !detail?.capability) {
          // 与后端 panel_to_cap 对齐的轻量回退（后端已发 open-capability 时幂等）
          const map = {
            promise: 'promise', motif: 'motif', northstar: 'northstar',
            codex_character: 'codex', outline: 'manuscript', beats: 'manuscript',
            deduce: 'deduce', qc: 'review',
          }
          const cap = map[panel]
          if (cap) {
            window.dispatchEvent(new CustomEvent('s3-open-capability', {
              detail: { capability: cap, focus: true, panel },
            }))
          }
        }
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
  if (directive.panel) {
    events.push({
      type: 's3-ui-directive',
      detail: {
        entry: directive.entry,
        phase: directive.phase,
        node: directive.node,
        panel: directive.panel,
        right_tab: directive.right_tab || 'chief',
      },
    })
    const panelCap = {
      promise: 'promise', motif: 'motif', northstar: 'northstar',
      codex_character: 'codex', outline: 'manuscript',
    }[directive.panel]
    if (panelCap) {
      events.push({
        type: 's3-open-capability',
        detail: { capability: panelCap, focus: true, panel: directive.panel },
      })
    }
  }
  return events
}
