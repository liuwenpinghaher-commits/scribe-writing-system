import { useState, useRef, useEffect, useMemo } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Send, MessagesSquare, Loader2, User, Wrench, Square, PenLine } from 'lucide-react'
import { api } from './api'
import { useChatPersist } from './useChatPersist'
import { useChiefSlot } from './ChiefSlotContext'
import { fallbackProposalText } from './lib/stageProposal'
import { focusTalk, focusChatKey, nextChatFocusKey } from './lib/focusTalk'
import { useDeduceSel } from './deduceContext'
import { useSelection } from './selectionContext'
import { Btn } from './ui.jsx'

// 主编对话气泡(讨论模式:复用 WriteChat 视觉规范,markdown 渲染 + 工具芯片)
function Bubble({ role, content, tools, streaming }) {
  const me = role === 'user'
  return (
    <div className={`flex gap-2.5 ${me ? 'flex-row-reverse' : ''}`}>
      <div className={`w-7 h-7 rounded-lg shrink-0 grid place-items-center ${me ? 'bg-brand text-brandfg' : 'bg-soft text-brand'}`}>
        {me ? <User size={14} /> : <MessagesSquare size={14} />}
      </div>
      <div className={`max-w-[85%] ${me ? '' : 'flex-1 min-w-0'}`}>
        {!me && tools?.length > 0 && (
          <div className="flex flex-wrap gap-1 mb-1.5">
            {tools.map((t, i) => (
              <span key={i} className="inline-flex items-center gap-1 rounded-md bg-soft/70 border border-line px-1.5 py-0.5 text-f11 text-faint">
                <Wrench size={9} className="text-brand" />
                {(t || '').replace(/^mcp_scribe3_/, '').replace(/^s3_/, '')}
              </span>
            ))}
          </div>
        )}
        <div className={`rounded-2xl px-3.5 py-2.5 text-f14 leading-relaxed ${me ? 'bg-brand text-brandfg' : 'bg-soft/60 text-ink'}`}>
          {me
            ? <span className="whitespace-pre-wrap">{content}</span>
            : (
              <div className="prose-chat">
                {content
                  ? <>{<ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>}{streaming && <Loader2 size={11} className="inline animate-spin text-faint ml-1 align-middle" />}</>
                  : <span className="text-faint">{streaming ? '主编在思考…' : '…'}</span>
                }
              </div>
            )
          }
        </div>
      </div>
    </div>
  )
}

// 据当前选中(章/素材/视图)给主编做上下文前缀 + 一句话定位 + 建议提问。
// phase(章阶段 tab)给定时,章的上下文/建议按阶段(大纲/节拍/演绎/草稿)调整。
// deduceName:演绎阶段当前编辑目标的展示名('场景真相' 或角色名),仅 phase==='deduce' 用。
function selContext(sel, phase, deduceName) {
  if (!sel) return { label: '未选中', prefix: '', suggests: [] }
  if (sel.mode === 'view') {
    const names = { atlas: '关系图谱', insight: '仪表盘', timeline: '时间线', overview: '概览', progress: '进度' }
    const n = names[sel.viewKey] || sel.viewKey
    return {
      label: `视图 · ${n}`,
      prefix: `【当前正在看横切视图:${n}】\n`,
      suggests: [`从${n}看,整体有什么风险或断点?`, '帮我梳理接下来该推进什么'],
    }
  }
  const node = sel.node
  if (!node) return { label: '未选中', prefix: '', suggests: ['这本书现在整体进度如何?', '接下来我该写哪一章?'] }
  if (node.type === 'chapter' || node.type === 'scene') {
    const seq = node.type === 'scene' ? node.ref?.seq : node.ref
    if (phase === 'outline') return {
      label: `第 ${seq} 章 · 大纲`,
      prefix: `【正在写第 ${seq} 章的大纲(synopsis)。请基于已有设定/伏笔/弧光,帮作者把这章大纲讨论清楚】\n`,
      suggests: [`帮我把第 ${seq} 章大纲展开成 3-5 句`, `这章大纲和已埋的伏笔/弧光对得上吗?`],
    }
    if (phase === 'beats') return {
      label: `第 ${seq} 章 · 节拍`,
      prefix: `【正在拆第 ${seq} 章的节拍(beats)。请据本章大纲帮作者把这章拆成有序小节点】\n`,
      suggests: [`据大纲把第 ${seq} 章拆成有序节拍`, `现在的节拍节奏有什么问题?`],
    }
    if (phase === 'deduce') return {
      label: `第 ${seq} 章 · 演绎 · ${deduceName || '场景真相'}`,
      prefix: `【正在做第 ${seq} 章的演绎,当前编辑:${deduceName || '场景真相'}。请据本章大纲/节拍/设定帮作者把这一场演绎清楚】\n`,
      suggests: (deduceName && deduceName !== '场景真相')
        ? [`以「${deduceName}」截至本章的限知,写他这一场的限知投影(看到/听到、知道、以为、做了/说了、没察觉的)`, `「${deduceName}」在这一场最可能误读什么?`]
        : [`写第 ${seq} 章这一场的「场景真相」:全知冷叙,客观上真正发生了什么,含角色们察觉不到的隐藏机制`, '这一场的真相还缺哪块机制?'],
    }
    if (phase === 'draft') return {
      label: `第 ${seq} 章 · 草稿`,
      prefix: `【正在起第 ${seq} 章的草稿。请据本章大纲/节拍与限知帧,帮作者把草稿往下推】\n`,
      suggests: [`据大纲和节拍给第 ${seq} 章草稿开个头`, `这段草稿哪里可以更冷/更志怪?`],
    }
    return {
      label: `第 ${seq} 章`,
      prefix: `【当前选中:第 ${seq} 章】\n`,
      suggests: [`第 ${seq} 章该怎么展开?`, `第 ${seq} 章的伏笔/节奏有什么风险?`],
    }
  }
  const kindName = {
    character: '角色', faction: '势力', item: '物品', term: '术语',
    world_rule: '世界规则', promise: '伏笔', motif: '母题',
    volume: '卷', manuscript_root: '手稿', codex_root: '设定库', codex_category: '设定分类',
    material: '素材', material_root: '素材库', material_category: '素材分类',
  }[node.type] || node.type
  const name = (node.label || '').replace(/^\d+\s*/, '') || node.ref || ''
  return {
    label: `${kindName} · ${name}`.trim(),
    prefix: `【当前选中:${kindName}「${name}」】\n`,
    suggests: [`聊聊${kindName}「${name}」,有什么可以深挖/校验的?`, `「${name}」和已有设定有冲突吗?`],
  }
}

/**
 * 章写作槽(右栏):chapterSel 时渲染。
 * 仅挂一个空槽 div,把其 DOM 经 ChiefSlotContext 注册;WriteLayout 经 portal
 * 把自己的 WriteChat 渲染进这里(WriteChat 仍是 WriteLayout 的子,共享其闭包状态)。
 * 折叠由外层 resizable Panel 负责(RightDock 不传 collapsed/onToggle),此处不再自带折叠 UI。
 */
function WriteSlot() {
  const { setSlotEl } = useChiefSlot()

  return (
    <div className="h-full w-full bg-surface flex flex-col min-h-0">
      {/* 头部:标题 */}
      <div className="shrink-0 h-11 px-3 flex items-center gap-2 border-b border-line">
        <PenLine size={15} className="text-brand shrink-0" />
        <div className="flex flex-col min-w-0 leading-tight">
          <span className="text-f12 font-semibold text-ink">主编 · 写作</span>
          <span className="text-f11 text-faint truncate">提思路让主编写,或改选中段落</span>
        </div>
      </div>
      {/* 写作 chat 槽:WriteLayout 的 WriteChat 经 portal 进来填充此处 */}
      <div ref={setSlotEl} className="flex-1 min-h-0" />
    </div>
  )
}

/**
 * 右主编栏(常驻)。
 * - 非章节点:讨论模式。把当前选中节点/视图作为上下文,走 /chat/agentic-stream(可联查实证)。
 * - 章/场景节点:写作模式。渲染 WriteSlot,WriteLayout 的 WriteChat 经 portal 落进来。
 * 波B Step3:右栏常驻;章=写作槽 / 非章=讨论 chat。无双 chat,无嵌套第4列。
 */
export function ChiefDock({ sel, chapterSel }) {
  const { chapterPhase } = useChiefSlot()
  if (chapterSel) {
    // 正文 tab(final)→ 写作槽(WriteLayout 的 WriteChat portal 进来,出草稿卡/护栏改写)。
    // 大纲/节拍/草稿 tab → 讨论 chat(据阶段调上下文)——右栏不再因切 tab 而消失。
    if (chapterPhase && chapterPhase !== 'final') {
      return <DiscussionDock sel={sel} phase={chapterPhase} />
    }
    return <WriteSlot />
  }
  return <DiscussionDock sel={sel} />
}

// 从选中节点取当前章 seq(章/场景节点),用于草稿阶段把 chapter 传给后端。
function selSeq(sel) {
  const node = sel?.node
  if (!node) return null
  if (node.type === 'chapter') return node.ref
  if (node.type === 'scene') return node.ref?.seq
  return null
}

// 前置阶段(块二)→ 走 /chat/write 的 phase 映射:后端 _phase_role_block 只认 plan|draft|final,
// 大纲/节拍属规划期→'plan';演绎与 DeduceStage.gen 同口径(不带阶段角色,靠 focalizer);草稿→'draft'。
const WRITE_PHASE = { outline: 'plan', beats: 'plan', deduce: '', draft: 'draft' }

function DiscussionDock({ sel, phase }) {
  const seq = useMemo(() => selSeq(sel), [sel])
  const { setStageProposal, chiefIntent, setChiefIntent } = useChiefSlot()
  // 演绎阶段:读左树/中区共享的当前演绎目标('truth' 或 character_id),生成完按它发布 target。
  const { selected: deduceSel } = useDeduceSel()
  const deduceName = deduceSel === 'truth' ? '场景真相' : String(deduceSel || '').replace(/^role:/, '')
  // 块三:通用选中总线 focus 优先——任何视图的显式选中(图谱节点/时间线事件/伏笔行/母题行/帧行…)
  // 立即改写主编标题与话术;focus 为空/sel 镜像/演绎目标 → 回退既有视图级/节点级/阶段话术。
  const { focus } = useSelection()
  const ctx = useMemo(
    () => focusTalk(focus) || selContext(sel, phase, phase === 'deduce' ? deduceName : undefined),
    [focus, sel, phase, deduceName])
  const [msgs, setMsgs] = useState([])
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const endRef = useRef(null)
  const taRef = useRef(null)
  const esRef = useRef(null)
  const proposalTsRef = useRef(0) // 递增计数器:区分「同一 prose 再次生成」以便重新提示

  // 主编对话历史持久化:按 work+当前选中节点/视图存,切节点/刷新可恢复。
  // 块三:显式聚焦(总线 focus)各自成串——切聚焦即切上下文(顺带经 chatKey 效应中止在途流);
  // 镜像/演绎目标不改 key(演绎生成中切目标不得断流,块二口径)。
  // 必修2(方案a):busy(流在途)期间冻结 fKey——生成中点母题行/帧行等纯聚焦只即时改话术 ctx,
  // 不改 chatKey(否则下方 chatKey 效应 abort 在途流,兜底发布永不执行,部分稿静默丢失);
  // 流结束(onDone/onError 置 busy=false)后的下一轮渲染再应用最新 fKey。渲染期写 ref 幂等安全。
  const fKeyRef = useRef('')
  fKeyRef.current = nextChatFocusKey(fKeyRef.current, focusChatKey(focus), busy)
  const fKey = fKeyRef.current
  const chatKey = sel?.mode === 'view'
    ? `${api.getWork()}:view:${sel.viewKey}${fKey}`
    : `${api.getWork()}:node:${sel?.node?.id || 'none'}${phase ? ':' + phase : ''}${fKey}`
  useChatPersist(chatKey, msgs, setMsgs)

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [msgs])
  // 中止在途流:chatStream 返回 EventSource(.close),chatWrite 返回 AbortController(.abort),两者都收。
  const stop = () => { const h = esRef.current; h?.close?.(); h?.abort?.(); esRef.current = null; setBusy(false) }
  // chatStream 返回 EventSource(.close),chatWrite 返回 AbortController(.abort);卸载时都收掉
  useEffect(() => () => { const h = esRef.current; h?.close?.(); h?.abort?.() }, [])
  // 切上下文(chatKey 变=切章/切阶段/切节点/切视图)→ 中止在途流,防旧流 delta 污染新上下文历史(串台)。
  // 只在 chatKey 真的变了时触发,不误伤正常发送(send 期间 chatKey 不变)。
  useEffect(() => { const h = esRef.current; if (h) { h.close?.(); h.abort?.(); esRef.current = null; setBusy(false) } }, [chatKey])

  useEffect(() => {
    const el = taRef.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = Math.min(el.scrollHeight, 128) + 'px'
  }, [input])

  // 块二:消费中区「让主编生成」入口——匹配当前 phase/seq 才消费(预填话术 + 聚焦输入框)。
  useEffect(() => {
    if (!chiefIntent) return
    if (chiefIntent.phase !== phase || chiefIntent.seq !== seq) return
    setChiefIntent(null)
    setInput(chiefIntent.text || '')
    setTimeout(() => taRef.current?.focus(), 0)
  }, [chiefIntent, phase, seq, setChiefIntent])

  const send = (text) => {
    const q = (text ?? input).trim()
    if (!q || busy) return
    const finalMsg = ctx.prefix + q
    setInput('')
    if (taRef.current) taRef.current.style.height = 'auto'
    setMsgs((m) => [...m, { role: 'user', content: q }, { role: 'assistant', content: '', tools: [] }])
    setBusy(true)
    const mut = (fn) => setMsgs((m) => { const c = [...m]; c[c.length - 1] = fn(c[c.length - 1]); return c })
    // 前置阶段(大纲/节拍/演绎/草稿,有本章 seq)→ 走 /chat/write(带映射 phase + chapter):
    // 草稿期后端 _deduction_block 注入本章场景真相 + 各角色限知投影;演绎带 focalizer(与 DeduceStage.gen 同口径)。
    // proposal 围栏(生成正文)与 delta(讨论)都收进同一气泡展示;生成完发布 stageProposal 给中区落地。
    if (seq != null && Object.prototype.hasOwnProperty.call(WRITE_PHASE, phase)) {
      // 发布 target 在发送时捕获:演绎=当前演绎目标;其余阶段 null。生成期间用户切目标/切章,
      // 中区靠 phase/seq/target 匹配不错落。
      const target = phase === 'deduce' ? deduceSel : null
      // proposal 围栏时序:proposal_start → proposal_chunk*(逐段散文文本) → proposal(全量,prose == 各 chunk 拼接)。
      // delta(讨论)与 proposal_chunk(草稿正文)拼进同一气泡 content,故不能整段替换 content。
      // 用「基线 base(围栏开始时的 content)+ 本条 proposal 累积 acc」归一:
      // chunk 逐段累加 acc→content=base+acc(干净流式预览);收尾 proposal 用 base+prose 归一
      // (围栏路径 prose==acc 不重复;纯 delta 兜底路径无 chunk、base 不变、prose 追加一次)。
      let propBase = ''
      let propAcc = ''
      let propOpen = false // 是否见过围栏开始(区分围栏路径 vs 纯 delta 兜底 proposal)
      let gotProposal = false // 是否收到过 proposal 收尾事件(收到则 onDone 不再兜底发布,防双发)
      // 本轮纯 delta 累积:兜底路径(整轮无 proposal 事件)的发布正文。
      // 独立累积而非从气泡 content 反推——发布绝不能在 setMsgs updater 里做
      // (updater 在 render 期间执行,跨组件 setState 触发 React 告警且时序不可靠)。
      let turnText = ''
      // 落地:把本次生成正文经 ChiefSlotContext 发布给中区对应阶段编辑器。
      // 围栏路径 → 纯生成正文 = propAcc(== proposal.prose);兜底 → 本轮 delta 正文。
      const publish = (prose) => {
        const clean = (prose || '').trim()
        if (!clean) return
        setStageProposal({ phase, seq, target, content: clean, ts: ++proposalTsRef.current })
      }
      esRef.current = api.chatWrite(finalMsg, {
        chapter: seq,
        phase: WRITE_PHASE[phase],
        focalizer: phase === 'deduce' && deduceSel !== 'truth' ? deduceSel : '',
        onDelta: (d) => { turnText += d; mut((l) => ({ ...l, content: l.content + d })) },
        onTool: (name) => mut((l) => ({ ...l, tools: [...(l.tools || []), name] })),
        onProposalStart: () => { propOpen = true; propAcc = ''; mut((l) => { propBase = l.content; return l }) },
        onProposalChunk: (c) => { propAcc += (c?.text ?? c ?? ''); mut((l) => ({ ...l, content: propBase + propAcc })) },
        // 围栏路径:base 已记录、prose==propAcc→base+prose 不重复。
        // 兜底路径(无 proposal_start):propOpen=false,把 prose 追加到已有讨论文之后,不吞 delta。
        // 无论哪条路径,拿到最终生成正文都 publish 给中区(只发纯生成正文,不含讨论前言)。
        onProposal: (p) => {
          gotProposal = true
          const prose = p?.prose ?? p?.text ?? propAcc
          mut((l) => ({ ...l, content: propOpen ? propBase + prose : l.content + prose }))
          publish(prose)
        },
        // 兜底(选择逻辑抽 fallbackProposalText 纯函数,负例见单测):无 proposal 收尾时,
        // 围栏开过 → 发部分正文 propAcc(截断稿),否则发纯 delta;收到过 proposal 绝不重发。
        onDone: () => {
          setBusy(false)
          const fb = fallbackProposalText({ gotProposal, propOpen, propAcc, turnText })
          if (fb != null) publish(fb)
        },
        onError: (err) => { mut((l) => ({ ...l, content: l.content + `\n\n_⚠ ${err}_` })); setBusy(false) },
      })
      return
    }
    // 非章前置阶段(素材/视图等):走 /chat/stream(绑当前书 + 注入该书设定圣经),不走 MCP 网关(网关连固定库会串到别的书)
    esRef.current = api.chatStream(finalMsg, {
      agentic: false,
      onDelta: (d) => mut((l) => ({ ...l, content: l.content + d })),
      onTool: (name) => mut((l) => ({ ...l, tools: [...(l.tools || []), name] })),
      onDone: () => setBusy(false),
      onError: (err) => { mut((l) => ({ ...l, content: l.content + `\n\n_⚠ ${err}_` })); setBusy(false) },
    })
  }

  return (
    <div className="h-full w-full bg-surface flex flex-col min-h-0">
      {/* 头部:标题 + 上下文(折叠由外层 resizable Panel 负责,此处不再自带折叠 UI) */}
      <div className="shrink-0 h-11 px-3 flex items-center gap-2 border-b border-line">
        <MessagesSquare size={15} className="text-brand shrink-0" />
        <div className="flex flex-col min-w-0 leading-tight">
          <span className="text-f12 font-semibold text-ink">主编</span>
          <span className="text-f11 text-faint truncate" data-testid="chief-ctx">{ctx.label}</span>
        </div>
      </div>

      {/* 消息列表 */}
      <div className="flex-1 min-h-0 overflow-y-auto px-3 py-3 space-y-3">
        {msgs.length === 0 ? (
          <div className="pt-2">
            <div className="text-f12 text-faint mb-2.5 leading-snug">就当前选中的内容与主编讨论。主编可联查书内实证(角色/伏笔/事件/设定)。</div>
            <div className="space-y-1.5">
              {ctx.suggests.map((s) => (
                <button key={s} onClick={() => send(s)}
                  className="w-full text-left rounded-lg border border-line bg-canvas hover:border-brand hover:bg-soft/40 px-2.5 py-1.5 text-f12 text-ink transition-colors cursor-pointer">{s}</button>
              ))}
            </div>
          </div>
        ) : msgs.map((m, i) => (
          <Bubble key={i} {...m} streaming={busy && i === msgs.length - 1 && m.role === 'assistant'} />
        ))}
        <div ref={endRef} />
      </div>

      {/* 输入区 */}
      <div className="shrink-0 border-t border-line px-2.5 py-2">
        <div className="flex items-end gap-1.5 rounded-xl bg-canvas px-2.5 py-2 focus-within:ring-1 focus-within:ring-brand/40 transition-shadow">
          <textarea
            ref={taRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            rows={1}
            placeholder="就当前内容问主编…(Enter 发送)"
            onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() } }}
            className="flex-1 resize-none bg-transparent text-f13 text-ink outline-none max-h-32 leading-relaxed placeholder:text-faint"
          />
          {busy ? (
            // 生成中:发送键变「停止」——中止在途流(EventSource.close/AbortController.abort)+ 解锁 busy,可立即再发。
            <Btn variant="danger" icon onClick={stop} title="停止生成" aria-label="停止生成" className="shrink-0">
              <Square size={13} fill="currentColor" />
            </Btn>
          ) : (
            <Btn variant="primary" icon onClick={() => send()} disabled={!input.trim()} aria-label="发送" className="shrink-0">
              <Send size={15} />
            </Btn>
          )}
        </div>
      </div>
    </div>
  )
}
