import { useState, useRef, useEffect } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Send, MessagesSquare, Loader2, User, Wrench, Zap, Database } from 'lucide-react'
import { api } from '../api'

const SUGGESTS = [
  '通读已确立的世界观与北极星,指出最大的叙事风险',
  '现有伏笔哪些有埋无收?按紧迫度排序',
  '查胡不为截至第1章的知识帧,他还不知道什么?',
  '这部书的反派动机够不够硬?怎么加压不洗白',
]

function ToolChip({ name, args }) {
  let a = ''
  try { const o = JSON.parse(args || '{}'); a = Object.entries(o).map(([k, v]) => `${k}=${v}`).join(' ') } catch { a = args || '' }
  return (
    <div className="inline-flex items-center gap-1.5 rounded-md bg-soft/70 border border-line px-2 py-1 text-[11.5px] text-faint mr-1.5 mb-1.5">
      <Wrench size={11} className="text-brand" /><span className="font-medium text-ink/80">{(name || '').replace(/^mcp_scribe3_/, '')}</span>{a && <span className="text-faint/80 truncate max-w-[160px]">{a}</span>}
    </div>
  )
}

function Bubble({ role, content, tools, streaming }) {
  const me = role === 'user'
  return (
    <div className={`flex gap-3 ${me ? 'flex-row-reverse' : ''}`}>
      <div className={`w-7 h-7 rounded-lg shrink-0 grid place-items-center ${me ? 'bg-brand text-white' : 'bg-soft text-brand'}`}>
        {me ? <User size={15} /> : <MessagesSquare size={15} />}
      </div>
      <div className={`max-w-[80%] ${me ? '' : 'flex-1'}`}>
        {!me && tools && tools.length > 0 && (
          <div className="flex flex-wrap mb-1.5">{tools.map((t, i) => <ToolChip key={i} name={t.name} args={t.args} />)}</div>
        )}
        <div className={`rounded-2xl px-4 py-2.5 text-[14px] leading-relaxed ${me ? 'bg-brand text-white inline-block' : 'bg-surface border border-line text-ink'}`}>
          {me ? <span className="whitespace-pre-wrap">{content}</span>
            : <div className="prose-chat">{content ? <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown> : <span className="text-faint">{streaming ? '主编在查证…' : '​'}</span>}{streaming && content && <Loader2 size={13} className="inline animate-spin text-faint ml-1" />}</div>}
        </div>
      </div>
    </div>
  )
}

export function ChatView() {
  const [msgs, setMsgs] = useState([])
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const [agentic, setAgentic] = useState(true)
  const endRef = useRef(null)
  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [msgs])

  const send = (text) => {
    const q = (text ?? input).trim()
    if (!q || busy) return
    setInput('')
    setMsgs((m) => [...m, { role: 'user', content: q }, { role: 'assistant', content: '', tools: [] }])
    setBusy(true)
    const mut = (fn) => setMsgs((m) => { const c = [...m]; c[c.length - 1] = fn(c[c.length - 1]); return c })
    api.chatStream(q, {
      agentic,
      onDelta: (delta) => mut((last) => ({ ...last, content: last.content + delta })),
      onTool: (name, args) => mut((last) => ({ ...last, tools: [...(last.tools || []), { name, args }] })),
      onDone: () => setBusy(false),
      onError: (err) => { mut((last) => ({ ...last, content: last.content + `\n\n_⚠ 出错:${err}_` })); setBusy(false) },
    })
  }

  return (
    <div className="h-full flex flex-col bg-canvas">
      <div className="h-11 shrink-0 border-b border-line bg-surface flex items-center gap-2 px-4">
        <MessagesSquare size={15} className="text-brand" />
        <span className="text-[13px] font-medium text-ink">主编对话</span>
        <span className="text-[12px] text-faint hidden md:inline">已注入本书北极星 / 角色 / 设定</span>
        <div className="ml-auto inline-flex rounded-lg border border-line bg-canvas p-0.5 text-[12px]">
          <button onClick={() => setAgentic(false)} className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-md transition-colors cursor-pointer ${!agentic ? 'bg-soft text-ink font-medium' : 'text-faint hover:text-ink'}`}><Zap size={12} />速答</button>
          <button onClick={() => setAgentic(true)} className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-md transition-colors cursor-pointer ${agentic ? 'bg-soft text-ink font-medium' : 'text-faint hover:text-ink'}`}><Database size={12} />联查实证</button>
        </div>
      </div>

      <div className="flex-1 min-h-0 overflow-y-auto">
        <div className="max-w-2xl mx-auto px-5 py-6 space-y-5">
          {msgs.length === 0 ? (
            <div className="pt-10">
              <div className="text-center text-faint text-[14px] mb-1.5">问主编任何关于这部书的事。</div>
              <div className="text-center text-faint/70 text-[12px] mb-5">「联查实证」模式下,主编会自己调 s3_ 工具查 SurrealDB 真实数据再答。</div>
              <div className="grid sm:grid-cols-2 gap-2.5">
                {SUGGESTS.map((s) => (
                  <button key={s} onClick={() => send(s)}
                    className="text-left rounded-xl border border-line bg-surface hover:border-brand hover:bg-soft/40 px-4 py-3 text-[13px] text-ink transition-colors cursor-pointer">{s}</button>
                ))}
              </div>
            </div>
          ) : msgs.map((m, i) => <Bubble key={i} role={m.role} content={m.content} tools={m.tools} streaming={busy && i === msgs.length - 1 && m.role === 'assistant'} />)}
          <div ref={endRef} />
        </div>
      </div>

      <div className="shrink-0 border-t border-line bg-surface px-4 py-3">
        <div className="max-w-2xl mx-auto flex items-end gap-2">
          <textarea value={input} onChange={(e) => setInput(e.target.value)} rows={1} placeholder={agentic ? '让主编联查实证…(Enter 发送)' : '和主编速聊…(Enter 发送)'}
            onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() } }}
            className="flex-1 resize-none rounded-xl border border-line bg-canvas px-3.5 py-2.5 text-[14px] text-ink outline-none focus:border-brand max-h-32" />
          <button onClick={() => send()} disabled={busy || !input.trim()}
            className="w-10 h-10 rounded-xl bg-brand text-white grid place-items-center disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer hover:opacity-90 transition-opacity shrink-0">
            {busy ? <Loader2 size={17} className="animate-spin" /> : <Send size={17} />}
          </button>
        </div>
      </div>
    </div>
  )
}
