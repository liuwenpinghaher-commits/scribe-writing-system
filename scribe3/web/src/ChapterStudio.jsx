import { useEffect, useRef, useState } from 'react'
import {
  ChevronLeft, ChevronRight, ListChecks, AlignLeft, FileEdit, BookText,
  Plus, Trash2, Check, Save, Loader2, Sparkles,
} from 'lucide-react'
import { api } from './api'
import { WriteLayout } from './WriteLayout'
import { FramePanel } from './FramePanel'
import { DeducePanel } from './DeducePanel'
import { DeduceStage } from './DeduceStage'
import { DeduceProvider } from './deduceContext'
import { cn } from './lib/utils'
import { useToast } from './ui/Toast.jsx'
import { useChiefSlot } from './ChiefSlotContext'

// 大纲/节拍/草稿阶段的左侧数据面板(与正文阶段一致的三栏体验):帧/意图 · 演绎 · 伏笔。
// 复用 FramePanel/DeducePanel 独立组件;伏笔为本章需埋/收的清单。带文字标签 tab 条,常显。
function ChapterSidePanel({ seq, focalizer }) {
  const [tab, setTab] = useState('frame')
  const [chars, setChars] = useState([])
  const [promises, setPromises] = useState([])
  useEffect(() => {
    api.entities().then((es) => setChars(es.filter((e) => e.kind === 'character'))).catch(() => {})
    api.promises().then((ps) => setPromises(Array.isArray(ps) ? ps : [])).catch(() => {})
  }, [seq])
  const caps = [
    { key: 'frame', label: '帧/意图', render: () => <FramePanel focalizer={focalizer} chapter={seq} /> },
    { key: 'deduce', label: '演绎', render: () => <DeducePanel chars={chars} chapter={seq} /> },
    { key: 'promise', label: '伏笔', render: () => (
      <div>
        <div className="text-[11px] text-faint uppercase tracking-wider mb-1.5">本章伏笔 · 埋/收</div>
        {promises.length === 0 ? <div className="text-[13px] text-faint/50">无</div> : promises.map((p) => (
          <div key={p.id} className="mb-2 pb-2 border-b border-line/50 last:border-0">
            <div className="text-[12.5px] text-ink leading-snug">{p.text}</div>
            <div className="text-[10px] text-faint mt-0.5">埋:第{p.setup_chapter ?? '—'}章 · {p.status === 'paid' ? '已收' : '待收'}</div>
          </div>
        ))}
      </div>
    ) },
  ]
  const active = caps.find((c) => c.key === tab) || caps[0]
  return (
    <div className="shrink-0 w-[250px] border-r border-line bg-surface flex flex-col min-h-0">
      <div className="shrink-0 flex items-center gap-0.5 px-1.5 pt-2 pb-1 border-b border-line overflow-x-auto">
        {caps.map((c) => (
          <button key={c.key} onClick={() => setTab(c.key)}
            className={cn('shrink-0 px-2 h-6 rounded-md text-[11.5px] whitespace-nowrap transition-colors cursor-pointer',
              tab === c.key ? 'bg-brand text-brandfg font-medium' : 'text-faint hover:bg-soft hover:text-ink')}>
            {c.label}
          </button>
        ))}
      </div>
      <div className="flex-1 min-h-0 overflow-y-auto p-3">{active.render()}</div>
    </div>
  )
}

// 章四阶段:大纲(synopsis)→ 节拍(beats)→ 草稿(draft)→ 正文(prose/WriteLayout)。
// 大纲/节拍 patchChapter;草稿 saveDraft/latestDraft;正文整体复用 WriteLayout(护栏/QC/帧/伏笔/版本不丢)。
const PHASES = [
  { key: 'outline', label: '大纲', icon: AlignLeft },
  { key: 'beats', label: '节拍', icon: ListChecks },
  { key: 'deduce', label: '演绎', icon: Sparkles },
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

  // 把当前阶段发布给右栏 ChiefDock:正文=写作槽;大纲/节拍/草稿=讨论(右栏 chat 不再消失)。
  const { setChapterPhase } = useChiefSlot()
  useEffect(() => { setChapterPhase(phase); return () => setChapterPhase(null) }, [phase, setChapterPhase])

  // F-06 场景级跳转:点项目树「场景」节点(sceneIdx 非空)→ 强制切到「正文」tab,
  // 由 WriteLayout 在正文加载后调 focusScene(sceneIdx) 滚到对应场景段。
  useEffect(() => {
    if (sceneIdx != null && phase !== 'final') setPhaseP('final')
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sceneIdx])

  // 大纲/节拍 tab 用:拉章 synopsis/beats/title(正文 tab 由 WriteLayout 自己拉,互不干扰)
  // 仅在切章/切阶段时显"加载中"占位;refresh(失焦落库后回读)静默刷新,不卸载中区编辑器
  // ——否则演绎生成落库触发 refresh→loading→DeduceStage 卸载重挂,竞态把刚生成的 scene_truth 冲掉。
  const metaKey = useRef('')
  useEffect(() => {
    if (phase === 'final') { setLoading(false); return }
    let alive = true
    const key = `${seq}|${phase}`
    if (metaKey.current !== key) { metaKey.current = key; setLoading(true) }
    api.chapter(seq)
      .then((ch) => { if (alive) setMeta((m) => ({ ...(m || {}), title: ch?.title || '', synopsis: ch?.synopsis || '', beats: ch?.beats || [], focalizer: ch?.focalizer || '', scene_truth: ch?.scene_truth || '', deductions: ch?.deductions || [], involved_characters: ch?.involved_characters || [] })) })
      .catch(() => { if (alive) setMeta((m) => ({ ...(m || {}), title: '', synopsis: '', beats: [], focalizer: '', scene_truth: '', deductions: [], involved_characters: [] })) })
      .finally(() => { if (alive) setLoading(false) })
    api.entities().then((es) => { if (alive) setMeta((m) => ({ ...(m || {}), chars: es.filter((e) => e.kind === 'character') })) }).catch(() => {})
    return () => { alive = false }
  }, [seq, phase, refresh])

  // 正文 tab:整体交给 WriteLayout(自带顶栏:章导航/视角/护栏/保存/存为正文)。
  // 两条 return 路径都包进 DeduceProvider,使中区 DeduceStage 与后续左栏演绎树共享选中态。
  if (phase === 'final') {
    return (
      <DeduceProvider>
        <div className="h-full flex flex-col min-h-0">
          <PhaseBar seq={seq} phase={phase} onPhase={setPhaseP} onSeqChange={onSeqChange} />
          <div className="flex-1 min-h-0">
            <WriteLayout key={`${work}-${seq}`} work={work} seq={seq} sceneIdx={sceneIdx} onSeqChange={onSeqChange} />
          </div>
        </div>
      </DeduceProvider>
    )
  }

  return (
    <DeduceProvider>
      <div className="h-full flex flex-col min-h-0 bg-canvas">
        <PhaseBar seq={seq} phase={phase} onPhase={setPhaseP} onSeqChange={onSeqChange} />
        {/* 中区只负责阶段编辑器;数据面板(帧/演绎/伏笔…)已上移到左栏 LeftDock,右栏主编由 RightDock 承载 */}
        <div className="flex-1 min-h-0 overflow-y-auto">
          {loading ? (
            <div className="flex items-center justify-center py-16 text-faint"><Loader2 size={18} className="animate-spin mr-2" />加载…</div>
          ) : phase === 'outline' ? (
            <OutlineTab seq={seq} value={meta?.synopsis} onSaved={() => setRefresh((r) => r + 1)} />
          ) : phase === 'beats' ? (
            <BeatsTab seq={seq} value={meta?.beats} onSaved={() => setRefresh((r) => r + 1)} />
          ) : phase === 'deduce' ? (
            <DeduceStage seq={seq} meta={meta} onSaved={() => setRefresh((r) => r + 1)} />
          ) : phase === 'draft' ? (
            <DraftTab seq={seq} onAdopt={() => setPhaseP('final')} />
          ) : null}
        </div>
      </div>
    </DeduceProvider>
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
