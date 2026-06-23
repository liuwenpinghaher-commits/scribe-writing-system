import { useState, useRef, useEffect } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Send, MessagesSquare, Loader2, User, Wrench, Sparkles } from 'lucide-react'
import { api } from './api'

const SUGGESTS = [
  '本章这样展开:……（提思路,主编写整章）',
  '把选中这段写得更冷,删形容词',
  '接着往下续写一段',
  '这章节奏如何?有什么风险',
]

function Bubble({ role, content, tools, note }) {
  const me = role === 'user'
  return (
    <div className={`flex gap-2 ${me ? 'flex-row-reverse' : ''}`}>
      <div className={`w-6 h-6 rounded-md shrink-0 grid place-items-center ${me ? 'bg-brand text-white' : 'bg-soft text-brand'}`}>{me ? <User size={13} /> : <MessagesSquare size={13} />}</div>
      <div className={`max-w-[85%] ${me ? '' : 'flex-1 min-w-0'}`}>
        {!me && tools?.length > 0 && <div className="flex flex-wrap gap-1 mb-1">{tools.map((t, i) => <span key={i} className="inline-flex items-center gap-1 rounded bg-soft/70 border border-line px-1.5 py-0.5 text-[10.5px] text-faint"><Wrench size={9} className="text-brand" />{(t || '').replace(/^mcp_scribe3_/, '')}</span>)}</div>}
        <div className={`rounded-xl px-3 py-2 text-[13px] leading-relaxed ${me ? 'bg-brand text-white' : 'bg-canvas border border-line text-ink'}`}>
          {me ? <span className="whitespace-pre-wrap">{content}</span> : <div className="prose-chat">{content ? <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown> : <span className="text-faint">…</span>}</div>}
        </div>
        {note && <div className="mt-1 inline-flex items-center gap-1 text-[11px] text-brand"><Sparkles size={11} />{note}</div>}
      </div>
    </div>
  )
}

// 右轨主编对话:发消息走 /chat/write;对话进这里,改写提议 onProposal 提给中区。
export function WriteChat({ chapter, focalizer, seedQuote, onSeedUsed, onProposal }) {
  const [msgs, setMsgs] = useState([])
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const endRef = useRef(null)
  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [msgs])
  useEffect(() => { if (seedQuote) { setInput((v) => (v ? v + '\n' : '') + `「${seedQuote}」`); onSeedUsed?.() } }, [seedQuote])

  const send = (text) => {
    const q = (text ?? input).trim()
    if (!q || busy) return
    setInput('')
    setMsgs((m) => [...m, { role: 'user', content: q }, { role: 'assistant', content: '', tools: [] }])
    setBusy(true)
    const mut = (fn) => setMsgs((m) => { const c = [...m]; c[c.length - 1] = fn(c[c.length - 1]); return c })
    api.chatWrite(q, {
      chapter, focalizer,
      onDelta: (d) => mut((l) => ({ ...l, content: l.content + d })),
      onTool: (name) => mut((l) => ({ ...l, tools: [...(l.tools || []), name] })),
      onProposal: (p) => { onProposal?.(p); mut((l) => ({ ...l, note: '已在手稿处生成改写,请接受/弃用' })) },
      onDone: () => setBusy(false),
      onError: (err) => { mut((l) => ({ ...l, content: l.content + `\n\n_⚠ ${err}_` })); setBusy(false) },
    })
  }

  return (
    <div className="flex flex-col h-full min-h-0">
      <div className="flex-1 min-h-0 overflow-y-auto px-3 py-3 space-y-3">
        {msgs.length === 0 ? (
          <div className="pt-2">
            <div className="text-[12px] text-faint mb-2.5 leading-snug">提思路,主编帮你写/改本章手稿。改写以草稿卡出现在中间,你接受/弃用。</div>
            <div className="space-y-1.5">
              {SUGGESTS.map((s) => <button key={s} onClick={() => send(s)} className="w-full text-left rounded-lg border border-line bg-canvas hover:border-brand hover:bg-soft/40 px-2.5 py-1.5 text-[12px] text-ink transition-colors cursor-pointer">{s}</button>)}
            </div>
          </div>
        ) : msgs.map((m, i) => <Bubble key={i} {...m} />)}
        {busy && <div className="text-[11px] text-faint inline-flex items-center gap-1"><Loader2 size={11} className="animate-spin" />主编书写中…</div>}
        <div ref={endRef} />
      </div>
      <div className="shrink-0 border-t border-line p-2.5">
        <div className="flex items-end gap-1.5">
          <textarea value={input} onChange={(e) => setInput(e.target.value)} rows={1} placeholder="提思路 / 提要求…(Enter 发送)"
            onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() } }}
            className="flex-1 resize-none rounded-lg border border-line bg-canvas px-2.5 py-2 text-[13px] text-ink outline-none focus:border-brand max-h-28" />
          <button onClick={() => send()} disabled={busy || !input.trim()} className="w-9 h-9 rounded-lg bg-brand text-white grid place-items-center disabled:opacity-40 disabled:cursor-default cursor-pointer hover:opacity-90 shrink-0">
            {busy ? <Loader2 size={16} className="animate-spin" /> : <Send size={16} />}
          </button>
        </div>
      </div>
    </div>
  )
}
