import { useState, useRef, useEffect } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Send, MessagesSquare, Loader2, User, Wrench, Sparkles, Paperclip, X, FileText, Mic, Check, AtSign } from 'lucide-react'
import { api } from './api'
import { orchestrateBeforeSend, evaluateOrchTurn, proposalFromDiscussion } from './lib/orchestrateSend'
import { applyUiEvents, uiDirectiveToEvents } from './lib/uiDirective'
import { WriteProposalCard } from './WriteProposalCard.jsx'
import { shouldUseHermesRun, hermesRunInstructions } from './lib/hermesRunIntent'
import { useSelection } from './selectionContext'
import { useChiefSlot } from './ChiefSlotContext'
import { useChatPersist } from './useChatPersist'
import { displayToolName } from './lib/toolName'
import { scrollBehavior } from './lib/utils'
import {
  approvalExpiryFromError,
  approvalStatusFromDecision,
  patchApprovalInMessages,
  runContextFromError,
  useHermesRunRecovery,
} from './lib/hermesRunRecovery'
import { useContextSnapshot } from './context/ContextSnapshotContext'
import { MaterialAtPicker } from './ui/MaterialAtPicker.jsx'
import { useMaterialAt } from './lib/useMaterialAt.js'
import { Btn } from './ui.jsx'
import { chiefEmptyCopy, chiefEmptyKind, pendingApprovalOf } from './lib/chiefReadable.js'
import { ChiefStatusStrip } from './views/chief/ChiefStatusStrip.jsx'

// Task 13 I-1:章内写作槽发起的 approval 型 run 也要绑发起时上下文,让重校验对它生效
// (WriteChat 与 ChiefDock 同走 scribe3_write 写路径;不绑=章内 run 永不受闸=假象)。
// 快照缺席(无 ContextSnapshotProvider / 降级直通)→ 返回 null,行为退回旧版(不绑,零回归)。
function runContextBind(snapshot) {
  if (!snapshot?.session_id) return null
  return { context_session_id: snapshot.session_id, context_revision: snapshot.revision ?? null }
}

function chatWriteContextBind(snapshot) {
  if (!snapshot?.session_id) return null
  return {
    context_session_id: snapshot.session_id,
    context_revision: snapshot.revision ?? null,
    context_hash: snapshot.context_hash ?? null,
  }
}

// Task 13:焦点对象 → 展示名(与 ChiefDock 同口径);run 卡片"发起时/当前焦点"用。
function focusLabel(f) {
  if (!f || typeof f !== 'object') return '—'
  return String(f.label || f.id || '—')
}

// Task 13:run 审批"发起时上下文已过期"卡片(voided=作废;stale=二次确认放行)。
function RunStaleCard({ ap, onApprovalDecision }) {
  const rc = ap.runContext
  if (!rc) return null
  return (
    <div data-testid="run-context-stale" className="mt-2 rounded-md border border-warn/40 bg-warn/5 px-2 py-1.5">
      <div className="flex items-center gap-1.5 text-f12 font-medium text-warn">
        <span data-testid="run-context-expired" className="inline-flex items-center rounded bg-warn/15 px-1 py-0.5 text-meta">已过期</span>
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
          className="mt-1.5 inline-flex h-6 items-center gap-1 rounded-md border border-warn/50 bg-surface px-2 text-meta font-medium text-warn">
          仍要批准(忽略过期)
        </button>
      )}
    </div>
  )
}

const SUGGESTS = [
  '本章这样展开:……（提思路,主编写整章）',
  '把选中这段写得更冷,删形容词',
  '接着往下续写一段',
  '这章节奏如何?有什么风险',
]

function toolOutputPreview(output) {
  const text = typeof output === 'string' ? output : JSON.stringify(output)
  return text.length > 220 ? text.slice(0, 220) + '…' : text
}

function Bubble({ role, content, tools, toolOutputs, approvals, note, streaming, onApprovalDecision, writeProposal, onProposalDone, setFocus }) {
  const me = role === 'user'
  // 无气泡:主编靠左 / 你靠右,色条+底色+分割线区分,省掉头像与圆角底
  return (
    <div
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
              <span key={i} className="inline-flex items-center gap-1 rounded-md bg-soft/70 border border-line px-1.5 py-0.5 text-meta text-faint">
                <Wrench size={9} className="text-brand" />
                {displayToolName(t)}
              </span>
            ))}
          </div>
        )}
        <div className="min-w-0 text-left text-ink">
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
          {!me && approvals?.length > 0 && (
            <div className="mt-2 space-y-2">
              {approvals.map((ap) => (
                <div key={`${ap.run_id || ''}:${ap.approval_id || ''}`} className="border-l-2 border-brand/50 pl-2.5 py-1">
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
                  </div>
                  <RunStaleCard ap={ap} onApprovalDecision={onApprovalDecision} />
                </div>
              ))}
            </div>
          )}
          {!me && writeProposal?.ops?.length > 0 && (
            <div className="mt-2">
              <WriteProposalCard
                proposal={writeProposal}
                onDone={onProposalDone}
                setFocus={setFocus}
                onSel={(detail) => {
                  try { window.dispatchEvent(new CustomEvent('s3-selection', { detail })) } catch { /* */ }
                }}
              />
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
        {note && <div className="mt-1 inline-flex items-center gap-1 text-meta text-brand"><Sparkles size={11} />{note}</div>}
      </div>
    </div>
  )
}

// 右轨主编对话:发消息走 POST /chat/write;改写提议 onProposal 提给中区。支持图片/文本附件。
export function WriteChat({ chapter, focalizer, seedQuote, phase = '', onSeedUsed, onProposalStart, onProposalChunk, onProposal, onProposalInterrupted }) {
  const { setFocus } = useSelection()
  const { jobBusy } = useChiefSlot()
  const orchOnSel = (detail) => {
    try { window.dispatchEvent(new CustomEvent('s3-selection', { detail })) } catch { /* */ }
  }
  const applyOrchUiAfterApprove = (pkg) => {
    const ui = pkg?.ui_directive
    if (!ui) return
    applyUiEvents(uiDirectiveToEvents(ui), { onSel: orchOnSel, setFocus })
  }
  // Task 13 I-1:章内 run 绑发起时上下文的来源(四栏共享的统一快照;缺席时降级不绑)。
  const { snapshot, restoring, capabilities } = useContextSnapshot()
  // capabilities 与 createContextSession 并行拉取。能力清单尚未返回时仍可能由后端
  // 要求 snapshot_v1；只要服务器上下文还在创建，就先按需绑定处理，不能出现“前端
  // 默认 false 放行、后端 true 拒绝”的竞态。旧部署/测试没有创建会话时 restoring=false，
  // 仍保留原有无绑定路径。
  const snapshotBindingRequired = capabilities?.flags?.snapshot_v1 === true || restoring
  const snapshotBindingReady = Boolean(
    snapshot?.session_id
      && Number.isFinite(snapshot?.revision)
      && typeof snapshot?.context_hash === 'string'
      && snapshot.context_hash.trim(),
  )
  const contextPreparing = snapshotBindingRequired && !snapshotBindingReady
  const [msgs, setMsgs] = useState([])
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const [attachments, setAttachments] = useState([])
  const [dragging, setDragging] = useState(false)
  const endRef = useRef(null)
  const taRef = useRef(null)
  const fileRef = useRef(null)
  const materialAt = useMaterialAt({ input, setInput, taRef })
  const ctrlRef = useRef(null)   // 断头修复#83:在途写作流的 AbortController(停止/卸载中止)
  const activeRunIdsRef = useRef(new Set())
  const stop = () => {
    ctrlRef.current?.abort?.()
    ctrlRef.current?.close?.()
    ctrlRef.current = null
    activeRunIdsRef.current.clear()
    // proposal_chunk 已由父级累积到中区草稿卡；Abort 不会再收到 proposal 收尾，
    // 必须显式解除其 streaming 锁，作者才能采用自己已经看见的部分稿。
    onProposalInterrupted?.()
    setBusy(false)
  }
  useEffect(() => () => { ctrlRef.current?.abort?.() }, [])
  // 主编主动化 T4/T5(审查 P0-2/P2-12):seed 双轨(sessionStorage pending+事件),预填=追加
  const seedIn = (v) => { setInput((prev) => (prev ? prev + '\n' : '') + String(v)); taRef.current?.focus() }
  useEffect(() => {
    try {
      const pending = sessionStorage.getItem('s3.chief.seed')
      if (pending) { sessionStorage.removeItem('s3.chief.seed'); seedIn(pending) }
    } catch { /* */ }
    const on = (e) => { if (e?.detail) { try { sessionStorage.removeItem('s3.chief.seed') } catch { /* */ }; seedIn(e.detail) } }
    window.addEventListener('s3-chief-seed', on)
    return () => window.removeEventListener('s3-chief-seed', on)
  }, [])

  // 对话历史持久化:按 work+章存 localStorage,切章/刷新可恢复
  useChatPersist(`${api.getWork()}:ch:${chapter}`, msgs, setMsgs)
  useHermesRunRecovery({
    msgs, setMsgs, setBusy, activeRunIdsRef,
    pendingApprovalScope: chapter != null && phase ? { chapter, phase } : null,
  })

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: scrollBehavior() }) }, [msgs])
  useEffect(() => {
    if (seedQuote) { setInput((v) => (v ? v + '\n' : '') + seedQuote); onSeedUsed?.() }
  }, [seedQuote])

  // auto-resize textarea
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
      // Task 13:approve_stale 二次确认令牌 + 当前快照上下文(后端仍以库内 live 快照为准)。
      const body = { approval_id: approval.approval_id, decision }
      if (approveStale) {
        body.approve_stale = true
        body.context_session_id = snapshot?.session_id ?? null
        body.context_revision = snapshot?.revision ?? null
      }
      await api.aiRunApproval(approval.run_id, body)
      patchApproval(approval, { status: decision === 'approve' ? 'approved' : 'denied', decision, runContext: null })
    } catch (e) {
      // Task 13:409 run_context_changed/stale → 展示过期焦点卡片,不当作提交失败。
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

  const addFiles = (files) => {
    for (const f of files) {
      if (f.type.startsWith('image/')) {
        const reader = new FileReader()
        reader.onload = (e) => setAttachments((a) => [...a, { id: Date.now() + Math.random(), kind: 'image', name: f.name, url: e.target.result, mime: f.type }])
        reader.readAsDataURL(f)
      } else if (f.size < 200_000 && (f.type === 'text/plain' || f.name.endsWith('.md') || f.name.endsWith('.txt'))) {
        const reader = new FileReader()
        reader.onload = (e) => setAttachments((a) => [...a, { id: Date.now() + Math.random(), kind: 'text', name: f.name, content: e.target.result }])
        reader.readAsText(f)
      }
    }
  }

  const send = (text) => {
    const q = (text ?? input).trim()
    if ((!q && attachments.length === 0) || busy || contextPreparing || jobBusy) return
    // 主编主动化 T8:「#想法 」前缀 → 想法收件箱(主编路由落位,不走写作流)
    if (q.startsWith('#想法')) {
      const idea = q.replace(/^#想法\s*/, '')
      if (!idea) return
      setInput('')
      setMsgs((m) => [...m, { role: 'user', content: q }, { role: 'assistant', content: '', tools: [] }])
      api.addIdea(idea).then((r) => {
        const tail = r.status === 'unclear' ? `\n\n${r.question}`
          : r.status === 'pending_approval' ? '\n\n(动设定/改旧章级——已挂收件箱等你批)'
          : r.target_seq ? `\n\n已落到第 ${r.target_seq} 章的作者意图,下次提案/写作最高优先吃它。` : ''
        setMsgs((m) => { const c = [...m]; c[c.length - 1] = { role: 'assistant', content: `收到想法(${r.kind}):${r.note || ''}${tail}` }; return c })
      }).catch((e) => setMsgs((m) => { const c = [...m]; c[c.length - 1] = { role: 'assistant', content: `想法登记失败:${e?.body?.detail || e?.message || ''}` }; return c }))
      return
    }

    // text attachments → quoted into message body
    const textExtra = attachments.filter((a) => a.kind === 'text').map((a) => `\n\n【附件:${a.name}】\n${a.content}`).join('')
    const finalMsg = q + textExtra
    const images = attachments.filter((a) => a.kind === 'image').map((a) => ({ data: a.url.split(',')[1], type: a.mime }))

    const displayQ = q + (attachments.length ? ` [附件 ${attachments.length} 个]` : '')
    setInput('')
    setAttachments([])
    if (taRef.current) taRef.current.style.height = 'auto'

    setMsgs((m) => [...m, { role: 'user', content: displayQ }, { role: 'assistant', content: '', tools: [] }])
    setBusy(true)
    const mut = (fn) => setMsgs((m) => { const c = [...m]; c[c.length - 1] = fn(c[c.length - 1]); return c })
    const streamHandlers = {
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
        mut((l) => ({ ...l, run_id: l.run_id || runId, approvals: [...(l.approvals || []), { ...approval, status: 'pending' }] }))
      },
      onApprovalResolved: (approval) => {
        const status = approvalStatusFromDecision(approval?.decision)
        patchApproval(approval, { ...approval, status })
        if (status === 'approved') applyOrchUiAfterApprove(orchPkg)
      },
      onProposalStart: (s) => onProposalStart?.(s),
      onProposalChunk: (c) => onProposalChunk?.(c),
      onProposal: (p) => { onProposal?.(p); mut((l) => ({ ...l, note: '已在手稿处生成改写,请接受/弃用' })) },
      onDone: () => {
        activeRunIdsRef.current.clear()
        setBusy(false)
        evaluateOrchTurn({ toolsCalled: toolsThisTurn, approvedWrites: [] }).then((ev) => {
          const status = ev?.evaluation?.status
          const remedy = ev?.evaluation?.remedy
          if (status === 'incomplete' && remedy?.message) {
            mut((l) => ({
              ...l,
              content: (l.content || '') + `\n\n_编排提示：${remedy.message}_`
                + (remedy.suggested_prompt ? `\n可发送：${remedy.suggested_prompt}` : ''),
            }))
            proposalFromDiscussion('根据本轮讨论生成写入提案').then((res) => {
              if (res?.proposal?.ops?.length) {
                mut((l) => ({ ...l, writeProposal: res.proposal, orchPackage: orchPkg }))
              }
            }).catch(() => {})
          }
          const writeTools = orchPkg?.write_tools || []
          const calledWrites = toolsThisTurn.filter((t) => writeTools.includes(t))
          if (calledWrites.length && orchPkg && (status === 'awaiting_approval' || status === 'incomplete')) {
            api.orchBuildProposal({
              package: orchPkg,
              ops: calledWrites.map((t) => ({ tool: t, args: {}, label: t })),
              summary: `本回合写入提案（${calledWrites.join(', ')}）`,
            }).then((res) => {
              if (res?.proposal) mut((l) => ({ ...l, writeProposal: res.proposal, orchPackage: orchPkg }))
            }).catch(() => {})
          }
        }).catch(() => {})
      },
      onRetry: () => mut((l) => ({ ...l, content: (l.content || '') + (l.content?.includes('重新连接') ? '' : '\n\n_重新连接中..._') })),
      onError: (err) => {
        activeRunIdsRef.current.clear()
        const hint = String(err || '')
        const guide = hint.includes('旅程') ? '\n可点顶栏「总纲」或「旅程」先立作品意图和母题。' : ''
        mut((l) => ({ ...l, content: l.content + `\n\n_出错:${hint}${guide}_` }))
        setBusy(false)
      },
    }
    const toolsThisTurn = []
    let orchPkg = null
    const origOnTool = streamHandlers.onTool
    streamHandlers.onTool = (name) => {
      toolsThisTurn.push(name)
      origOnTool?.(name)
    }
    // 统一编排 resolve（正则仅作 resolve 失败回退）
    orchestrateBeforeSend(finalMsg, {
      chapter, phase, applyFocus: true, onSel: orchOnSel, setFocus,
    }).then((orch) => {
      orchPkg = orch.package || null
      if (orchPkg) mut((l) => ({ ...l, orchPackage: orchPkg, orchDomain: orchPkg.domain }))
      const worldWrite = orch.useWorldWriteRun || shouldUseHermesRun(finalMsg)
      if (worldWrite) {
        ctrlRef.current = api.runWrite(finalMsg, {
          chapter, focalizer, phase: '',
          context: runContextBind(snapshot),
          instructions: orch.instructions || hermesRunInstructions({ chapter, focalizer, phase: '' }),
          ...streamHandlers,
        })
        return
      }
      ctrlRef.current = api.chatWrite(finalMsg, {
        chapter, focalizer, images, phase,
        context: chatWriteContextBind(snapshot),
        ...streamHandlers,
      })
    }).catch(() => {
      if (shouldUseHermesRun(finalMsg)) {
        ctrlRef.current = api.runWrite(finalMsg, {
          chapter, focalizer, phase: '',
          context: runContextBind(snapshot),
          instructions: hermesRunInstructions({ chapter, focalizer, phase: '' }),
          ...streamHandlers,
        })
      } else {
        ctrlRef.current = api.chatWrite(finalMsg, {
          chapter, focalizer, images, phase,
          context: chatWriteContextBind(snapshot),
          ...streamHandlers,
        })
      }
    })
  }

  const pending = pendingApprovalOf(msgs)
  const emptyKind = chiefEmptyKind({
    work: api.getWork?.() || '',
    msgs,
    pending,
    surface: 'write',
  })
  const emptyCopy = chiefEmptyCopy(emptyKind || 'write_ask')

  return (
    <div
      data-testid="chief-write-chat"
      className="flex flex-col h-full min-h-0 relative bg-surface"
      onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
      onDragLeave={() => setDragging(false)}
      onDrop={(e) => { e.preventDefault(); setDragging(false); addFiles([...e.dataTransfer.files]) }}
    >
      {dragging && (
        <div className="absolute inset-0 z-20 bg-brand/10 border-2 border-dashed border-brand/50 rounded-md flex items-center justify-center pointer-events-none">
          <span className="text-brand text-f13 font-medium">拖入附件</span>
        </div>
      )}

      {/* 消息列表 */}
      <div data-testid="chief-chat-messages" className="flex-1 min-h-0 overflow-y-auto px-3 py-2 bg-canvas/50">
        {msgs.length === 0 ? (
          <div className="pt-1 space-y-2" data-testid="chief-empty">
            <div className="rounded-md bg-soft/40 px-3 py-2 text-f12 text-faint leading-snug">
              <div className="text-ink">{emptyCopy.title}</div>
              <div className="mt-0.5">{emptyCopy.body}</div>
            </div>
            <div className="space-y-1.5">
              {SUGGESTS.map((s) => (
                <button key={s} onClick={() => send(s)} className="w-full text-left rounded-md bg-surface hover:bg-soft px-3 py-2 text-f12 text-ink transition-colors cursor-pointer shadow-[var(--shadow-panel)]">{s}</button>
              ))}
            </div>
          </div>
        ) : msgs.map((m, i) => (
          <Bubble
            key={i}
            {...m}
            streaming={busy && i === msgs.length - 1 && m.role === 'assistant'}
            onApprovalDecision={handleApprovalDecision}
            setFocus={setFocus}
            onProposalDone={(res) => {
              if (res?.ui_events?.length) applyUiEvents(res.ui_events, { onSel: orchOnSel, setFocus })
              if (res?.proposal) {
                setMsgs((prev) => {
                  const c = [...prev]
                  if (c[i]) c[i] = { ...c[i], writeProposal: res.proposal }
                  return c
                })
              }
            }}
          />
        ))}
        <div ref={endRef} />
      </div>

      {/* 附件预览条 */}
      {attachments.length > 0 && (
        <div className="shrink-0 px-2.5 pb-1.5 flex flex-wrap gap-1.5">
          {attachments.map((a) => (
            <div key={a.id} className="relative flex items-center gap-1.5 rounded-md bg-soft px-2 py-1 text-f12 text-ink max-w-[130px]">
              {a.kind === 'image'
                ? <img src={a.url} alt={a.name} className="w-5 h-5 rounded object-cover shrink-0" />
                : <FileText size={12} className="text-brand shrink-0" />}
              <span className="truncate flex-1">{a.name}</span>
              <button onClick={() => setAttachments((v) => v.filter((x) => x.id !== a.id))} className="shrink-0 text-faint hover:text-danger cursor-pointer transition-colors">
                <X size={10} />
              </button>
            </div>
          ))}
        </div>
      )}

      <ChiefStatusStrip
        label={chapter != null ? `第 ${chapter} 章${phase ? ` · ${phase}` : ''}` : '未选中'}
        input={input}
        pending={!!pending}
        onJumpPending={() => document.querySelector('[data-testid="chief-pending-card"], [data-testid="run-approve"]')?.scrollIntoView({ block: 'nearest' })}
      />
      {/* 输入区 */}
      <div className="shrink-0 border-t border-line/60 bg-surface px-3 py-2.5">
        {contextPreparing && (
          <div role="status" aria-live="polite" className="mb-1.5 text-f12 text-faint">
            {restoring ? '上下文准备中，暂不能发送写作请求。' : '上下文尚未就绪，暂不能发送写作请求。'}
          </div>
        )}
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
            placeholder="提思路 / 提要求… 输入 @ 引用章/设定/事件/素材…"
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
            <Btn variant="ghost" icon
              onClick={() => fileRef.current?.click()}
              title="添加图片或文本文件" aria-label="添加附件"
            >
              <Paperclip size={15} />
            </Btn>
            <Btn variant="ghost" icon title="语音输入待接入" aria-label="语音输入" disabled>
              <Mic size={15} />
            </Btn>
            <div className="flex-1" />
            {busy ? (
              <Btn variant="danger" onClick={stop} title="停止生成" aria-label="停止生成" className="h-8 min-w-[88px] shadow-none">
                <X size={15} />
                停止
              </Btn>
            ) : (
              <Btn variant="primary"
                onClick={() => send()}
                disabled={contextPreparing || jobBusy || (!input.trim() && attachments.length === 0)}
                title={jobBusy ? '选择/驾驶作业进行中，暂勿再写同章' : undefined}
                className="h-8 min-w-[88px] shadow-none"
                aria-label="发送"
              >
                <Send size={15} />
                发送
              </Btn>
            )}
          </div>
        </div>
        <input
          ref={fileRef}
          type="file"
          accept="image/*,.txt,.md"
          multiple
          className="hidden"
          onChange={(e) => { addFiles([...e.target.files]); e.target.value = '' }}
        />
      </div>
    </div>
  )
}
