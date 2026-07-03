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

/** 一次性消费 suppress 标记:置位 → 本次返回 true 并复位;未置位 → false。纯逻辑,便于单测。 */
export function consumeSuppress(ref) {
  if (ref.current) { ref.current = false; return true }
  return false
}

export function SelectionProvider({ children }) {
  const [focus, setFocus] = useState(null)
  // 一次性事务标记(spec 审查必修1):「聚焦+跳章」复合动作(点伏笔行/仪表盘卡内跳章)在 setFocus
  // 的同时置位;紧随其后的那一次 sel 变化被 SelMirror 消费掉(跳过镜像,保住伏笔聚焦),
  // 再往后的任何 sel 变化正常镜像——因果标记替代时间窗,快速连点(跳章后立刻点树节点)天然正确。
  const suppressNextMirrorRef = useRef(false)
  const suppressNextMirror = useCallback(() => { suppressNextMirrorRef.current = true }, [])
  return (
    <Ctx.Provider value={{ focus, setFocus, suppressNextMirror, suppressNextMirrorRef }}>
      {children}
    </Ctx.Provider>
  )
}

export function useSelection() {
  return useContext(Ctx) || {
    focus: null, setFocus: () => {},
    suppressNextMirror: () => {}, suppressNextMirrorRef: { current: false },
  }
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

/** 挂在 SelectionProvider 内、由持有 sel 的层(BinderLayout)渲染:sel 变化 → 镜像成 focus。
 *  suppress 标记置位时消费掉本次变化(复合动作里的跳章不冲掉刚设的显式聚焦)。 */
export function SelMirror({ sel }) {
  const { setFocus, suppressNextMirrorRef } = useSelection()
  useEffect(() => {
    if (consumeSuppress(suppressNextMirrorRef)) return
    setFocus(focusFromSel(sel))
  }, [sel]) // eslint-disable-line react-hooks/exhaustive-deps
  return null
}
