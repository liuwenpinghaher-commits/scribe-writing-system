import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import { Sparkles } from 'lucide-react'
import { Btn } from './ui.jsx'
import { matchStageProposal } from './lib/stageProposal'

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
const ChiefSlotContext = createContext({
  slotEl: null, setSlotEl: () => {},
  chapterPhase: null, setChapterPhase: () => {},
  stageProposal: null, setStageProposal: () => {},
  chiefIntent: null, setChiefIntent: () => {},
})

export function ChiefSlotProvider({ children }) {
  // 用 state 持有 slot DOM(而非裸 ref):槽挂载/卸载会触发依赖方重渲染,
  // 解决「ChapterStudio 把 WriteLayout 包在 tab 里时 portal 目标尚未就绪」的时序问题。
  const [slotEl, setSlotElState] = useState(null)
  // callback ref 形态:稳定引用,DOM 变化即同步(挂载传 el,卸载传 null)
  const setSlotEl = useCallback((el) => { setSlotElState(el || null) }, [])
  // 当前章的阶段 tab(由 ChapterStudio 发布):'outline'|'beats'|'deduce'|'draft'|'final'|null。
  // ChiefDock 据此决定右栏:final=写作槽(WriteLayout portal);其余=讨论(据阶段调上下文)。
  const [chapterPhase, setChapterPhase] = useState(null)
  // 块二:通用 stageProposal 落点通道(草稿旧 draftProposal 并入,单通道)。
  // ChiefDock(右栏)在前置阶段生成完毕时发布 { phase, seq, target, content, ts },
  // 中区对应阶段编辑器经 useStageProposal 接住(phase/seq/target 全匹配才显示),
  // 给出「填入/追加」提示条。ts 递增,区分「同一内容再次生成」以便重新提示。
  const [stageProposal, setStageProposal] = useState(null)
  // 块二:中区「让主编生成」入口 → 右栏预填话术通道 { phase, seq, text }。
  // DiscussionDock 匹配当前 phase/seq 后消费:预填输入框 + 聚焦(生成在主编,落地在中区)。
  const [chiefIntent, setChiefIntent] = useState(null)
  // 外部发布 seam:window 派发 CustomEvent('s3:stage-proposal', {detail}) 也走同一通道。
  // 供真机注入测试/未来外部集成模拟「主编生成完成」,与 ChiefDock 发布口径完全一致。
  useEffect(() => {
    const h = (e) => { if (e?.detail) setStageProposal(e.detail) }
    window.addEventListener('s3:stage-proposal', h)
    return () => window.removeEventListener('s3:stage-proposal', h)
  }, [])
  return (
    <ChiefSlotContext.Provider value={{ slotEl, setSlotEl, chapterPhase, setChapterPhase, stageProposal, setStageProposal, chiefIntent, setChiefIntent }}>
      {children}
    </ChiefSlotContext.Provider>
  )
}

export function useChiefSlot() {
  return useContext(ChiefSlotContext)
}

/**
 * 中区阶段编辑器接收 stageProposal:phase/seq/target 全匹配且内容非空才给 pending,
 * 否则 null(切章/切阶段/切演绎目标后旧 proposal 不得错落)。consume 后调 clear 撤提示条。
 */
export function useStageProposal(phase, seq, target = null) {
  const { stageProposal, setStageProposal } = useChiefSlot()
  const pending = matchStageProposal(stageProposal, { phase, seq, target })
  const clear = useCallback(() => setStageProposal(null), [setStageProposal])
  return { pending, clear }
}

/** 「主编生成了内容」提示条(各阶段共用视觉;actions: [{label, onClick, variant?}];
 *  onDismiss:「忽略」——纯讨论轮也会经兜底发布出提示条,给一条不落地的退路(调 clear)。 */
export function ProposalBar({ text, actions, onDismiss }) {
  return (
    <div className="mb-2 rounded-md border border-brand/20 bg-brand/10 text-brand px-3 py-2 flex items-center gap-2 flex-wrap">
      <Sparkles size={14} className="shrink-0" />
      <span className="text-f13 flex-1 min-w-0">{text}</span>
      <div className="flex items-center gap-1.5 shrink-0">
        {actions.map((a) => (
          <Btn key={a.label} data-testid={a.label.startsWith('填入') ? 'stage-fill' : a.label.startsWith('追加') ? 'stage-append' : undefined}
            variant={a.variant || 'soft'} size="sm" onClick={a.onClick}>{a.label}</Btn>
        ))}
        {onDismiss && <Btn variant="ghost" size="sm" onClick={onDismiss} aria-label="忽略" data-testid="stage-dismiss">忽略</Btn>}
      </div>
    </div>
  )
}
