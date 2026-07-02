import { useEffect, useRef, useState } from 'react'
import { Sparkles, Loader2 } from 'lucide-react'
import { api } from './api'
import { useDeduceSel } from './deduceContext'
import { useToast } from './ui/Toast.jsx'

// 演绎中区:据当前选中(truth 或 character_id)显示/编辑/生成并失焦落库。
export function DeduceStage({ seq, meta, onSaved }) {
  const toast = useToast()
  const { selected } = useDeduceSel()
  const [text, setText] = useState('')
  const [busy, setBusy] = useState(false)
  const dirty = useRef(false)
  const chars = meta?.chars || []
  const cur = selected === 'truth'
    ? { name: '场景真相', prose: meta?.scene_truth || '' }
    : (meta?.deductions || []).find((d) => d.character_id === selected)
      || { character_id: selected, character_name: (chars.find((c) => c.id === selected) || {}).name || selected, prose: '' }
  useEffect(() => { setText(cur.prose || ''); dirty.current = false }, [selected, seq]) // eslint-disable-line

  const persist = async (val) => {
    try {
      if (selected === 'truth') {
        await api.patchChapter(seq, { scene_truth: val })
      } else {
        const others = (meta?.deductions || []).filter((d) => d.character_id !== selected)
        await api.patchChapter(seq, { deductions: [...others, { character_id: selected, character_name: cur.character_name, prose: val }] })
      }
      onSaved?.()
    } catch (e) {
      toast(e?.body?.detail || '演绎保存失败,请重试', { tone: 'danger' })
    }
  }
  const blur = () => { if (dirty.current) { dirty.current = false; persist(text) } }

  const gen = () => {
    setBusy(true); let acc = ''
    const instr = selected === 'truth'
      ? `写第${seq}章这一场的「场景真相」:全知冷叙,客观上真正发生了什么,含角色们察觉不到的隐藏机制。据本章大纲/节拍/设定(含私密)。只输出真相正文。`
      : `以「${cur.character_name}」截至第${seq}章的限知,写他这一场的限知投影,分五个小标题:看到/听到、知道、以为(误读)、做了/说了、没察觉的。据场景真相与他的限知帧,只含他所知所感。`
    // 后端写作流事件:proposal_start → proposal_chunk（逐段文本，用于流式预览）→ proposal（完整稿）。
    // 兼容纯 delta 流。全部累进到 acc，完成后落库。
    api.chatWrite(instr, {
      chapter: seq, focalizer: selected === 'truth' ? '' : selected,
      onProposalStart: () => { acc = ''; setText('') },
      onProposalChunk: (c) => { acc += (c?.text ?? c ?? ''); setText(acc) },
      onDelta: (d) => { acc += d; setText(acc) },
      onProposal: (p) => { acc = p.prose ?? p.text ?? acc; setText(acc) },
      onDone: () => { setBusy(false); const v = acc.trim(); if (v) { dirty.current = true; persist(v) } },
      onError: (e) => { setBusy(false); toast('演绎失败:' + e, { tone: 'danger' }) },  // 不动 text,保留已有内容
    })
  }

  return (
    <div className="max-w-[48rem] mx-auto px-6 py-6 h-full flex flex-col min-h-0">
      <div className="flex items-center gap-2 mb-3">
        <h3 className="text-[14px] font-semibold text-ink">{selected === 'truth' ? '场景真相 · 全知' : `${cur.character_name} · 限知投影`}</h3>
        <button onClick={gen} disabled={busy}
          className="ml-auto h-7 px-3 rounded-lg bg-brand text-brandfg text-[12px] inline-flex items-center gap-1 cursor-pointer hover:brightness-110 disabled:opacity-40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand/40">
          {busy ? <Loader2 size={13} className="animate-spin" /> : <Sparkles size={13} />}{busy ? '演绎中…' : '生成'}
        </button>
      </div>
      <textarea value={text} onChange={(e) => { setText(e.target.value); dirty.current = true }} onBlur={blur}
        placeholder={selected === 'truth' ? '这一场客观真正发生了什么(全知,含隐藏机制)…' : '看到/听到 · 知道 · 以为(误读) · 做了/说了 · 没察觉的'}
        className="flex-1 min-h-0 w-full rounded-xl border border-line bg-canvas px-4 py-3 text-[14px] leading-[1.85] text-ink outline-none focus:border-brand resize-none" />
      <div className="text-[11.5px] text-faint mt-2">失焦自动存;所有角色投影都从「场景真相」派生,保持一致。</div>
    </div>
  )
}
