import { useState, useRef, useEffect } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Send, MessagesSquare, Loader2, User, Wrench, Sparkles, Paperclip, X, FileText } from 'lucide-react'
import { api } from './api'
import { useChatPersist } from './useChatPersist'

const SUGGESTS = [
  '本章这样展开:……（提思路,主编写整章）',
  '把选中这段写得更冷,删形容词',
  '接着往下续写一段',
  '这章节奏如何?有什么风险',
]

function Bubble({ role, content, tools, note, streaming }) {
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
              <span key={i} className="inline-flex items-center gap-1 rounded-md bg-soft/70 border border-line px-1.5 py-0.5 text-[10.5px] text-faint">
                <Wrench size={9} className="text-brand" />
                {(t || '').replace(/^mcp_scribe3_/, '')}
              </span>
            ))}
          </div>
        )}
        <div className={`rounded-2xl px-3.5 py-2.5 text-[13.5px] leading-relaxed ${me ? 'bg-brand text-brandfg' : 'bg-surface border border-line text-ink'}`}>
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
        {note && <div className="mt-1 inline-flex items-center gap-1 text-[11px] text-brand"><Sparkles size={11} />{note}</div>}
      </div>
    </div>
  )
}

// 右轨主编对话:发消息走 POST /chat/write;改写提议 onProposal 提给中区。支持图片/文本附件。
export function WriteChat({ chapter, focalizer, seedQuote, onSeedUsed, onProposalStart, onProposalChunk, onProposal }) {
  const [msgs, setMsgs] = useState([])
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const [attachments, setAttachments] = useState([])
  const [dragging, setDragging] = useState(false)
  const endRef = useRef(null)
  const taRef = useRef(null)
  const fileRef = useRef(null)

  // 对话历史持久化:按 work+章存 localStorage,切章/刷新可恢复
  useChatPersist(`${api.getWork()}:ch:${chapter}`, msgs, setMsgs)

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [msgs])
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

    // text attachments → quoted into message body
    const textExtra = attachments.filter((a) => a.kind === 'text').map((a) => `\n\n【附件:${a.name}】\n${a.content}`).join('')
    const finalMsg = q + textExtra
    const images = attachments.filter((a) => a.kind === 'image').map((a) => ({ data: a.url.split(',')[1], type: a.mime }))

    const displayQ = q + (attachments.length ? ` [附件×${attachments.length}]` : '')
    setInput('')
    setAttachments([])
    if (taRef.current) taRef.current.style.height = 'auto'

    setMsgs((m) => [...m, { role: 'user', content: displayQ }, { role: 'assistant', content: '', tools: [] }])
    setBusy(true)
    const mut = (fn) => setMsgs((m) => { const c = [...m]; c[c.length - 1] = fn(c[c.length - 1]); return c })
    api.chatWrite(finalMsg, {
      chapter, focalizer, images,
      onDelta: (d) => mut((l) => ({ ...l, content: l.content + d })),
      onTool: (name) => mut((l) => ({ ...l, tools: [...(l.tools || []), name] })),
      onProposalStart: (s) => onProposalStart?.(s),
      onProposalChunk: (c) => onProposalChunk?.(c),
      onProposal: (p) => { onProposal?.(p); mut((l) => ({ ...l, note: '已在手稿处生成改写,请接受/弃用' })) },
      onDone: () => setBusy(false),
      onError: (err) => { mut((l) => ({ ...l, content: l.content + `\n\n_⚠ ${err}_` })); setBusy(false) },
    })
  }

  return (
    <div
      className="flex flex-col h-full min-h-0 relative"
      onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
      onDragLeave={() => setDragging(false)}
      onDrop={(e) => { e.preventDefault(); setDragging(false); addFiles([...e.dataTransfer.files]) }}
    >
      {dragging && (
        <div className="absolute inset-0 z-20 bg-brand/10 border-2 border-dashed border-brand rounded-lg flex items-center justify-center pointer-events-none">
          <span className="text-brand text-[13px] font-medium">拖入附件</span>
        </div>
      )}

      {/* 消息列表 */}
      <div className="flex-1 min-h-0 overflow-y-auto px-3 py-3 space-y-3">
        {msgs.length === 0 ? (
          <div className="pt-2">
            <div className="text-[12px] text-faint mb-2.5 leading-snug">提思路,主编帮你写/改本章手稿。改写以草稿卡出现在中间,你接受/弃用。</div>
            <div className="space-y-1.5">
              {SUGGESTS.map((s) => (
                <button key={s} onClick={() => send(s)} className="w-full text-left rounded-lg border border-line bg-canvas hover:border-brand hover:bg-soft/40 px-2.5 py-1.5 text-[12px] text-ink transition-colors cursor-pointer">{s}</button>
              ))}
            </div>
          </div>
        ) : msgs.map((m, i) => (
          <Bubble key={i} {...m} streaming={busy && i === msgs.length - 1 && m.role === 'assistant'} />
        ))}
        <div ref={endRef} />
      </div>

      {/* 附件预览条 */}
      {attachments.length > 0 && (
        <div className="shrink-0 px-2.5 pb-1.5 flex flex-wrap gap-1.5">
          {attachments.map((a) => (
            <div key={a.id} className="relative flex items-center gap-1.5 rounded-lg border border-line bg-soft px-2 py-1 text-[11.5px] text-ink max-w-[130px]">
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
      <div className="shrink-0 border-t border-line px-2.5 py-2">
        <div className={`flex items-end gap-1.5 rounded-xl border ${dragging ? 'border-brand' : 'border-line'} bg-canvas px-2.5 py-2 focus-within:border-brand transition-colors`}>
          <textarea
            ref={taRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            rows={1}
            placeholder="提思路 / 提要求…(Enter 发送,Shift+Enter 换行)"
            onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() } }}
            className="flex-1 resize-none bg-transparent text-[13px] text-ink outline-none max-h-32 leading-relaxed placeholder:text-faint"
          />
          <div className="flex items-center gap-0.5 shrink-0 pb-0.5">
            <button
              onClick={() => fileRef.current?.click()}
              title="附加图片或文本文件"
              className="w-7 h-7 rounded-lg grid place-items-center text-faint hover:text-ink hover:bg-soft transition-colors cursor-pointer"
            >
              <Paperclip size={14} />
            </button>
            <button
              onClick={() => send()}
              disabled={busy || (!input.trim() && attachments.length === 0)}
              className="w-8 h-8 rounded-lg bg-brand text-brandfg grid place-items-center disabled:opacity-40 disabled:cursor-default cursor-pointer hover:opacity-90 transition-opacity"
            >
              {busy ? <Loader2 size={15} className="animate-spin" /> : <Send size={15} />}
            </button>
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
