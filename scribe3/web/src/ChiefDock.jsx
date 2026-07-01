import { useState, useRef, useEffect, useMemo } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Send, MessagesSquare, Loader2, User, Wrench, ChevronRight, ChevronLeft, PenLine } from 'lucide-react'
import { api } from './api'
import { useChatPersist } from './useChatPersist'
import { useChiefSlot } from './ChiefSlotContext'

// 主编对话气泡(讨论模式:复用 WriteChat 视觉规范,markdown 渲染 + 工具芯片)
function Bubble({ role, content, tools, streaming }) {
  const me = role === 'user'
  return (
    <div className={`flex gap-2.5 ${me ? 'flex-row-reverse' : ''}`}>
      <div className={`w-7 h-7 rounded-lg shrink-0 grid place-items-center ${me ? 'bg-brand text-white' : 'bg-soft text-brand'}`}>
        {me ? <User size={14} /> : <MessagesSquare size={14} />}
      </div>
      <div className={`max-w-[85%] ${me ? '' : 'flex-1 min-w-0'}`}>
        {!me && tools?.length > 0 && (
          <div className="flex flex-wrap gap-1 mb-1.5">
            {tools.map((t, i) => (
              <span key={i} className="inline-flex items-center gap-1 rounded-md bg-soft/70 border border-line px-1.5 py-0.5 text-[10.5px] text-faint">
                <Wrench size={9} className="text-brand" />
                {(t || '').replace(/^mcp_scribe3_/, '').replace(/^s3_/, '')}
              </span>
            ))}
          </div>
        )}
        <div className={`rounded-2xl px-3.5 py-2.5 text-[13.5px] leading-relaxed ${me ? 'bg-brand text-white' : 'bg-surface border border-line text-ink'}`}>
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
// phase(章阶段 tab)给定时,章的上下文/建议按阶段(大纲/节拍/草稿)调整。
function selContext(sel, phase) {
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
 * 折叠时只显示竖条;展开时显示头部 + 槽。槽内容由 WriteLayout 的 portal 填充。
 */
function WriteSlot({ collapsed, onToggle }) {
  const { setSlotEl } = useChiefSlot()

  if (collapsed) {
    return (
      <div className="h-full w-full bg-surface flex flex-col items-center py-3 gap-2">
        <button onClick={onToggle} title="展开主编写作"
          className="w-9 h-9 rounded-lg inline-flex items-center justify-center text-faint hover:bg-soft hover:text-ink cursor-pointer">
          <ChevronLeft size={18} />
        </button>
        <div className="w-9 h-9 rounded-lg grid place-items-center bg-soft text-brand"><PenLine size={16} /></div>
        <div className="text-[10px] text-faint [writing-mode:vertical-rl] mt-1 tracking-wide">主编</div>
      </div>
    )
  }

  return (
    <div className="h-full w-full bg-surface flex flex-col min-h-0">
      {/* 头部:标题 + 折叠 */}
      <div className="shrink-0 h-11 px-3 flex items-center gap-2 border-b border-line">
        <PenLine size={15} className="text-brand shrink-0" />
        <div className="flex flex-col min-w-0 leading-tight">
          <span className="text-[12px] font-semibold text-ink">主编 · 写作</span>
          <span className="text-[10.5px] text-faint truncate">提思路让主编写,或改选中段落</span>
        </div>
        <button onClick={onToggle} title="折叠主编写作"
          className="ml-auto w-7 h-7 rounded-lg inline-flex items-center justify-center text-faint hover:bg-soft hover:text-ink cursor-pointer">
          <ChevronRight size={16} />
        </button>
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
export function ChiefDock({ sel, chapterSel, collapsed, onToggle }) {
  const { chapterPhase } = useChiefSlot()
  if (chapterSel) {
    // 正文 tab(final)→ 写作槽(WriteLayout 的 WriteChat portal 进来,出草稿卡/护栏改写)。
    // 大纲/节拍/草稿 tab → 讨论 chat(据阶段调上下文)——右栏不再因切 tab 而消失。
    if (chapterPhase && chapterPhase !== 'final') {
      return <DiscussionDock sel={sel} phase={chapterPhase} collapsed={collapsed} onToggle={onToggle} />
    }
    return <WriteSlot collapsed={collapsed} onToggle={onToggle} />
  }
  return <DiscussionDock sel={sel} collapsed={collapsed} onToggle={onToggle} />
}

// 从选中节点取当前章 seq(章/场景节点),用于草稿阶段把 chapter 传给后端。
function selSeq(sel) {
  const node = sel?.node
  if (!node) return null
  if (node.type === 'chapter') return node.ref
  if (node.type === 'scene') return node.ref?.seq
  return null
}

function DiscussionDock({ sel, phase, collapsed, onToggle }) {
  const ctx = useMemo(() => selContext(sel, phase), [sel, phase])
  const seq = useMemo(() => selSeq(sel), [sel])
  const [msgs, setMsgs] = useState([])
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const endRef = useRef(null)
  const taRef = useRef(null)
  const esRef = useRef(null)

  // 主编对话历史持久化:按 work+当前选中节点/视图存,切节点/刷新可恢复
  const chatKey = sel?.mode === 'view'
    ? `${api.getWork()}:view:${sel.viewKey}`
    : `${api.getWork()}:node:${sel?.node?.id || 'none'}${phase ? ':' + phase : ''}`
  useChatPersist(chatKey, msgs, setMsgs)

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [msgs])
  // chatStream 返回 EventSource(.close),chatWrite 返回 AbortController(.abort);卸载时都收掉
  useEffect(() => () => { const h = esRef.current; h?.close?.(); h?.abort?.() }, [])

  useEffect(() => {
    const el = taRef.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = Math.min(el.scrollHeight, 128) + 'px'
  }, [input])

  const send = (text) => {
    const q = (text ?? input).trim()
    if (!q || busy) return
    const finalMsg = ctx.prefix + q
    setInput('')
    if (taRef.current) taRef.current.style.height = 'auto'
    setMsgs((m) => [...m, { role: 'user', content: q }, { role: 'assistant', content: '', tools: [] }])
    setBusy(true)
    const mut = (fn) => setMsgs((m) => { const c = [...m]; c[c.length - 1] = fn(c[c.length - 1]); return c })
    // 草稿阶段(有本章 seq)→ 走 /chat/write 并带 phase='draft'+chapter,
    // 使后端 _deduction_block 注入本章场景真相 + 各角色限知投影,主编据真相/投影写限知初稿。
    // proposal 围栏(草稿正文)与 delta(讨论)都收进同一气泡展示。
    if (phase === 'draft' && seq != null) {
      // proposal 围栏时序:proposal_start → proposal_chunk*(逐段散文文本) → proposal(全量,prose == 各 chunk 拼接)。
      // delta(讨论)与 proposal_chunk(草稿正文)拼进同一气泡 content,故不能整段替换 content。
      // 用「基线 base(围栏开始时的 content)+ 本条 proposal 累积 acc」归一:
      // chunk 逐段累加 acc→content=base+acc(干净流式预览);收尾 proposal 用 base+prose 归一
      // (围栏路径 prose==acc 不重复;纯 delta 兜底路径无 chunk、base 不变、prose 追加一次)。
      let propBase = ''
      let propAcc = ''
      let propOpen = false // 是否见过围栏开始(区分围栏路径 vs 纯 delta 兜底 proposal)
      esRef.current = api.chatWrite(finalMsg, {
        chapter: seq,
        phase: 'draft',
        onDelta: (d) => mut((l) => ({ ...l, content: l.content + d })),
        onTool: (name) => mut((l) => ({ ...l, tools: [...(l.tools || []), name] })),
        onProposalStart: () => { propOpen = true; propAcc = ''; mut((l) => { propBase = l.content; return l }) },
        onProposalChunk: (c) => { propAcc += (c?.text ?? c ?? ''); mut((l) => ({ ...l, content: propBase + propAcc })) },
        // 围栏路径:base 已记录、prose==propAcc→base+prose 不重复。
        // 兜底路径(无 proposal_start):propOpen=false,把 prose 追加到已有讨论文之后,不吞 delta。
        onProposal: (p) => {
          const prose = p?.prose ?? p?.text ?? propAcc
          mut((l) => ({ ...l, content: propOpen ? propBase + prose : l.content + prose }))
        },
        onDone: () => setBusy(false),
        onError: (err) => { mut((l) => ({ ...l, content: l.content + `\n\n_⚠ ${err}_` })); setBusy(false) },
      })
      return
    }
    // 非草稿:走 /chat/stream(绑当前书 + 注入该书设定圣经),不走 MCP 网关(网关连固定库会串到别的书)
    esRef.current = api.chatStream(finalMsg, {
      agentic: false,
      onDelta: (d) => mut((l) => ({ ...l, content: l.content + d })),
      onTool: (name) => mut((l) => ({ ...l, tools: [...(l.tools || []), name] })),
      onDone: () => setBusy(false),
      onError: (err) => { mut((l) => ({ ...l, content: l.content + `\n\n_⚠ ${err}_` })); setBusy(false) },
    })
  }

  if (collapsed) {
    return (
      <div className="h-full w-full bg-surface flex flex-col items-center py-3 gap-2">
        <button onClick={onToggle} title="展开主编对话"
          className="w-9 h-9 rounded-lg inline-flex items-center justify-center text-faint hover:bg-soft hover:text-ink cursor-pointer">
          <ChevronLeft size={18} />
        </button>
        <div className="w-9 h-9 rounded-lg grid place-items-center bg-soft text-brand"><MessagesSquare size={16} /></div>
        <div className="text-[10px] text-faint [writing-mode:vertical-rl] mt-1 tracking-wide">主编</div>
      </div>
    )
  }

  return (
    <div className="h-full w-full bg-surface flex flex-col min-h-0">
      {/* 头部:标题 + 上下文 + 折叠 */}
      <div className="shrink-0 h-11 px-3 flex items-center gap-2 border-b border-line">
        <MessagesSquare size={15} className="text-brand shrink-0" />
        <div className="flex flex-col min-w-0 leading-tight">
          <span className="text-[12px] font-semibold text-ink">主编</span>
          <span className="text-[10.5px] text-faint truncate">{ctx.label}</span>
        </div>
        <button onClick={onToggle} title="折叠主编对话"
          className="ml-auto w-7 h-7 rounded-lg inline-flex items-center justify-center text-faint hover:bg-soft hover:text-ink cursor-pointer">
          <ChevronRight size={16} />
        </button>
      </div>

      {/* 消息列表 */}
      <div className="flex-1 min-h-0 overflow-y-auto px-3 py-3 space-y-3">
        {msgs.length === 0 ? (
          <div className="pt-2">
            <div className="text-[12px] text-faint mb-2.5 leading-snug">就当前选中的内容与主编讨论。主编可联查书内实证(角色/伏笔/事件/设定)。</div>
            <div className="space-y-1.5">
              {ctx.suggests.map((s) => (
                <button key={s} onClick={() => send(s)}
                  className="w-full text-left rounded-lg border border-line bg-canvas hover:border-brand hover:bg-soft/40 px-2.5 py-1.5 text-[12px] text-ink transition-colors cursor-pointer">{s}</button>
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
        <div className="flex items-end gap-1.5 rounded-xl border border-line bg-canvas px-2.5 py-2 focus-within:border-brand transition-colors">
          <textarea
            ref={taRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            rows={1}
            placeholder="就当前内容问主编…(Enter 发送)"
            onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() } }}
            className="flex-1 resize-none bg-transparent text-[13px] text-ink outline-none max-h-32 leading-relaxed placeholder:text-faint"
          />
          <button
            onClick={() => send()}
            disabled={busy || !input.trim()}
            className="w-8 h-8 rounded-lg bg-brand text-white grid place-items-center disabled:opacity-40 disabled:cursor-default cursor-pointer hover:opacity-90 transition-opacity shrink-0"
          >
            {busy ? <Loader2 size={15} className="animate-spin" /> : <Send size={15} />}
          </button>
        </div>
      </div>
    </div>
  )
}
