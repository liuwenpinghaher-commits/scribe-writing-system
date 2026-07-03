import { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react'

/**
 * 块三:通用选中总线(universal selection bus)。
 *
 * focus = { type, id, label, payload?, origin } | null
 *  - type ∈ chapter/scene/character/faction/item/term/world_rule/promise/motif/event/frame_fact/deduction/view
 *  - id/label:选中项标识与展示名;payload:附加信息(章号/主题/密级等),主编话术与后续中区详情联动(块四)用
 *  - origin:发起方。'sel' = 项目树/视图级 sel 的镜像(主编按既有 selContext 话术回退);
 *    其余('atlas'/'timeline'/'panel'/'insight'/'deduce')= 显式聚焦,主编按 focusTalk 生成聚焦话术。
 *
 * 任何视图选中即 setFocus(规范对象):图谱节点/时间线事件/左栏伏笔·母题·帧行/演绎目标/仪表盘条目。
 * 过渡期与现有 sel 并存:sel 变化由 <SelMirror> 映射为 focus;focus 不反向改 sel(不重写现有导航)。
 */
const Ctx = createContext(null)

export function SelectionProvider({ children }) {
  const [focus, setFocusState] = useState(null)
  // 最近一次「显式」setFocus 的时刻:同一次交互里聚焦+跳章并发时(如点伏笔行→聚焦伏笔并跳埋设章),
  // 跳章引发的 sel 镜像不得反把 focus 冲成「章」——SelMirror 据此在极短窗口内避让。
  const lastSetRef = useRef(0)
  const setFocus = useCallback((f) => { lastSetRef.current = Date.now(); setFocusState(f) }, [])
  // 镜像专用:不计入「显式聚焦」时间戳(连续快速点两个树节点时,第二次镜像不得被第一次避让掉)。
  const mirrorFocus = useCallback((f) => { setFocusState(f) }, [])
  return <Ctx.Provider value={{ focus, setFocus, mirrorFocus, lastSetRef }}>{children}</Ctx.Provider>
}

export function useSelection() {
  return useContext(Ctx) || { focus: null, setFocus: () => {}, mirrorFocus: () => {}, lastSetRef: { current: 0 } }
}

/** sel({mode:'view'|'node'}) → focus 镜像(origin:'sel')。纯函数,便于单测。 */
export function focusFromSel(sel) {
  if (!sel) return null
  if (sel.mode === 'view') return { type: 'view', id: sel.viewKey, label: sel.viewKey, origin: 'sel' }
  const node = sel.node
  if (!node) return null
  return {
    type: node.type,
    id: node.id,
    label: node.label || String(node.ref ?? ''),
    payload: { ref: node.ref },
    origin: 'sel',
  }
}

/** 挂在 SelectionProvider 内、由持有 sel 的层(BinderLayout)渲染:sel 变化 → 镜像成 focus。 */
export function SelMirror({ sel }) {
  const { mirrorFocus, lastSetRef } = useSelection()
  useEffect(() => {
    // 400ms 内刚有显式聚焦(点伏笔行/仪表盘卡等触发的跳章与聚焦同属一次交互)→ 本次 sel 变化不镜像覆盖
    if (Date.now() - lastSetRef.current < 400) return
    mirrorFocus(focusFromSel(sel))
  }, [sel]) // eslint-disable-line react-hooks/exhaustive-deps
  return null
}
