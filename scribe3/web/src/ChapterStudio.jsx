import { useEffect, useRef, useState } from 'react'
import {
  ChevronLeft, ChevronRight, ListChecks, AlignLeft, FileEdit, BookText,
  Plus, Trash2, Check, Save, Loader2,
} from 'lucide-react'
import { api } from './api'
import { WriteLayout } from './WriteLayout'
import { useToast } from './ui/Toast.jsx'

// 章四阶段:大纲(synopsis)→ 节拍(beats)→ 草稿(draft)→ 正文(prose/WriteLayout)。
// 大纲/节拍 patchChapter;草稿 saveDraft/latestDraft;正文整体复用 WriteLayout(护栏/QC/帧/伏笔/版本不丢)。
const PHASES = [
  { key: 'outline', label: '大纲', icon: AlignLeft },
  { key: 'beats', label: '节拍', icon: ListChecks },
  { key: 'draft', label: '草稿', icon: FileEdit },
  { key: 'final', label: '正文', icon: BookText },
]

// ——— 大纲:textarea,失焦 patchChapter({synopsis}) ———
function OutlineTab({ seq, value, onSaved }) {
  const [text, setText] = useState(value || '')
  const [saving, setSaving] = useState(false)
  const dirtyRef = useRef(false)
  useEffect(() => { setText(value || ''); dirtyRef.current = false }, [seq, value])

  const flush = async () => {
    if (!dirtyRef.current) return
    setSaving(true)
    try { await api.patchChapter(seq, { synopsis: text }); dirtyRef.current = false; onSaved?.() }
    finally { setSaving(false) }
  }

  return (
    <div className="max-w-[44rem] mx-auto px-6 py-6 h-full flex flex-col">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-[13px] font-semibold text-ink">本章大纲 · 一句话到一段话写清这章要发生什么</h3>
        <span className="text-[11px] text-faint">{saving ? '保存中…' : '失焦自动保存'}</span>
      </div>
      <textarea
        value={text}
        onChange={(e) => { setText(e.target.value); dirtyRef.current = true }}
        onBlur={flush}
        placeholder="例:焦三被请进炉坊,第一次见到铜炉——他还不知道这炉子认主。本章建立悬念,埋『炉认主』伏笔。"
        className="flex-1 min-h-[240px] w-full rounded-xl border border-line bg-canvas px-4 py-3 text-[14px] leading-relaxed text-ink outline-none focus:border-brand resize-none"
      />
      <div className="text-[11.5px] text-faint mt-2 leading-snug">大纲喂给主编当本章写作纲领;在右栏可与主编讨论怎么展开。</div>
    </div>
  )
}

// ——— 节拍:beats 列表(增/删/打勾/上下移),patchChapter({beats}) ———
function BeatsTab({ seq, value, onSaved }) {
  const [beats, setBeats] = useState(() => Array.isArray(value) ? value : [])
  const [draft, setDraft] = useState('')
  const [saving, setSaving] = useState(false)
  useEffect(() => { setBeats(Array.isArray(value) ? value : []) }, [seq, value])

  const persist = async (next) => {
    setBeats(next)
    setSaving(true)
    try { await api.patchChapter(seq, { beats: next }); onSaved?.() }
    finally { setSaving(false) }
  }
  const add = () => {
    const t = draft.trim()
    if (!t) return
    setDraft('')
    persist([...beats, { text: t, done: false }])
  }
  const toggle = (i) => persist(beats.map((b, idx) => idx === i ? { ...b, done: !b.done } : b))
  const remove = (i) => persist(beats.filter((_, idx) => idx !== i))
  const move = (i, dir) => {
    const j = i + dir
    if (j < 0 || j >= beats.length) return
    const next = [...beats]
    ;[next[i], next[j]] = [next[j], next[i]]
    persist(next)
  }

  return (
    <div className="max-w-[44rem] mx-auto px-6 py-6">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-[13px] font-semibold text-ink">节拍 · 把这章拆成有序的小节点</h3>
        <span className="text-[11px] text-faint">{saving ? '保存中…' : `${beats.filter((b) => b.done).length}/${beats.length} 完成`}</span>
      </div>

      <div className="flex gap-2 mb-4">
        <input
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); add() } }}
          placeholder="加一个节拍…(Enter 添加)"
          className="flex-1 h-9 rounded-lg border border-line bg-canvas px-3 text-[13px] text-ink outline-none focus:border-brand"
        />
        <button onClick={add} className="h-9 px-3 rounded-lg bg-brand text-white text-[13px] inline-flex items-center gap-1 cursor-pointer hover:opacity-90">
          <Plus size={15} />加
        </button>
      </div>

      {beats.length === 0 ? (
        <div className="text-[13px] text-faint text-center py-10 rounded-xl border border-dashed border-line">还没有节拍。把这章想发生的事一条条列出来。</div>
      ) : (
        <div className="space-y-1.5">
          {beats.map((b, i) => (
            <div key={i} className="group flex items-center gap-2 rounded-lg border border-line bg-canvas px-2.5 py-2">
              <button onClick={() => toggle(i)}
                className={`w-5 h-5 rounded-md border shrink-0 inline-flex items-center justify-center cursor-pointer transition-colors ${b.done ? 'bg-brand border-brand text-white' : 'border-line hover:border-brand'}`}>
                {b.done && <Check size={13} />}
              </button>
              <span className={`flex-1 text-[13.5px] leading-snug ${b.done ? 'text-faint line-through' : 'text-ink'}`}>{b.text}</span>
              <div className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity shrink-0">
                <button onClick={() => move(i, -1)} disabled={i === 0} title="上移"
                  className="w-6 h-6 rounded inline-flex items-center justify-center text-faint hover:bg-soft hover:text-ink disabled:opacity-30 cursor-pointer">↑</button>
                <button onClick={() => move(i, 1)} disabled={i === beats.length - 1} title="下移"
                  className="w-6 h-6 rounded inline-flex items-center justify-center text-faint hover:bg-soft hover:text-ink disabled:opacity-30 cursor-pointer">↓</button>
                <button onClick={() => remove(i)} title="删除"
                  className="w-6 h-6 rounded inline-flex items-center justify-center text-faint hover:bg-soft hover:text-danger cursor-pointer"><Trash2 size={13} /></button>
              </div>
            </div>
          ))}
        </div>
      )}
      <div className="text-[11.5px] text-faint mt-4 leading-snug">节拍是草稿的骨架;右栏可让主编据节拍生成草稿。</div>
    </div>
  )
}

// ——— 草稿:编辑器,初值 latestDraft,存草稿 saveDraft;采用=进正文(回调切到正文 tab) ———
function DraftTab({ seq, onAdopt }) {
  const toast = useToast()
  const [text, setText] = useState('')
  const [summary, setSummary] = useState('')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    let alive = true
    setLoading(true)
    api.latestDraft(seq)
      .then((d) => { if (alive) { setText(d?.prose || ''); setSummary(d?.summary || '') } })
      .catch(() => {})
      .finally(() => { if (alive) setLoading(false) })
    return () => { alive = false }
  }, [seq])

  const saveDraft = async () => {
    setSaving(true)
    try { await api.saveDraft(seq, text, summary); toast('草稿已存') }
    catch (e) { toast('存草稿失败:' + (e.message || ''), { tone: 'danger' }) }
    finally { setSaving(false) }
  }
  const adopt = async () => {
    setSaving(true)
    try { await api.saveDraft(seq, text, summary); onAdopt?.(text); toast('已采用为正文,切到正文 tab 继续打磨') }
    catch (e) { toast('采用失败:' + (e.message || ''), { tone: 'danger' }) }
    finally { setSaving(false) }
  }

  if (loading) return <div className="flex items-center justify-center py-16 text-faint"><Loader2 size={18} className="animate-spin mr-2" />加载草稿…</div>

  const wc = text.replace(/\s/g, '').length
  return (
    <div className="max-w-[48rem] mx-auto px-6 py-6 h-full flex flex-col">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-[13px] font-semibold text-ink">草稿 · 自由打磨,满意后采用为正文</h3>
        <div className="flex items-center gap-2">
          <span className="text-[11px] text-faint tnum">{wc} 字</span>
          <button onClick={saveDraft} disabled={saving}
            className="h-7 px-2.5 rounded-lg border border-line text-[12px] text-ink hover:bg-soft inline-flex items-center gap-1 cursor-pointer disabled:opacity-40">
            <Save size={13} />存草稿
          </button>
          <button onClick={adopt} disabled={saving || !text.trim()}
            className="h-7 px-2.5 rounded-lg bg-brand text-white text-[12px] inline-flex items-center gap-1 cursor-pointer hover:opacity-90 disabled:opacity-40">
            <Check size={13} />采用为正文
          </button>
        </div>
      </div>
      <input
        value={summary}
        onChange={(e) => setSummary(e.target.value)}
        placeholder="给这版草稿一句备注(可留空)"
        className="w-full h-8 rounded-lg border border-line bg-canvas px-3 text-[12.5px] text-ink outline-none focus:border-brand mb-2"
      />
      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder="在此自由起草,或在右栏让主编据大纲/节拍生成草稿。满意后『采用为正文』搬进正文 tab 做护栏/QC 打磨。"
        className="flex-1 min-h-[300px] w-full rounded-xl border border-line bg-canvas px-4 py-3 text-[14px] leading-relaxed text-ink outline-none focus:border-brand resize-none"
      />
      <div className="text-[11.5px] text-faint mt-2 leading-snug">草稿区不跑护栏/QC,放手写;正文区才上全套校验。</div>
    </div>
  )
}

/**
 * 章工作台:顶部四阶段 tab + 章导航。
 * 大纲/节拍/草稿 = ChapterStudio 自带轻量编辑器(patchChapter/saveDraft);
 * 正文 = 整体复用 WriteLayout(护栏/QC/帧/伏笔/版本/检索/主编对话全保留)。
 */
export function ChapterStudio({ work, seq, sceneIdx, onSeqChange }) {
  const [phase, setPhase] = useState(() => localStorage.getItem('s3.chapter.phase') || 'final')
  const [meta, setMeta] = useState(null)   // {title, synopsis, beats}
  const [loading, setLoading] = useState(true)
  const [refresh, setRefresh] = useState(0)

  const setPhaseP = (p) => { setPhase(p); localStorage.setItem('s3.chapter.phase', p) }

  // F-06 场景级跳转:点项目树「场景」节点(sceneIdx 非空)→ 强制切到「正文」tab,
  // 由 WriteLayout 在正文加载后调 focusScene(sceneIdx) 滚到对应场景段。
  useEffect(() => {
    if (sceneIdx != null && phase !== 'final') setPhaseP('final')
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sceneIdx])

  // 大纲/节拍 tab 用:拉章 synopsis/beats/title(正文 tab 由 WriteLayout 自己拉,互不干扰)
  useEffect(() => {
    if (phase === 'final') { setLoading(false); return }
    let alive = true
    setLoading(true)
    api.chapter(seq)
      .then((ch) => { if (alive) setMeta({ title: ch?.title || '', synopsis: ch?.synopsis || '', beats: ch?.beats || [] }) })
      .catch(() => { if (alive) setMeta({ title: '', synopsis: '', beats: [] }) })
      .finally(() => { if (alive) setLoading(false) })
    return () => { alive = false }
  }, [seq, phase, refresh])

  // 正文 tab:整体交给 WriteLayout(自带顶栏:章导航/视角/护栏/保存/存为正文)。
  if (phase === 'final') {
    return (
      <div className="h-full flex flex-col min-h-0">
        <PhaseBar seq={seq} phase={phase} onPhase={setPhaseP} onSeqChange={onSeqChange} />
        <div className="flex-1 min-h-0">
          <WriteLayout key={`${work}-${seq}`} work={work} seq={seq} sceneIdx={sceneIdx} onSeqChange={onSeqChange} />
        </div>
      </div>
    )
  }

  return (
    <div className="h-full flex flex-col min-h-0 bg-canvas">
      <PhaseBar seq={seq} phase={phase} onPhase={setPhaseP} onSeqChange={onSeqChange} />
      <div className="flex-1 min-h-0 overflow-y-auto">
        {loading ? (
          <div className="flex items-center justify-center py-16 text-faint"><Loader2 size={18} className="animate-spin mr-2" />加载…</div>
        ) : phase === 'outline' ? (
          <OutlineTab seq={seq} value={meta?.synopsis} onSaved={() => setRefresh((r) => r + 1)} />
        ) : phase === 'beats' ? (
          <BeatsTab seq={seq} value={meta?.beats} onSaved={() => setRefresh((r) => r + 1)} />
        ) : phase === 'draft' ? (
          <DraftTab seq={seq} onAdopt={() => setPhaseP('final')} />
        ) : null}
      </div>
    </div>
  )
}

// 顶部:章导航 + 四阶段 tab
function PhaseBar({ seq, phase, onPhase, onSeqChange }) {
  return (
    <div className="shrink-0 border-b border-line bg-surface h-11 flex items-center gap-3 px-3">
      <div className="flex items-center gap-1 shrink-0">
        <button onClick={() => onSeqChange?.(Math.max(1, (seq || 1) - 1))} title="上一章"
          className="w-7 h-7 rounded-lg text-faint hover:bg-soft hover:text-ink inline-flex items-center justify-center cursor-pointer"><ChevronLeft size={16} /></button>
        <span className="text-[13px] text-ink tnum whitespace-nowrap px-1">第 {seq} 章</span>
        <button onClick={() => onSeqChange?.((seq || 1) + 1)} title="下一章"
          className="w-7 h-7 rounded-lg text-faint hover:bg-soft hover:text-ink inline-flex items-center justify-center cursor-pointer"><ChevronRight size={16} /></button>
      </div>
      <div className="flex items-center gap-0.5 rounded-lg bg-soft/60 p-0.5">
        {PHASES.map((p) => {
          const Icon = p.icon
          const on = phase === p.key
          return (
            <button key={p.key} onClick={() => onPhase(p.key)}
              className={`h-7 px-2.5 rounded-md text-[12.5px] inline-flex items-center gap-1.5 transition-colors cursor-pointer ${on ? 'bg-surface text-brand shadow-sm ring-1 ring-line' : 'text-faint hover:text-ink'}`}>
              <Icon size={13} />{p.label}
            </button>
          )
        })}
      </div>
    </div>
  )
}
