import { useState, useRef, useEffect, useMemo } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Send, MessagesSquare, Loader2, User, Wrench, Square, PenLine, Paperclip, Mic, Check, X, AtSign } from 'lucide-react'
import { api } from './api'
import { useChatPersist, loadChat } from './useChatPersist'
import { useChiefSlot } from './ChiefSlotContext'
import { fallbackProposalText } from './lib/stageProposal'
import { focusTalk, focusChatKey, nextChatFocusKey } from './lib/focusTalk'
import { hermesRunInstructions, shouldUseHermesRun } from './lib/hermesRunIntent'
import { mergeThreadHistory, mutateLatestAssistantMessage, normalizeThreadMessages } from './lib/chiefThreadMessages'
import { displayToolName } from './lib/toolName'
import { scrollBehavior } from './lib/utils'
import {
  approvalExpiryFromError,
  approvalStatusFromDecision,
  patchApprovalInMessages,
  runContextFromError,
  useHermesRunRecovery,
} from './lib/hermesRunRecovery'
import { SelectionQuoteActions } from './ui/SelectionQuoteActions.jsx'
import { MaterialAtPicker } from './ui/MaterialAtPicker.jsx'
import { useMaterialAt } from './lib/useMaterialAt.js'
import { useDeduceSel } from './deduceContext'
import { useSelection } from './selectionContext'
import { useContextSnapshot } from './context/ContextSnapshotContext'
import { ContextInspector } from './context/ContextInspector'
import { PendingClaimsPanel } from './context/PendingClaimsPanel'
import { ThreadSwitcher } from './ThreadSwitcher'
import { showToast } from './ui/Toast.jsx'
import { Btn } from './ui.jsx'
import { notifyWorldWriteApproved } from './lib/codexLifecycle.js'

// P0b:早期摘要卡(折叠可展开)——近窗之外的更早讨论压缩在此;summary_error 红字如实示警。
function ThreadSummaryCard({ meta }) {
  const [open, setOpen] = useState(false)
  if (!meta) return null
  const err = (meta.summary_error || '').trim()
  const summ = (meta.summary || '').trim()
  if (!err && !summ) return null
  return (
    <div className="rounded-md bg-soft/50 px-2.5 py-2 text-f12 leading-snug">
      {err && (
        <div className="text-danger mb-1">早期摘要未更新(上次生成失败:{err})——以下为旧摘要。</div>
      )}
      {summ && (
        <button onClick={() => setOpen((v) => !v)} className="w-full text-left cursor-pointer">
          <span className="text-faint">【早期摘要】</span>
          <span className="text-ink">{open ? summ : summ.slice(0, 72) + (summ.length > 72 ? '…' : '')}</span>
          {summ.length > 72 && <span className="text-brand ml-1">{open ? '收起' : '展开'}</span>}
        </button>
      )}
    </div>
  )
}

// 焦点标签取话术:非线程模式与既有一致(focusTalk(选中总线 focus));
// 线程模式用快照焦点(无 origin 也能出话术),入口/视图型交回 selContext 兜底。
function threadFocusTalk(f, threadMode) {
  if (!threadMode) return focusTalk(f)
  if (!f || !f.id || f.type === 'entry' || f.type === 'view') return null
  return focusTalk(f)
}

// 主编对话气泡(讨论模式:复用 WriteChat 视觉规范,markdown 渲染 + 工具芯片)
function toolOutputPreview(output) {
  const text = typeof output === 'string' ? output : JSON.stringify(output)
  return text.length > 220 ? text.slice(0, 220) + '…' : text
}

// Task 13:焦点对象 → 展示名(label 优先,回退 id;中性/空 → 破折号)。run 卡片"发起时/当前焦点"用。
function focusLabel(f) {
  if (!f || typeof f !== 'object') return '—'
  return String(f.label || f.id || '—')
}

// Task 13:run 审批的"发起时上下文已过期"卡片。
// run_context_changed(voided)= 影响当前章/条目 → 原审批作废,须重新发起;
// run_context_stale = 无关的过期 run → 二次确认后带 approve_stale=true 放行。
function RunStaleCard({ ap, onApprovalDecision }) {
  const rc = ap.runContext
  if (!rc) return null
  return (
    <div data-testid="run-context-stale" className="mt-2 rounded-md border border-warn/30 bg-warn/5 px-2.5 py-2">
      <div className="flex items-center gap-1.5 text-f12 font-medium text-warn">
        <span data-testid="run-context-expired" className="inline-flex items-center rounded-lg bg-warn/15 px-1.5 py-0.5 text-meta">已过期</span>
        {rc.voided ? '发起时焦点已推进,原审批作废' : '发起时焦点已变,但与当前焦点无关'}
      </div>
      <div className="mt-1 grid grid-cols-1 gap-0.5 text-meta text-faint">
        <div>发起时焦点:<span data-testid="run-origin-focus" className="text-ink">{focusLabel(rc.originFocus)}</span></div>
        <div>当前焦点:<span data-testid="run-current-focus" className="text-ink">{focusLabel(rc.currentFocus)}</span></div>
      </div>
      {rc.voided ? (
        <div data-testid="run-context-voided" className="mt-1.5 text-meta text-danger">已作废,请就当前焦点重新发起该任务。</div>
      ) : (
        <button type="button" data-testid="run-approve-stale" onClick={() => onApprovalDecision?.(ap, 'approve', { approveStale: true })}
          className="mt-1.5 inline-flex h-7 items-center gap-1 rounded-md bg-warn/10 px-2.5 text-meta font-medium text-warn hover:bg-warn/15 cursor-pointer">
          仍要批准(忽略过期)
        </button>
      )}
    </div>
  )
}

function Bubble({ role, content, tools, toolOutputs, approvals, streaming, onApprovalDecision, focus, context_revision, writeEffects, chapterSeq }) {
  const me = role === 'user'
  // Task 6:带焦点标签的消息打上 data-context-revision(每轮焦点=快照 revision 的印记)。
  const ctxRev = focus && context_revision != null ? String(context_revision) : undefined
  // 存/引入/聊：只在划选浮窗(SelectionQuoteActions)，不在每条消息头挂冗余「存」
  // 无气泡:主编靠左 / 你靠右,色条+底色+分割线区分,省掉头像与圆角底
  return (
    <div
      data-context-revision={ctxRev}
      data-testid="chat-turn"
      data-role={me ? 'user' : 'assistant'}
      className={`flex min-w-0 border-b border-line/70 py-2 last:border-b-0 ${me ? 'justify-end' : 'justify-start'}`}
    >
      <div
        className={`min-w-0 max-w-[94%] text-f13 leading-relaxed ${
          me
            ? 'border-r-2 border-brand/50 pr-2 bg-brand/[0.04] pl-2 py-1'
            : 'border-l-2 border-line pl-2 pr-1 py-1'
        }`}
      >
        <div className={`flex items-center gap-1.5 mb-1 ${me ? 'justify-end text-brand' : 'justify-start text-faint'}`}>
          {me ? (
            <>
              <span className="text-meta font-medium whitespace-nowrap">你</span>
              <User size={12} className="shrink-0" />
            </>
          ) : (
            <>
              <MessagesSquare size={12} className="shrink-0 text-brand" />
              <span className="text-meta font-medium whitespace-nowrap">主编</span>
            </>
          )}
        </div>
        {!me && tools?.length > 0 && (
          <div className="flex flex-wrap gap-1 mb-1.5">
            {tools.map((t, i) => (
              <span key={i} className="inline-flex items-center gap-1 rounded-lg bg-soft/80 px-1.5 py-0.5 text-meta text-faint">
                <Wrench size={9} className="text-brand" />
                {displayToolName(t)}
              </span>
            ))}
          </div>
        )}
        <SelectionQuoteActions
          scopeLabel={me ? '你的消息' : '主编回复'}
          chapterSeq={chapterSeq}
          originLabel="主编会话"
          disabled={streaming}
          className="min-w-0 text-left text-ink"
        >
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
        </SelectionQuoteActions>
        {!me && approvals?.length > 0 && (
          <div className="mt-2 space-y-2">
            {approvals.map((ap, apIdx) => {
              const done = ap.status === 'approved' || ap.status === 'denied'
              // Hermes MCP elicitation 常不带 approval_id;用 message+idx 防 React 同 key 刷屏
              const apKey = `${ap.run_id || ''}:${ap.approval_id || ap.message || ''}:${apIdx}`
              return (
                <div key={apKey} className="border-l-2 border-brand/50 pl-2.5 py-1">
                  <div className="text-f12 font-medium text-ink">Hermes 请求审批</div>
                  <div className="mt-0.5 text-f12 text-faint whitespace-pre-wrap">{ap.message || '需要你确认后继续'}</div>
                  <div className="mt-2 flex items-center gap-2">
                    {ap.status === 'approved' ? (
                      <span className="text-f12 text-ok">已批准</span>
                    ) : ap.status === 'denied' ? (
                      <span className="text-f12 text-danger">已拒绝</span>
                    ) : ap.status === 'expired' ? (
                      <span className="text-f12 text-warn">审批已过期，请重新发起</span>
                    ) : ap.status === 'submitting' ? (
                      <span className="text-f12 text-faint">提交中…</span>
                    ) : ap.status === 'error' ? (
                      <span className="text-f12 text-danger">提交失败</span>
                    ) : ap.runContext ? null : (
                      <>
                        <button type="button" data-testid="run-approve" aria-label="批准" onClick={() => onApprovalDecision?.(ap, 'approve')}
                          className="inline-flex h-7 items-center gap-1 rounded-md bg-brand px-2.5 text-f12 font-medium text-brandfg cursor-pointer">
                          <Check size={12} />批准
                        </button>
                        <button type="button" data-testid="run-deny" aria-label="拒绝" onClick={() => onApprovalDecision?.(ap, 'deny')}
                          className="inline-flex h-7 items-center gap-1 rounded-md bg-soft px-2.5 text-f12 font-medium text-ink hover:bg-soft/80 cursor-pointer">
                          <X size={12} />拒绝
                        </button>
                      </>
                    )}
                    {done && ap.decision && <span className="text-meta text-faint">{ap.decision}</span>}
                  </div>
                  <RunStaleCard ap={ap} onApprovalDecision={onApprovalDecision} />
                </div>
              )
            })}
          </div>
        )}
        {!me && writeEffects?.length > 0 && (
          <div data-testid="run-write-effects" className="mt-2 border-l-2 border-brand/40 pl-2.5 py-1">
            <div className="text-f12 font-medium text-ink">写入影响</div>
            <div className="mt-0.5 text-meta text-faint">
              {writeEffects.map((e, i) => (
                <div key={i}>{e.kind || '写入'}{e.context_revision != null ? ` · rev ${e.context_revision}` : ''}{e.stale_confirmed ? ' · 过期放行' : ''}</div>
              ))}
            </div>
          </div>
        )}
        {!me && toolOutputs?.length > 0 && (
          <div className="mt-2 space-y-1.5">
            {toolOutputs.map((out, i) => (
              <div key={out.call_id || i} className="border-l-2 border-line pl-2.5 py-1">
                <div className="text-f12 font-medium text-ink">工具返回</div>
                <div className="mt-0.5 whitespace-pre-wrap break-words text-meta leading-snug text-faint">
                  {toolOutputPreview(out.output)}
                </div>
              </div>
            ))}
          </div>
        )}
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
    <div data-testid="chief-chat-shell" className="h-full w-full min-w-0 bg-surface flex flex-col min-h-0 overflow-hidden">
      {/* 头部:标题 · nowrap 防窄栏逐字竖排 */}
      <div className="shrink-0 px-3.5 py-3 flex items-center gap-2 border-b border-line/60 min-w-0 overflow-hidden bg-surface/95 backdrop-blur-sm">
        <PenLine size={15} className="text-brand shrink-0" />
        <div className="flex flex-col min-w-0 flex-1 leading-tight overflow-hidden">
          <span data-testid="chief-chat-title" className="text-f13 font-semibold tracking-tight text-ink whitespace-nowrap truncate">主编上下文</span>
          <span className="text-meta text-faint truncate">提思路让主编写,或改选中段落</span>
        </div>
      </div>
      {/* 写作 chat 槽:WriteLayout 的 WriteChat 经 portal 进来填充此处 */}
      <div ref={setSlotEl} className="flex-1 min-h-0" />
    </div>
  )
}

/**
 * 右主编栏(常驻)。
 * - 非章节点:讨论模式。把当前选中节点/视图作为上下文,走 /chat/stream(纯对话)。
 *   注:agentic 联查(/chat/agentic-stream)当前禁用(防跨书串库,见 send() 的 agentic:false);
 *   要联查书内实证请到章内写作槽,主编在那挂 s3_ 工具。
 * - 章/场景节点:写作模式。渲染 WriteSlot,WriteLayout 的 WriteChat 经 portal 落进来。
 * 波B Step3:右栏常驻;章=写作槽 / 非章=讨论 chat。无双 chat,无嵌套第4列。
 */
// 主编主动化 T5·时机A:进章开场白——有 decision 级且该维「本章未开过口、未静音」才说,
// 只说一条(防烦协议:每章每维最多一次;显示即记账,刷新不重复)。
// 每条自带依据(pulse message 本身就是"因为…"),按钮:聊(seed 预填)/静音此维。
function UsageChip() {
  // H-10 全系统预算:日帽(app+MCP 共享 SQLite 台账)+ 分渠道 token 证据。
  // 官方直连台账与 trace 聚合口径可能覆盖同一次调用，必须并列展示、绝不相加。
  // fail-soft:接口挂/后端旧版无此端点 → 不渲染,绝不拖垮主编区。
  const [u, setU] = useState(null)
  useEffect(() => {
    let alive = true
    const load = () => { api.aiUsage?.(7).then((r) => { if (alive) setU(r) }).catch(() => {}) }
    load()
    const t = setInterval(load, 300000)
    return () => { alive = false; clearInterval(t) }
  }, [])
  if (!u?.cap) return null
  const traceTok = u.tokens?.days?.[0]?.total?.total_tokens ?? 0
  const hasProviderUsage = u.provider_usage != null
  const providerTok = (u.provider_usage?.days?.[0]?.groups || [])
    .reduce((sum, group) => sum + (Number(group?.total_tokens) || 0), 0)
  const formatTok = (value) => value >= 1000 ? `${Math.round(value / 1000)}k` : String(value)
  const channelLabel = [
    hasProviderUsage ? `官方直连 ${formatTok(providerTok)} tok` : null,
    `trace ${formatTok(traceTok)} tok`,
  ].filter(Boolean).join(' · ')
  const scopeLabel = u.cap.scope === 'shared' ? 'app+MCP 共享台账' : '台账故障,进程内计数(下限)'
  const unlimited = u.cap.unlimited === true
  const usageLabel = unlimited
    ? `今日已用 ${u.cap.used_today} 发 · 不限次数`
    : `${u.cap.used_today}/${u.cap.cap} 发`
return (
    <span
      data-testid="chief-usage-chip"
      className="ml-auto max-w-[42%] shrink-0 truncate text-meta text-faint tabular-nums whitespace-nowrap"
      title={`LLM ${unlimited ? '用量' : '日帽'}:${usageLabel}(${scopeLabel});${hasProviderUsage ? `官方直连 ${providerTok} token；` : ''}trace ${traceTok} token${hasProviderUsage ? '；两个渠道可能重叠，不相加' : ''}`}
    >
      {usageLabel} · {channelLabel}
    </span>
  )
}


function ProactiveGreeting({ seq }) {
  const [item, setItem] = useState(null)
  useEffect(() => {
    if (seq == null) { setItem(null); return }
    let dead = false
    api.chapterPulse(seq).then((p) => {
      if (dead) return
      const w = api.getWork()
      for (const d of p.dimensions || []) {
        if (localStorage.getItem(`s3.pulse.mute.${w}.${d.dimension}`) === '1') continue   // R2-10:键含 work(此前跨书全局静音)
        if (localStorage.getItem(`s3.spoke.${w}.${seq}.${d.dimension}`) === '1') continue
        const hit = (d.items || []).find((it) => it.severity === 'decision')
        if (hit) {
          localStorage.setItem(`s3.spoke.${w}.${seq}.${d.dimension}`, '1')   // 显示即记账
          setItem({ dim: d.dimension, ...hit })
          return
        }
      }
      setItem(null)
    }).catch(() => setItem(null))
    return () => { dead = true }
  }, [seq])
  if (!item) return null
  return (
    <div className="mx-3 mt-2 px-2.5 py-2 rounded-lg border border-warn/40 bg-warn/5 text-f12 leading-snug">
      <span className="text-ink">进章提醒:{item.message}</span>
      <div className="mt-1 flex items-center gap-3">
        {item.action?.kind === 'chat' && (
          <button onClick={() => { try { sessionStorage.setItem('s3.chief.seed', item.action.payload) } catch { /* */ }; try { window.dispatchEvent(new CustomEvent('s3-chief-seed', { detail: item.action.payload })) } catch { /* */ }; setItem(null) }}
            className="text-meta text-brand hover:underline cursor-pointer">聊聊 →</button>
        )}
        <button onClick={() => { localStorage.setItem(`s3.pulse.mute.${api.getWork()}.${item.dim}`, '1'); setItem(null) }}
          className="text-meta text-faint hover:text-ink cursor-pointer">静音此维</button>
      </div>
    </div>
  )
}

export function ChiefDock({ sel, chapterSel, lastSeq }) {
  const { chapterPhase } = useChiefSlot()
  const seq = selSeq(sel)
  if (chapterSel) {
    // 正文 tab(final)→ 写作槽(WriteLayout 的 WriteChat portal 进来,出草稿卡/护栏改写)。
    // 大纲/节拍/草稿 tab → 讨论 chat(据阶段调上下文)——右栏不再因切 tab 而消失。
    if (chapterPhase && chapterPhase !== 'final') {
      return (<div className="h-full flex flex-col min-h-0">
        <ProactiveGreeting seq={seq} />
        <div className="flex-1 min-h-0"><DiscussionDock sel={sel} phase={chapterPhase} /></div>
      </div>)
    }
    return (<div className="h-full flex flex-col min-h-0">
      <ProactiveGreeting seq={seq} />
      {/* P0a:正文写作槽也可换会话(busy 状态在 WriteChat 内部拿不到,切换保护由
          bind 发送时捕获 + _ChatTurnLog 部分留痕兜底,不弹确认) */}
      <div className="shrink-0 px-3 py-1 border-b border-line/60 flex justify-end"><ThreadSwitcher /></div>
      <div className="flex-1 min-h-0"><WriteSlot /></div>
    </div>)
  }
  return <DiscussionDock sel={sel} ctxSeq={lastSeq} />
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
// 大纲/节拍属规划期→'plan';演绎传真实 phase(后端注入场景真相块,投影同源派生的
// 物理保证,断头修复#5);草稿→'draft'。
const WRITE_PHASE = { outline: 'plan', beats: 'plan', deduce: 'deduce', draft: 'draft' }

function DiscussionDock({ sel, phase, ctxSeq }) {
  const seq = useMemo(() => selSeq(sel), [sel])
  const { setStageProposal, chiefIntent, setChiefIntent } = useChiefSlot()
  // 演绎阶段:读左树/中区共享的当前演绎目标('truth' 或 character_id),生成完按它发布 target。
  const { selected: deduceSel } = useDeduceSel()
  const deduceName = deduceSel === 'truth' ? '场景真相' : String(deduceSel || '').replace(/^role:/, '')
  // 块三:通用选中总线 focus 优先——任何视图的显式选中(图谱节点/时间线事件/伏笔行/母题行/帧行…)
  // 立即改写主编标题与话术;focus 为空/sel 镜像/演绎目标 → 回退既有视图级/节点级/阶段话术。
  const { focus } = useSelection()
  const { snapshot } = useContextSnapshot()
  // Task 6:线程模式——有快照(thread_id)且 api.threadMessages 可用才启用「一 work 一连续线程」;
  // 否则完全走既有 chatKey 逻辑(旧测试无 snapshot/无 threadMessages → 行为一字不变)。
  const threadId = snapshot?.thread_id || null
  const threadMode = !!(threadId && typeof api.threadMessages === 'function')
  // 上下文标签:线程模式跟随快照焦点(切焦点即改标签但不换线程);否则跟随选中总线 focus。
  const effectiveFocus = threadMode ? (snapshot?.focus || focus) : focus
  const ctx = useMemo(
    () => threadFocusTalk(effectiveFocus, threadMode) || selContext(sel, phase, phase === 'deduce' ? deduceName : undefined),
    [effectiveFocus, threadMode, sel, phase, deduceName])
  const [msgs, setMsgs] = useState([])
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const endRef = useRef(null)
  const taRef = useRef(null)
  const materialAt = useMaterialAt({ input, setInput, taRef })
  const esRef = useRef(null)
  // chat/write 已到达但尚未正式收尾的草稿。作者停止生成时，不能让这段可见文本
  // 随 AbortController 一起消失；由当前阶段的 proposal 通道交给中区明确决定是否采用。
  const partialProposalRef = useRef(null)
  const activeRunIdsRef = useRef(new Set())
  const proposalTsRef = useRef(0) // 递增计数器:区分「同一 prose 再次生成」以便重新提示
  // 主编主动化 T4/T5(审查 P0-2/P2-12):seed 双轨——挂载时消费 sessionStorage pending
  // (点按钮时监听者可能未挂载),事件给已挂载者;预填=追加不整替(不吞作者半句)。
  // 世界写种子(s3_* / 需我审批):自动发送——否则「让主编写入」只填框不提交,作者/e2e 点了等于没点。
  const sendRef = useRef((/** @type {string|undefined} */ _t) => {})
  const seedIn = (v) => {
    const text = String(v ?? '')
    if (!text.trim()) return
    setInput((prev) => (prev ? prev + '\n' : '') + text)
    taRef.current?.focus()
    const auto = /s3_[a-z_]+|需我审批|写入落库|提交写入提案/.test(text)
    if (auto) {
      // 下一帧再发:等 input 提交路径与 focus 就绪;send 读显式 text 不依赖 state
      setTimeout(() => sendRef.current(text), 80)
    }
  }
  useEffect(() => {
    try {
      const pending = sessionStorage.getItem('s3.chief.seed')
      if (pending) { sessionStorage.removeItem('s3.chief.seed'); seedIn(pending) }
    } catch { /* */ }
    const on = (e) => { if (e?.detail) { try { sessionStorage.removeItem('s3.chief.seed') } catch { /* */ }; seedIn(e.detail) } }
    window.addEventListener('s3-chief-seed', on)
    return () => window.removeEventListener('s3-chief-seed', on)
  }, [])

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
  // 线程模式:持久键 = work:editorial:thread_id(不含焦点 → 切焦点不换键、不重载);
  // useChatPersist 降权为草稿缓存(不 load-replace 消息——消息由服务端 threadMessages 供给)。
  const threadKey = threadMode ? `${snapshot.work}:editorial:${threadId}` : null
  const persistKey = threadMode ? threadKey : chatKey
  useChatPersist(persistKey, msgs, setMsgs, threadMode ? { mode: 'thread' } : undefined)
  useHermesRunRecovery({ msgs, setMsgs, setBusy, activeRunIdsRef })

  // 线程模式:一次性从服务端载入线程历史(键为 threadId、不含焦点 → 焦点切换不触发重载)。
  // I-2:ref 仅在**成功**后置位(失败不置 → 保持可重试);失败置错误态、log,并允许
  // 依赖变化/用户点重试(reloadTick)再拉,不再"一次抖动即历史凭空消失"。
  // I-3:失败时读回本地 draft 缓存兜底(断网未同步消息的显示回填),让草稿写入不再是死缓存。
  const loadedThreadRef = useRef(null)
  const [threadLoadError, setThreadLoadError] = useState(false)
  const [reloadTick, setReloadTick] = useState(0)
  // P0b:懒加载近窗(30 条)+「载入更早」游标 + 线程摘要卡数据
  const RECENT_N = 30
  const [earlier, setEarlier] = useState({ cursor: null, hasMore: false })
  const [threadMeta, setThreadMeta] = useState(null)
  useEffect(() => {
    if (!threadMode) { loadedThreadRef.current = null; return undefined }
    if (loadedThreadRef.current === threadId) return undefined
    let dead = false
    api.threadMessages(threadId, { limit: RECENT_N })
      .then((rows) => {
        if (dead) return
        loadedThreadRef.current = threadId   // 仅成功后置位:失败不置 → 下次可重试
        setThreadLoadError(false)
        setMsgs((current) => mergeThreadHistory(normalizeThreadMessages(rows), current))
        setEarlier({ cursor: rows[0]?.ts || null, hasMore: rows.length === RECENT_N })
        // 摘要卡数据(summary/summary_error);旧测试精简 api 无 threads → 跳过(行为回旧版)
        if (typeof api.threads === 'function') {
          api.threads()
            .then((d) => { if (!dead) setThreadMeta((d.threads || []).find((t) => t.thread_id === threadId) || null) })
            .catch(() => { if (!dead) setThreadMeta(null) })
        }
      })
      .catch((e) => {
        if (dead) return
        // 失败不吞:至少 log + 置错误态供重试;不清空已有显示。
        console.warn('主编线程历史载入失败,可重试:', e)
        setThreadLoadError(true)
        // 断网兜底:本地有 draft 缓存且当前空 → 用草稿回填,避免历史凭空空白(I-3)。
        const draft = loadChat('draft:' + threadKey)
        if (draft.length) setMsgs((prev) => (prev.length === 0 ? draft : prev))
      })
    return () => { dead = true }
  }, [threadMode, threadId, threadKey, reloadTick])
  const retryThreadLoad = () => setReloadTick((t) => t + 1)

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: scrollBehavior() }) }, [msgs])
  // 中止在途流:chatStream 返回 EventSource(.close),chatWrite 返回 AbortController(.abort),两者都收。
  const stop = () => {
    const recoverPartial = partialProposalRef.current
    partialProposalRef.current = null
    recoverPartial?.()
    const h = esRef.current
    h?.close?.()
    h?.abort?.()
    esRef.current = null
    activeRunIdsRef.current.clear()
    setBusy(false)
  }
  // chatStream 返回 EventSource(.close),chatWrite 返回 AbortController(.abort);卸载时都收掉
  useEffect(() => () => { const h = esRef.current; h?.close?.(); h?.abort?.(); activeRunIdsRef.current.clear() }, [])
  // 切上下文(persistKey 变=切章/切阶段/切节点/切视图/切线程)→ 中止在途流,防旧流 delta 污染新历史(串台)。
  // 只在 persistKey 真的变了时触发,不误伤正常发送;线程模式 persistKey=threadKey(不含焦点)→ 切焦点不断流。
  useEffect(() => { const h = esRef.current; if (h) { h.close?.(); h.abort?.(); esRef.current = null; activeRunIdsRef.current.clear(); setBusy(false) } }, [persistKey])

  useEffect(() => {
    const el = taRef.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = Math.min(el.scrollHeight, 128) + 'px'
  }, [input])

  const patchApproval = (approval, patch) => {
    setMsgs((m) => patchApprovalInMessages(m, approval, patch))
  }

  const handleApprovalDecision = async (approval, decision, { approveStale = false } = {}) => {
    patchApproval(approval, { status: 'submitting' })
    try {
      // Task 13:approve_stale 二次确认时带上当前快照上下文(后端仍以库内 live 快照为准)。
      const body = { approval_id: approval.approval_id, decision }
      if (approveStale) {
        body.approve_stale = true
        body.context_session_id = snapshot?.session_id ?? null
        body.context_revision = snapshot?.revision ?? null
      }
      await api.aiRunApproval(approval.run_id, body)
      patchApproval(approval, { status: decision === 'approve' ? 'approved' : 'denied', decision, runContext: null })
      // 批准落库后通知设定详情轮询:删除/归档对象消失再退回分类
      if (decision === 'approve') {
        try {
          notifyWorldWriteApproved({
            decision,
            message: approval?.message || '',
            run_id: approval?.run_id,
          })
        } catch { /* */ }
      }
    } catch (e) {
      // Task 13:409 run_context_changed/stale → 展示"发起时/当前焦点 + 已过期"卡片,不当作提交失败。
      const expiry = approvalExpiryFromError(e)
      const rc = runContextFromError(e)
      if (expiry) {
        patchApproval(approval, { status: 'expired', error: expiry, runContext: null })
      } else if (rc) {
        patchApproval(approval, { status: 'pending', runContext: rc })
      } else {
        patchApproval(approval, { status: 'error', error: e?.body?.detail || e?.message || '提交失败' })
      }
    }
  }

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
    // 见上方 seedIn auto-send
    // 主编主动化 T8:「#想法 」→ 想法收件箱
    if (q.startsWith('#想法')) {
      const idea = q.replace(/^#想法\s*/, '')
      if (!idea) return
      setInput('')
      setMsgs((m) => [...m, { role: 'user', content: q }, { role: 'assistant', content: '', tools: [] }])
      api.addIdea(idea).then((r) => {
        const tail = r.status === 'unclear' ? `\n\n${r.question}`
          : r.status === 'pending_approval' ? '\n\n(动设定/改旧章级——已挂收件箱等你批)'
          : r.target_seq ? `\n\n已落到第 ${r.target_seq} 章的作者意图。` : ''
        setMsgs((m) => { const c = [...m]; c[c.length - 1] = { role: 'assistant', content: `收到想法(${r.kind}):${r.note || ''}${tail}` }; return c })
      }).catch((e) => setMsgs((m) => { const c = [...m]; c[c.length - 1] = { role: 'assistant', content: `想法登记失败:${e?.body?.detail || e?.message || ''}` }; return c }))
      return
    }
    const finalMsg = ctx.prefix + q
    setInput('')
    if (taRef.current) taRef.current.style.height = 'auto'
    // Task 6:线程模式捕获本轮 focusAtSend + context 绑定(随请求体带上,并标注气泡)。
    const bind = threadMode ? {
      thread_id: threadId,
      context_session_id: snapshot?.session_id ?? null,
      context_revision: snapshot?.revision ?? null,
      context_hash: snapshot?.context_hash ?? null,
      focus: effectiveFocus || null,
    } : null
    setMsgs((m) => [...m,
      { role: 'user', content: q, focus: bind?.focus || null, context_revision: bind?.context_revision ?? null },
      { role: 'assistant', content: '', tools: [] }])
    setBusy(true)
    const mut = (fn) => setMsgs((messages) => mutateLatestAssistantMessage(messages, fn))
    // 世界正典写入虽可从某一章的讨论槽发起，却不是该章的受限演绎 Run。
    // 只有 deduce/deduce_preview 有已注册的章节 profile；把 outline/beats/draft 的
    // 映射值(plan/draft)带入 run_scope 会被后端 fail-closed 为未知阶段，导致角色、
    // 设定等作者明确授权的作品级写入根本无法送达审批。作品级写入必须走全写 profile。
    const worldWriteRun = shouldUseHermesRun(q)
    const runPhase = worldWriteRun ? '' : (seq != null && Object.prototype.hasOwnProperty.call(WRITE_PHASE, phase) ? WRITE_PHASE[phase] : (phase || ''))
    const runFocalizer = phase === 'deduce' && deduceSel !== 'truth' ? deduceSel : ''
    if (worldWriteRun) {
      esRef.current = api.runWrite(finalMsg, {
        chapter: seq ?? ctxSeq,
        phase: runPhase,
        focalizer: runFocalizer,
        context: bind,   // Task 13:线程模式带发起时上下文(会话/版本)→ 后端快照 origin focus 供审批重校验
        instructions: hermesRunInstructions({ chapter: seq ?? ctxSeq, phase: runPhase, focalizer: runFocalizer }),
        onRun: (run) => {
          const runId = run?.run_id || run?.id
          if (runId) activeRunIdsRef.current.add(runId)
          mut((l) => ({ ...l, run_id: l.run_id || runId, runStatus: run?.status || l.runStatus }))
        },
        onDelta: (d) => mut((l) => ({ ...l, content: l.content + d })),
        onTool: (name) => mut((l) => ({ ...l, tools: [...(l.tools || []), name] })),
        onToolOutput: (output, call_id) => mut((l) => ({ ...l, toolOutputs: [...(l.toolOutputs || []), { output, call_id }] })),
        onApproval: (approval) => {
          const runId = approval?.run_id
          if (runId) activeRunIdsRef.current.add(runId)
          mut((l) => {
            const nextApproval = { ...approval, status: 'pending' }
            const duplicate = (l.approvals || []).some((item) =>
              item?.run_id === nextApproval.run_id
              && item?.approval_id === nextApproval.approval_id)
            return {
              ...l,
              run_id: l.run_id || runId,
              approvals: duplicate ? (l.approvals || []) : [...(l.approvals || []), nextApproval],
            }
          })
        },
        onApprovalResolved: (approval) => {
          const status = approvalStatusFromDecision(approval?.decision)
          patchApproval(approval, { ...approval, status })
        },
        onDone: () => { activeRunIdsRef.current.clear(); setBusy(false) },
        onError: (err) => { activeRunIdsRef.current.clear(); mut((l) => ({ ...l, content: l.content + `\n\n_出错:${err}_` })); setBusy(false) },
      })
      return
    }
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
      let partialRecovered = false
      const recoverPartialProposal = () => {
        if (partialRecovered) return
        partialRecovered = true
        const fallback = fallbackProposalText({ gotProposal, propOpen, propAcc, turnText })
        if (fallback != null) publish(fallback)
      }
      partialProposalRef.current = recoverPartialProposal
      esRef.current = api.chatWrite(finalMsg, {
        chapter: seq,
        phase: WRITE_PHASE[phase],
        focalizer: phase === 'deduce' && deduceSel !== 'truth' ? deduceSel : '',
        context: bind,   // Task 6:线程绑定/焦点标签随请求体带上(非线程模式为 null,后端忽略)
        onDelta: (d) => { turnText += d; mut((l) => ({ ...l, content: l.content + d })) },
        onTool: (name) => mut((l) => ({ ...l, tools: [...(l.tools || []), name] })),
        onToolOutput: (output, call_id) => mut((l) => ({ ...l, toolOutputs: [...(l.toolOutputs || []), { output, call_id }] })),
        onApproval: (approval) => mut((l) => ({ ...l, approvals: [...(l.approvals || []), { ...approval, status: 'pending' }] })),
        onApprovalResolved: (approval) => {
          const status = approvalStatusFromDecision(approval?.decision)
          patchApproval(approval, { ...approval, status })
        },
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
          recoverPartialProposal()
          if (partialProposalRef.current === recoverPartialProposal) partialProposalRef.current = null
        },
        onError: (err) => {
          recoverPartialProposal()
          if (partialProposalRef.current === recoverPartialProposal) partialProposalRef.current = null
          mut((l) => ({ ...l, content: l.content + `\n\n_出错:${err}_` }))
          setBusy(false)
        },
      })
      return
    }
    // 非章前置阶段(素材/视图等):走 /chat/stream(绑当前书 + 注入该书设定圣经),不走 MCP 网关(网关连固定库会串到别的书)
    esRef.current = api.chatStream(finalMsg, {
      agentic: false, seq: seq ?? ctxSeq,   // 审查 P0-1:非章上下文用最近章记忆,时机C 不死线
      thread: threadMode ? threadId : undefined,   // P0a:消息落当前选中会话(非线程模式不传=旧行为)
      onDelta: (d) => mut((l) => ({ ...l, content: l.content + d })),
      onTool: (name) => mut((l) => ({ ...l, tools: [...(l.tools || []), name] })),
      onToolOutput: (output, call_id) => mut((l) => ({ ...l, toolOutputs: [...(l.toolOutputs || []), { output, call_id }] })),
      onApproval: (approval) => mut((l) => ({ ...l, approvals: [...(l.approvals || []), { ...approval, status: 'pending' }] })),
      onApprovalResolved: (approval) => {
        const status = approvalStatusFromDecision(approval?.decision)
        patchApproval(approval, { ...approval, status })
      },
      onDone: () => setBusy(false),
      onError: (err) => { mut((l) => ({ ...l, content: l.content + `\n\n_出错:${err}_` })); setBusy(false) },
    })
  }
  sendRef.current = send

  return (
    <div data-testid="chief-chat-shell" className="h-full w-full min-w-0 bg-surface flex flex-col min-h-0 overflow-hidden">
      {/* 头部:标题 + 上下文(折叠由外层 resizable Panel 负责,此处不再自带折叠 UI)
          min-w-0 + nowrap/truncate:窄栏时禁止「主编上下文」逐字折成竖排 */}
      <div className="shrink-0 px-3.5 py-3 flex items-center gap-2 border-b border-line/60 min-w-0 overflow-hidden bg-surface/95 backdrop-blur-sm">
        <MessagesSquare size={15} className="text-brand shrink-0" />
        <div className="flex flex-col min-w-0 flex-1 leading-tight overflow-hidden">
          <span data-testid="chief-chat-title" className="text-f13 font-semibold tracking-tight text-ink whitespace-nowrap truncate">主编上下文</span>
          <span className="text-meta text-faint truncate" data-testid="chief-ctx">{ctx.label}</span>
        </div>
        {/* P0a:会话下拉(历史/新建/切换/管理)——自门控,非线程模式渲染 null */}
        <div className="shrink-0"><ThreadSwitcher busy={busy} /></div>
        <UsageChip />
      </div>

      {/* Task 14:上下文检查器 —— 主编到底看到了什么、为什么选/弃某条记忆(可折叠,常显第1层) */}
      <ContextInspector />
      {/* 待审正典揭示:作者面 list+approve/reject → /memory/pending-claims */}
      <PendingClaimsPanel />

      {/* 消息列表 */}
      <div data-testid="chief-chat-messages" className="flex-1 min-h-0 overflow-y-auto px-3 py-2 bg-canvas/50">
        {/* P0b:载入更早(分页游标)+ 早期摘要卡(折叠) */}
        {threadMode && earlier.hasMore && (
          <button
            onClick={() => {
              api.threadMessages(threadId, { limit: RECENT_N, before: earlier.cursor })
                .then((rows) => {
                  setMsgs((prev) => [...normalizeThreadMessages(rows), ...prev])
                  setEarlier({ cursor: rows[0]?.ts || earlier.cursor, hasMore: rows.length === RECENT_N })
                })
                .catch((e) => showToast(`载入更早失败:${e?.body?.detail || e?.message || e}`, { tone: 'danger' }))
            }}
            className="w-full text-center text-f12 text-brand hover:underline cursor-pointer py-1">
            载入更早…
          </button>
        )}
        {threadMode && <ThreadSummaryCard meta={threadMeta} />}
        {threadLoadError && (
          <div data-testid="chief-thread-load-error" className="rounded-md border border-warn/30 bg-warn/5 px-2.5 py-2 text-f12 leading-snug text-ink flex items-center gap-2 mb-2">
            <span className="flex-1">线程历史加载失败{msgs.length ? '(显示本地缓存)' : ''},可重试。</span>
            <button type="button" data-testid="chief-thread-retry" onClick={retryThreadLoad}
              className="shrink-0 text-meta text-brand hover:underline cursor-pointer">重试</button>
          </div>
        )}
        {msgs.length === 0 ? (
          <div className="pt-1 space-y-2">
            {/* 空态按会话类型分文案(作者语义:新建=界面清洁不是失忆):
                有 parent=延续会话(近窗+摘要都带着);无 parent=手动全新会话 */}
            {threadMode && threadMeta && (
              threadMeta.parent_thread_id ? (
                <div className="rounded-md bg-soft/40 px-3 py-2 text-f12 text-faint leading-snug">已延续上一会话的上下文(近窗对话+早期摘要)——主编记得之前聊的,这个新会话只是界面归档分组。</div>
              ) : (
                <div className="rounded-md bg-soft/40 px-3 py-2 text-f12 text-faint leading-snug">全新会话,不带对话历史——主编的长期记忆(设定圣经/伏笔/正典)仍然在。</div>
              )
            )}
            <div className="rounded-md bg-soft/40 px-3 py-2 text-f12 text-faint leading-snug">就当前选中的内容与主编讨论(纯对话)。要主编联查书内实证(角色/伏笔/事件/设定),请到章内写作槽——主编在那挂书内工具。</div>
            <div className="space-y-1.5">
              {ctx.suggests.map((s) => (
                <button key={s} onClick={() => send(s)}
                  className="w-full text-left rounded-md bg-surface hover:bg-soft px-3 py-2 text-f12 text-ink transition-colors cursor-pointer shadow-[var(--shadow-panel)]">{s}</button>
              ))}
            </div>
          </div>
        ) : msgs.map((m, i) => (
          <Bubble key={i} {...m} streaming={busy && i === msgs.length - 1 && m.role === 'assistant'} onApprovalDecision={handleApprovalDecision} chapterSeq={seq ?? ctxSeq} />
        ))}
        <div ref={endRef} />
      </div>

      {/* 输入区 */}
      <div className="shrink-0 border-t border-line/60 bg-surface px-3 py-2.5">
        <div
          data-testid="chief-chat-composer"
          data-chief-composer="true"
          className="chief-composer-panel relative rounded-md px-2.5 py-2"
        >
          <MaterialAtPicker
            open={materialAt.open}
            query={materialAt.query}
            items={materialAt.items}
            loading={materialAt.loading}
            error={materialAt.error}
            activeIndex={materialAt.activeIndex}
            onActiveIndexChange={materialAt.setActiveIndex}
            onPick={materialAt.pick}
          />
          <textarea
            ref={taRef}
            value={input}
            onChange={(e) => {
              const v = e.target.value
              setInput(v)
              materialAt.syncFromValue(v, e.target.selectionStart ?? v.length)
            }}
            onSelect={(e) => {
              materialAt.syncFromValue(e.target.value, e.target.selectionStart ?? 0)
            }}
            rows={1}
            placeholder="就当前内容问主编… 输入 @ 引用章/设定/事件/素材…"
            onKeyDown={(e) => materialAt.onKeyDown(e, { onEnterSend: () => send() })}
            className="block w-full min-h-[36px] max-h-28 resize-none border-0 bg-transparent px-0 py-0.5 text-f13 leading-relaxed text-ink outline-none shadow-none ring-0 placeholder:text-faint/70 focus:border-transparent focus:outline-none focus:ring-0 focus:shadow-none focus-visible:outline-none"
          />
          <div data-testid="chief-chat-toolbar" className="mt-1.5 flex items-center gap-1.5">
            <Btn
              variant="ghost"
              icon
              title="引用全书对象(@)：章节/设定/事件/命题/素材"
              aria-label="引用全书对象"
              data-testid="chief-at-material"
              onClick={() => materialAt.openManual()}
            >
              <AtSign size={15} />
            </Btn>
            <Btn variant="ghost" icon title="附件功能待接入讨论模式" aria-label="添加附件" disabled>
              <Paperclip size={15} />
            </Btn>
            <Btn variant="ghost" icon title="语音输入待接入" aria-label="语音输入" disabled>
              <Mic size={15} />
            </Btn>
            <div className="flex-1" />
            {busy ? (
              // 生成中:发送键变「停止」——中止在途流(EventSource.close/AbortController.abort)+ 解锁 busy,可立即再发。
              <Btn variant="danger" onClick={stop} title="停止生成" aria-label="停止生成" className="h-8 min-w-[88px] shadow-none">
                <Square size={13} fill="currentColor" />
                停止
              </Btn>
            ) : (
              <Btn variant="primary" onClick={() => send()} disabled={!input.trim()} aria-label="发送" className="h-8 min-w-[88px] shadow-none">
                <Send size={15} />
                发送
              </Btn>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
