import { createContext, useCallback, useContext, useState } from 'react'

/**
 * ChiefSlotContext —— 章写作 chat 的「落点」共享。
 *
 * 波B Step3:把 WriteLayout 内部实例化的 WriteChat,经 React Portal 渲染进
 * 右栏 ChiefDock 的槽容器(消除 WriteLayout 内嵌 Shell 的第4列),
 * 但 WriteChat 在逻辑树上仍是 WriteLayout 的子(共享其全部闭包状态)——
 * portal 只改 DOM 落点,不改逻辑树、不上提状态。写作链路零回归。
 *
 * - ChiefDock(provider 由 BinderLayout 提供)挂一个空槽 div,经 setSlotEl 注册其 DOM。
 * - WriteLayout 经 useChiefSlot() 拿到该 DOM,createPortal(<WriteChat/>, slotEl)。
 * - 槽未就绪(null)时,WriteLayout 内部兜底渲染(见 WriteLayout 注释),不丢 chat。
 */
const ChiefSlotContext = createContext({ slotEl: null, setSlotEl: () => {}, chapterPhase: null, setChapterPhase: () => {}, draftProposal: null, setDraftProposal: () => {} })

export function ChiefSlotProvider({ children }) {
  // 用 state 持有 slot DOM(而非裸 ref):槽挂载/卸载会触发依赖方重渲染,
  // 解决「ChapterStudio 把 WriteLayout 包在 tab 里时 portal 目标尚未就绪」的时序问题。
  const [slotEl, setSlotElState] = useState(null)
  // callback ref 形态:稳定引用,DOM 变化即同步(挂载传 el,卸载传 null)
  const setSlotEl = useCallback((el) => { setSlotElState(el || null) }, [])
  // 当前章的阶段 tab(由 ChapterStudio 发布):'outline'|'beats'|'draft'|'final'|null。
  // ChiefDock 据此决定右栏:final=写作槽(WriteLayout portal);其余=讨论(据阶段调上下文)。
  const [chapterPhase, setChapterPhase] = useState(null)
  // 草稿 proposal 落点通道:ChiefDock(右栏)在草稿生成完毕时发布 { seq, prose, ts },
  // DraftTab(中区)接住,给出「填入草稿框/追加到草稿」按钮。ts 递增,用于区分
  // 「同一 prose 再次生成」以便重新提示(不用 Date.now(),避免环境禁用/时钟依赖)。
  const [draftProposal, setDraftProposal] = useState(null)
  return (
    <ChiefSlotContext.Provider value={{ slotEl, setSlotEl, chapterPhase, setChapterPhase, draftProposal, setDraftProposal }}>
      {children}
    </ChiefSlotContext.Provider>
  )
}

export function useChiefSlot() {
  return useContext(ChiefSlotContext)
}
