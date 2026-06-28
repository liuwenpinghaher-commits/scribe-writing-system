/**
 * F-05: 护栏可操作性 — GuardDecoration(进阶 + 完整)
 *
 * 进阶:把 MVP 的"点击才 flash"升级为 TipTap/ProseMirror Decoration 插件——
 *   所有当前 issue 在正文上【常驻波浪下划线】,六类分色(set.map 防漂移)。
 * 完整:点波浪线 → 派发 'guard:issue-click' 事件(WriteLayout 接住弹悬浮卡)。
 *
 * 核心能力:
 * 1. proseOffsetToPm / proseRangeToPm — prose 字符 offset → ProseMirror 位置(逆 pmPosToProseOffset)。
 * 2. GuardDecoration Extension — addProseMirrorPlugins 返回 plugin,DecorationSet 常驻波浪线,
 *    apply 里先 set.map(防漂移)再吸收 meta 注入的新 issues。
 * 3. pushIssues(editor, issues) — 外部把 issues 注入 decoration 层。
 * 4. focusIssue(editor, issue) — 滚动定位 + 叠一层 flash decoration(1.2s 后撤)。
 * 5. 失配兜底:it.text 校验 → toText.indexOf 回退 → 仍失败丢弃(宁可不标不标错)。
 */
import { Extension } from '@tiptap/core'
import { Plugin, PluginKey } from '@tiptap/pm/state'
import { Decoration, DecorationSet } from '@tiptap/pm/view'

export const guardKey = new PluginKey('guard')

/**
 * prose 字符串 offset → ProseMirror 文档位置。
 * 逆 pmPosToProseOffset,口径完全照抄 ProseEditor.jsx:
 * - 顶层块间 +2 (对应 '\n\n')
 * - sceneBreak: 序列化为 '* * *' (5字符),内部位置落到块起
 * - 段落: 文本始于 nodeStart+1
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

/** 与 ProseEditor.jsx toText 同口径:段落 \n\n 隔,sceneBreak → '* * *' */
export function docToText(doc) {
  const parts = []
  doc.forEach((node) => {
    parts.push(node.type.name === 'sceneBreak' ? '* * *' : node.textContent)
  })
  return parts.join('\n\n')
}

const _strip = (s) => (s || '').replace(/\s+/g, '')

/**
 * 把一条 issue 解析成 PM 位置(带失配兜底)。
 * 1) range → proseRangeToPm;
 * 2) 用 it.text 校验:doc.textBetween 去空白 ≠ text 去空白 → 回退;
 * 3) 回退:在 toText 上 indexOf(text) 重算 offset 再转 PM;
 * 4) 仍失败 → 返回 null(不画错位置的线)。
 */
export function resolveIssuePm(doc, issue) {
  const text = issue?.text || ''
  const range = issue?.range
  // 路径 A:用 range 直接转,再 text 校验
  if (Array.isArray(range) && range.length >= 2) {
    const pm = proseRangeToPm(doc, range[0], range[1])
    if (pm) {
      if (!text) return pm
      const got = doc.textBetween(pm.pmFrom, pm.pmTo, '\n')
      if (_strip(got) === _strip(text)) return pm
      // 校验失败 → 落到路径 B
    }
  }
  // 路径 B:text indexOf 回退
  if (text) {
    const prose = docToText(doc)
    const idx = prose.indexOf(text)
    if (idx >= 0) {
      const pmFb = proseRangeToPm(doc, idx, idx + text.length)
      if (pmFb) return pmFb
    }
  }
  return null
}

/**
 * 把 issues 列表编译成 Decoration[]。每条带 range 的 issue → 一段波浪线 inline decoration,
 * class = `guard-uline guard-<type>`,data-issue-id 用于点击反查。
 */
function buildDecorations(doc, issues) {
  const decos = []
  for (const it of issues || []) {
    const pm = resolveIssuePm(doc, it)
    if (!pm) continue
    decos.push(Decoration.inline(pm.pmFrom, pm.pmTo, {
      class: `guard-uline guard-${it.type || 'misc'}`,
      'data-issue-id': String(it.id),
    }))
  }
  return decos
}

/**
 * GuardDecoration Extension：常驻波浪线 decoration 层。
 * - state.init: 空集合 + active=null + issues=[]
 * - state.apply: 先 set.map(防漂移),再吸收 meta(issues 重建 / active 叠 flash)
 * - props.decorations: 返回常驻集合;active 时叠一层 guard-flash
 * - props.handleClick: 命中 data-issue-id → 派发 'guard:issue-click' 事件
 */
export const GuardDecoration = Extension.create({
  name: 'guardDecoration',
  addProseMirrorPlugins() {
    return [
      new Plugin({
        key: guardKey,
        state: {
          init: () => ({ set: DecorationSet.empty, active: null, issues: [] }),
          apply(tr, value) {
            // 1) 先把已有 decoration 随文档变化映射(作者打字时不漂、不闪)
            let set = value.set.map(tr.mapping, tr.doc)
            let active = value.active
            let issues = value.issues
            // 若有结构性文档改动且 active 仍在,映射其 pm(避免 flash 位错)
            if (active && tr.docChanged) {
              const pmFrom = tr.mapping.map(active.pm.pmFrom)
              const pmTo = tr.mapping.map(active.pm.pmTo)
              active = pmTo > pmFrom ? { ...active, pm: { pmFrom, pmTo } } : null
            }
            // 2) 外部注入(/check 回来 / 面板点选)
            const meta = tr.getMeta(guardKey)
            if (meta) {
              if (meta.issues !== undefined) {
                issues = meta.issues || []
                set = DecorationSet.create(tr.doc, buildDecorations(tr.doc, issues))
              }
              if (meta.active !== undefined) active = meta.active
            }
            return { set, active, issues }
          },
        },
        props: {
          decorations(state) {
            const st = guardKey.getState(state)
            if (!st) return null
            if (!st.active || !st.active.pm) return st.set
            const { pmFrom, pmTo } = st.active.pm
            return st.set.add(state.doc, [
              Decoration.inline(pmFrom, pmTo, { class: 'guard-flash' }),
            ])
          },
          handleClick(view, pos, event) {
            const el = event.target
            const id = el && el.getAttribute && el.getAttribute('data-issue-id')
            if (id != null && id !== '') {
              view.dom.dispatchEvent(new CustomEvent('guard:issue-click', {
                detail: { id }, bubbles: true,
              }))
              return true
            }
            return false
          },
        },
      }),
    ]
  },
})

/**
 * 命令式 API:把 issues 注入 decoration 层。给每条 issue 派 id(若后端没给)。
 * 返回带 id 的 issues(供面板与正文共享同一份 id)。
 */
export function pushIssues(editor, issues) {
  if (!editor || !editor.view) return []
  const withId = (issues || []).map((it, i) => ({ ...it, id: it.id ?? `iss-${i}` }))
  editor.view.dispatch(editor.state.tr.setMeta(guardKey, { issues: withId }))
  return withId
}

/**
 * 点护栏面板一条 issue → 滚动定位 + 叠 flash decoration(1.2s 后撤)。
 * 复用 resolveIssuePm 的失配兜底(range → text 校验 → indexOf 回退 → 丢弃)。
 *
 * @returns {boolean} 是否成功定位
 */
export function focusIssue(editor, issue) {
  if (!editor || !editor.view || !issue) return false
  const doc = editor.state.doc
  const pm = resolveIssuePm(doc, issue)
  if (!pm) return false
  editor.chain()
    .setTextSelection({ from: pm.pmFrom, to: pm.pmTo })
    .scrollIntoView()
    .run()
  editor.view.dispatch(editor.state.tr.setMeta(guardKey, { active: { id: issue.id, pm } }))
  setTimeout(() => {
    if (editor.view && !editor.view.isDestroyed) {
      editor.view.dispatch(editor.state.tr.setMeta(guardKey, { active: null }))
    }
  }, 1200)
  return true
}
