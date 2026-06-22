import { useState, useRef, useEffect } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Send, MessagesSquare, Loader2, User } from 'lucide-react'
import { api } from '../api'

const SUGGESTS = [
  '通读已确立的世界观与北极星,指出最大的叙事风险',
  '主角的情感弧怎么落地到具体场景?给 3 个开场选项',
  '现有伏笔哪些有埋无收?按紧迫度排序',
  '这部书的反派动机够不够硬?怎么加压不洗白',
]

function Bubble({ role, content, streaming }) {
  const me = role === 'user'
  return (
    <div className={`flex gap-3 ${me ? 'flex-row-reverse' : ''}`}>
      <div className={`w-7 h-7 rounded-lg shrink-0 grid place-items-center ${me ? 'bg-brand text-white' : 'bg-soft text-brand'}`}>
        {me ? <User size={15} /> : <MessagesSquare size={15} />}
      </div>
      <div className={`max-w-[78%] rounded-2xl px-4 py-2.5 text-[14px] leading-relaxed ${me ? 'bg-brand text-white' : 'bg-surface border border-line text-ink'}`}>
        {me ? <span className="whitespace-pre-wrap">{content}</span>
          : <div className="prose-chat"><ReactMarkdown remarkPlugins={[remarkGfm]}>{content || '​'}</ReactMarkdown>{streaming && <Loader2 size={13} className="inline animate-spin text-faint ml-1" />}</div>}
      </div>
    </div>
  )
}

export function ChatView() {
  const [msgs, setMsgs] = useState([])
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const endRef = useRef(null)
  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [msgs])

  const send = (text) => {
    const q = (text ?? input).trim()
    if (!q || busy) return
    setInput('')
    setMsgs((m) => [...m, { role: 'user', content: q }, { role: 'assistant', content: '' }])
    setBusy(true)
    const append = (delta) => setMsgs((m) => {
      const c = [...m]; const last = c[c.length - 1]
      c[c.length - 1] = { ...last, content: last.content + delta }; return c
    })
    api.chatStream(q, {
      onDelta: append,
      onDone: () => setBusy(false),
      onError: (err) => { append(`\n\n_⚠ 出错:${err}_`); setBusy(false) },
    })
  }

  return (
    <div className="h-full flex flex-col bg-canvas">
      <div className="h-11 shrink-0 border-b border-line bg-surface flex items-center gap-2 px-4">
        <MessagesSquare size={15} className="text-brand" />
        <span className="text-[13px] font-medium text-ink">主编对话</span>
        <span className="text-[12px] text-faint">已注入本书北极星 / 角色 / 设定 · 限知护栏</span>
      </div>

      <div className="flex-1 min-h-0 overflow-y-auto">
        <div className="max-w-2xl mx-auto px-5 py-6 space-y-5">
          {msgs.length === 0 ? (
            <div className="pt-10">
              <div className="text-center text-faint text-[14px] mb-5">问主编任何关于这部书的事——它读过你的设定。</div>
              <div className="grid sm:grid-cols-2 gap-2.5">
                {SUGGESTS.map((s) => (
                  <button key={s} onClick={() => send(s)}
                    className="text-left rounded-xl border border-line bg-surface hover:border-brand hover:bg-soft/40 px-4 py-3 text-[13px] text-ink transition-colors cursor-pointer">{s}</button>
                ))}
              </div>
            </div>
          ) : msgs.map((m, i) => <Bubble key={i} role={m.role} content={m.content} streaming={busy && i === msgs.length - 1 && m.role === 'assistant'} />)}
          <div ref={endRef} />
        </div>
      </div>

      <div className="shrink-0 border-t border-line bg-surface px-4 py-3">
        <div className="max-w-2xl mx-auto flex items-end gap-2">
          <textarea value={input} onChange={(e) => setInput(e.target.value)} rows={1} placeholder="和主编聊聊这部书…(Enter 发送 / Shift+Enter 换行)"
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
