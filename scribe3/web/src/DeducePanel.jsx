import { useState } from 'react'
import { Sparkles, Loader2, Copy, ArrowRight } from 'lucide-react'
import { api } from './api'
import { Btn, Empty } from './ui'

// 演绎:渲染某角色这一场的限知草稿(他知道什么、看到什么)——作为素材,不直接入正文。
// 「给主编」把草稿带进对话,主编据它以作者视角成文。
export function DeducePanel({ chars, chapter, onToChief }) {
  const [who, setWho] = useState(chars[0]?.id || '')
  const [draft, setDraft] = useState(null)
  const [busy, setBusy] = useState(false)

  const run = () => {
    if (!who) return
    setBusy(true); setDraft({ who, prose: '' })
    let acc = ''
    const instr = `以「${(chars.find((c) => c.id === who) || {}).name || who}」截至第${chapter}章的限知体验,写这一场的演绎草稿——只含该角色所知所感所见,不要全知旁白。`
    api.chatWrite(instr, {
      chapter, focalizer: who,
      onDelta: (d) => { acc += d; setDraft({ who, prose: acc }) },
      onProposal: (p) => { acc = p.prose || acc; setDraft({ who, prose: acc }) },
      onDone: () => setBusy(false),
      onError: (e) => { setDraft({ who, prose: '演绎失败:' + e }); setBusy(false) },
    })
  }
  const name = (chars.find((c) => c.id === who) || {}).name || who

  return (
    <div>
      <div className="text-f12 text-faint mb-2.5 leading-snug">演绎某角色<b className="text-ink font-medium">这一场的限知体验</b>(他知道什么/看到什么)——作素材,不直接入正文。</div>
      <div className="flex gap-1.5 mb-3">
        <select value={who} onChange={(e) => setWho(e.target.value)}
          className="flex-1 h-8 rounded-lg border border-line bg-canvas px-2 text-f13 text-ink outline-none focus:border-brand cursor-pointer">
          {chars.length === 0 && <option value="">（无角色)</option>}
          {chars.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
        </select>
        <Btn variant="primary" size="sm" onClick={run} disabled={busy || !who}>
          {busy ? <Loader2 size={13} className="animate-spin" /> : <Sparkles size={13} />}演绎第{chapter}章
        </Btn>
      </div>
      {busy && <div className="text-f12 text-faint inline-flex items-center gap-1"><Loader2 size={12} className="animate-spin" />演绎中(走 Hermes,限知渲染)…</div>}
      {!draft && !busy ? <Empty>选角色 → 演绎他这一场的限知草稿</Empty> : draft && (
        <div className="rounded-xl border border-line bg-canvas overflow-hidden">
          <div className="flex items-center gap-2 px-2.5 h-8 border-b border-line bg-soft/40">
            <Sparkles size={12} className="text-brand" />
            <span className="text-f12 font-medium text-ink">{name} · 演绎草稿</span>
            <div className="ml-auto flex gap-0.5">
              <button onClick={() => navigator.clipboard?.writeText(draft.prose)} title="复制" className="w-6 h-6 grid place-items-center rounded text-faint hover:text-ink hover:bg-soft cursor-pointer"><Copy size={12} /></button>
              <button onClick={() => onToChief?.(name, draft.prose)} title="交给主编据此成文" className="inline-flex items-center gap-1 h-6 px-2 rounded text-meta text-brand hover:bg-soft cursor-pointer transition-colors"><ArrowRight size={11} />给主编</button>
            </div>
          </div>
          <div className="manuscript px-3 py-2.5 text-f14 leading-[1.8] whitespace-pre-wrap text-ink max-h-[42vh] overflow-y-auto">{draft.prose}</div>
        </div>
      )}
    </div>
  )
}
