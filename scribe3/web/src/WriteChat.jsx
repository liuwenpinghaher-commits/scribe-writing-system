import { useState, useRef, useEffect } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Send, MessagesSquare, Loader2, User, Wrench, Sparkles, Paperclip, X, FileText, Mic, Check } from 'lucide-react'
import { api } from './api'
import { useChatPersist } from './useChatPersist'
import { displayToolName } from './lib/toolName'
import { scrollBehavior } from './lib/utils'
import { hermesRunInstructions, shouldUseHermesRun } from './lib/hermesRunIntent'
import { patchApprovalInMessages, runContextFromError, useHermesRunRecovery } from './lib/hermesRunRecovery'
import { useContextSnapshot } from './context/ContextSnapshotContext'
import { Btn } from './ui.jsx'

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

function Bubble({ role, content, tools, toolOutputs, approvals, note, streaming, onApprovalDecision }) {
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
              <span key={i} className="inline-flex items-center gap-1 rounded-md bg-soft/70 border border-line px-1.5 py-0.5 text-meta text-faint">
                <Wrench size={9} className="text-brand" />
                {displayToolName(t)}
              </span>
            ))}
          </div>
        )}
        <div className={`rounded-2xl px-3.5 py-2.5 text-f14 leading-relaxed ${me ? 'bg-brand text-brandfg' : 'bg-surface border border-line text-ink'}`}>
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
                    ) : ap.status === 'submitting' ? (
                      <span className="text-f12 text-faint">提交中…</span>
                    ) : ap.status === 'error' ? (
                      <span className="text-f12 text-danger">提交失败</span>
                    ) : ap.runContext ? null : (
                      <>
                        <button type="button" aria-label="批准" onClick={() => onApprovalDecision?.(ap, 'approve')}
                          className="inline-flex h-7 items-center gap-1 rounded-md bg-brand px-2 text-f12 font-medium text-brandfg">
                          <Check size={12} />批准
                        </button>
                        <button type="button" aria-label="拒绝" onClick={() => onApprovalDecision?.(ap, 'deny')}
                          className="inline-flex h-7 items-center gap-1 rounded-md border border-line bg-surface px-2 text-f12 font-medium text-ink">
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
export function WriteChat({ chapter, focalizer, seedQuote, phase = '', onSeedUsed, onProposalStart, onProposalChunk, onProposal }) {
  // Task 13 I-1:章内 run 绑发起时上下文的来源(四栏共享的统一快照;缺席时降级不绑)。
  const { snapshot } = useContextSnapshot()
  const [msgs, setMsgs] = useState([])
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const [attachments, setAttachments] = useState([])
  const [dragging, setDragging] = useState(false)
  const endRef = useRef(null)
  const taRef = useRef(null)
  const fileRef = useRef(null)
  const ctrlRef = useRef(null)   // 断头修复#83:在途写作流的 AbortController(停止/卸载中止)
  const activeRunIdsRef = useRef(new Set())
  const stop = () => { ctrlRef.current?.abort?.(); ctrlRef.current?.close?.(); ctrlRef.current = null; activeRunIdsRef.current.clear(); setBusy(false) }
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
  useHermesRunRecovery({ msgs, setMsgs, setBusy, activeRunIdsRef })

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
      const rc = runContextFromError(e)
      if (rc) {
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
    if ((!q && attachments.length === 0) || busy) return
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
        const status = approval?.decision === 'approve' ? 'approved' : 'denied'
        patchApproval(approval, { ...approval, status })
      },
      onProposalStart: (s) => onProposalStart?.(s),
      onProposalChunk: (c) => onProposalChunk?.(c),
      onProposal: (p) => { onProposal?.(p); mut((l) => ({ ...l, note: '已在手稿处生成改写,请接受/弃用' })) },
      onDone: () => { activeRunIdsRef.current.clear(); setBusy(false) },
      onError: (err) => { activeRunIdsRef.current.clear(); mut((l) => ({ ...l, content: l.content + `\n\n_出错:${err}_` })); setBusy(false) },
    }
    if (shouldUseHermesRun(finalMsg)) {
      ctrlRef.current = api.runWrite(finalMsg, {
        chapter, focalizer, phase,
        context: runContextBind(snapshot),   // Task 13 I-1:绑发起时上下文 → 章内 run 也受审批重校验
        instructions: hermesRunInstructions({ chapter, focalizer, phase }),
        ...streamHandlers,
      })
      return
    }
    // 断头修复#83:chatWrite 返回 AbortController——存 ref 供停止按钮中止在途流
    ctrlRef.current = api.chatWrite(finalMsg, {
      chapter, focalizer, images, phase,
      // 与审批型 Run 同样绑定发起时快照；ContextSnapshot 门开启时，普通动稿
      // 不能因缺少 session/revision 被后端 400 拒绝。
      context: chatWriteContextBind(snapshot),
      ...streamHandlers,
    })
  }

  return (
    <div
      data-testid="chief-write-chat"
      className="flex flex-col h-full min-h-0 relative bg-surface"
      onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
      onDragLeave={() => setDragging(false)}
      onDrop={(e) => { e.preventDefault(); setDragging(false); addFiles([...e.dataTransfer.files]) }}
    >
      {dragging && (
        <div className="absolute inset-0 z-20 bg-brand/10 border-2 border-dashed border-brand rounded-lg flex items-center justify-center pointer-events-none">
          <span className="text-brand text-f13 font-medium">拖入附件</span>
        </div>
      )}

      {/* 消息列表 */}
      <div data-testid="chief-chat-messages" className="flex-1 min-h-0 overflow-y-auto px-3 py-3 space-y-3 bg-canvas/60">
        {msgs.length === 0 ? (
          <div className="pt-2">
            <div className="rounded-lg border border-line bg-surface px-2.5 py-2 text-f12 text-faint mb-2.5 leading-snug">提思路,主编帮你写/改本章手稿。改写以草稿卡出现在中间,你接受/弃用。</div>
            <div className="space-y-1.5">
              {SUGGESTS.map((s) => (
                <button key={s} onClick={() => send(s)} className="w-full text-left rounded-lg border border-line bg-canvas hover:border-brand hover:bg-soft/40 px-2.5 py-1.5 text-f12 text-ink transition-colors cursor-pointer">{s}</button>
              ))}
            </div>
          </div>
        ) : msgs.map((m, i) => (
          <Bubble key={i} {...m} streaming={busy && i === msgs.length - 1 && m.role === 'assistant'} onApprovalDecision={handleApprovalDecision} />
        ))}
        <div ref={endRef} />
      </div>

      {/* 附件预览条 */}
      {attachments.length > 0 && (
        <div className="shrink-0 px-2.5 pb-1.5 flex flex-wrap gap-1.5">
          {attachments.map((a) => (
            <div key={a.id} className="relative flex items-center gap-1.5 rounded-lg border border-line bg-soft px-2 py-1 text-f12 text-ink max-w-[130px]">
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

      {/* 输入区 */}
      <div className="shrink-0 border-t border-line bg-surface px-3 py-2">
        <div
          data-testid="chief-chat-composer"
          data-chief-composer="true"
          className="chief-composer-panel rounded-xl px-2.5 py-2"
        >
          <textarea
            ref={taRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            rows={1}
            placeholder="提思路 / 提要求…"
            onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() } }}
            className="block w-full min-h-[36px] max-h-28 resize-none border-0 bg-transparent px-0 py-0.5 text-f13 leading-relaxed text-ink outline-none shadow-none ring-0 placeholder:text-faint/70 focus:border-transparent focus:outline-none focus:ring-0 focus:shadow-none focus-visible:outline-none"
          />
          <div data-testid="chief-chat-toolbar" className="mt-1.5 flex items-center gap-1.5">
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
                disabled={!input.trim() && attachments.length === 0}
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
