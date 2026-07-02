import { useEffect, useRef, useState } from 'react'
import {
  ChevronLeft, ChevronRight, ChevronUp, ChevronDown, ListChecks, AlignLeft, FileEdit, BookText,
  Plus, Trash2, Check, Save, Loader2, Sparkles,
} from 'lucide-react'
import { api } from './api'
import { WriteLayout } from './WriteLayout'
import { DeduceStage } from './DeduceStage'
import { useToast } from './ui/Toast.jsx'
import { useChiefSlot } from './ChiefSlotContext'
import { Btn, Input, Textarea } from './ui.jsx'

// 章四阶段:大纲(synopsis)→ 节拍(beats)→ 草稿(draft)→ 正文(prose/WriteLayout)。
// 大纲/节拍 patchChapter;草稿 saveDraft/latestDraft;正文整体复用 WriteLayout(护栏/QC/帧/伏笔/版本不丢)。
const PHASES = [
  { key: 'outline', label: '大纲', icon: AlignLeft },
  { key: 'beats', label: '节拍', icon: ListChecks },
  { key: 'deduce', label: '演绎', icon: Sparkles },
  { key: 'draft', label: '草稿', icon: FileEdit },
  { key: 'final', label: '正文', icon: BookText },
]

// 中区各阶段统一容器留白(P1):统一 max-w / py,消除三种 max-w、两种 py。
const STAGE_WRAP = 'max-w-[48rem] mx-auto px-6 py-6 h-full flex flex-col min-h-0'
// hover 才显的行内操作(移动/删除):键盘 Tab 聚焦 + 触屏无 hover 时也可达。
const HOVER_ACTIONS = 'opacity-0 group-hover:opacity-100 focus-within:opacity-100 [@media(hover:none)]:opacity-100 transition-opacity'

// ——— 阶段 meta 摘要条(P1):后端已有 focalizer/涉及角色/演绎/字数,在每个阶段顶部只读呈现 ———
function MetaBar({ meta, wordCount }) {
  if (!meta) return null
  const chars = meta.chars || []
  const focName = meta.focalizer ? ((chars.find((c) => c.id === meta.focalizer) || {}).name || meta.focalizer) : '未设'
  const involved = meta.involved_characters || []
  const done = (meta.deductions || []).filter((d) => (d.prose || '').trim()).length
  const wc = wordCount != null ? wordCount : (meta.synopsis ? null : null)
  return (
    <div className="text-f11 text-faint flex items-center gap-2 flex-wrap mb-2 leading-snug">
      <span>视角:{focName}</span>
      <span className="opacity-50">·</span>
      <span>涉及角色 {done}/{involved.length} 已演绎</span>
      {wc != null && <><span className="opacity-50">·</span><span className="tnum">字数 {wc}</span></>}
    </div>
  )
}

// ——— 大纲:textarea,失焦 patchChapter({synopsis}) ———
function OutlineTab({ seq, value, meta, onSaved }) {
  const toast = useToast()
  const [text, setText] = useState(value || '')
  const [saving, setSaving] = useState(false)
  const dirtyRef = useRef(false)
  useEffect(() => { setText(value || ''); dirtyRef.current = false }, [seq, value])

  const flush = async () => {
    if (!dirtyRef.current) return
    setSaving(true)
    try { await api.patchChapter(seq, { synopsis: text }); dirtyRef.current = false; onSaved?.() }
    catch (e) { toast(e?.body?.detail || '大纲保存失败', { tone: 'danger' }) }
    finally { setSaving(false) }
  }

  return (
    <div className={STAGE_WRAP}>
      <MetaBar meta={meta} wordCount={meta?.proseWords} />
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-f13 font-semibold text-ink">本章大纲 · 一句话到一段话写清这章要发生什么</h3>
        <span className="text-f11 text-faint">{saving ? '保存中…' : '失焦自动保存'}</span>
      </div>
      <Textarea
        value={text}
        onChange={(e) => { setText(e.target.value); dirtyRef.current = true }}
        onBlur={flush}
        placeholder="例:焦三被请进炉坊,第一次见到铜炉——他还不知道这炉子认主。本章建立悬念,埋『炉认主』伏笔。"
        className="flex-1 min-h-0 rounded-xl px-4 py-3 text-f14 resize-none"
      />
      <div className="text-f12 text-faint mt-2 leading-snug">大纲喂给主编当本章写作纲领;在右栏可与主编讨论怎么展开。</div>
    </div>
  )
}

// ——— 节拍:beats 列表(增/删/打勾/上下移),patchChapter({beats}) ———
function BeatsTab({ seq, value, meta, onSaved }) {
  const toast = useToast()
  const [beats, setBeats] = useState(() => Array.isArray(value) ? value : [])
  const [draft, setDraft] = useState('')
  const [saving, setSaving] = useState(false)
  useEffect(() => { setBeats(Array.isArray(value) ? value : []) }, [seq, value])

  const persist = async (next) => {
    setBeats(next)
    setSaving(true)
    try { await api.patchChapter(seq, { beats: next }); onSaved?.() }
    catch (e) { toast(e?.body?.detail || '节拍保存失败', { tone: 'danger' }) }
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
    <div className={STAGE_WRAP}>
      <MetaBar meta={meta} wordCount={meta?.proseWords} />
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-f13 font-semibold text-ink">节拍 · 把这章拆成有序的小节点</h3>
        <span className="text-f11 text-faint">{saving ? '保存中…' : `${beats.filter((b) => b.done).length}/${beats.length} 完成`}</span>
      </div>

      <div className="flex gap-2 mb-4">
        <Input
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); add() } }}
          placeholder="加一个节拍…(Enter 添加)"
        />
        <Btn variant="primary" onClick={add} className="h-9 shrink-0">
          <Plus size={15} />加
        </Btn>
      </div>

      <div className="flex-1 min-h-0 overflow-y-auto">
      {beats.length === 0 ? (
        <div className="text-f13 text-faint text-center py-10 rounded-xl border border-dashed border-line">还没有节拍。把这章想发生的事一条条列出来。</div>
      ) : (
        <div className="space-y-1.5">
          {beats.map((b, i) => (
            <div key={i} className="group flex items-center gap-2 rounded-lg border border-line bg-canvas px-2.5 py-2">
              <button onClick={() => toggle(i)}
                className={`w-5 h-5 rounded-md border shrink-0 inline-flex items-center justify-center cursor-pointer transition-colors ${b.done ? 'bg-brand border-brand text-brandfg' : 'border-line hover:border-brand'}`}>
                {b.done && <Check size={13} />}
              </button>
              <span className={`flex-1 text-f14 leading-snug ${b.done ? 'text-faint line-through' : 'text-ink'}`}>{b.text}</span>
              <div className={`flex items-center gap-0.5 shrink-0 ${HOVER_ACTIONS}`}>
                <Btn variant="ghost" size="xs" icon onClick={() => move(i, -1)} disabled={i === 0} title="上移" aria-label="上移"><ChevronUp size={13} /></Btn>
                <Btn variant="ghost" size="xs" icon onClick={() => move(i, 1)} disabled={i === beats.length - 1} title="下移" aria-label="下移"><ChevronDown size={13} /></Btn>
                <Btn variant="ghost" size="xs" icon onClick={() => remove(i)} title="删除" aria-label="删除" className="hover:text-danger"><Trash2 size={13} /></Btn>
              </div>
            </div>
          ))}
        </div>
      )}
      <div className="text-f12 text-faint mt-4 leading-snug">节拍是草稿的骨架;右栏可让主编据节拍生成草稿。</div>
      </div>
    </div>
  )
}

// ——— 草稿:编辑器,初值 latestDraft,存草稿 saveDraft;采用=进正文(回调切到正文 tab) ———
function DraftTab({ seq, meta, onAdopt }) {
  const toast = useToast()
  const { draftProposal, setDraftProposal } = useChiefSlot()
  const [text, setText] = useState('')
  const [summary, setSummary] = useState('')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  // 待落草稿:仅当本次提议属于当前章且正文非空才提示(防切章串到旧章)。
  const pending = draftProposal && draftProposal.seq === seq && (draftProposal.prose || '').trim() ? draftProposal : null
  // 落进后置 dirty,靠既有 flush(切章/存草稿)落库;同时清除待落。
  const fillDraft = () => {
    if (!pending) return
    setText(pending.prose); draftRef.current.dirty = true
    setDraftProposal(null); toast('已填入草稿框')
  }
  const appendDraft = () => {
    if (!pending) return
    setText((prev) => (prev ? prev + '\n\n' : '') + pending.prose); draftRef.current.dirty = true
    setDraftProposal(null); toast('已追加到草稿')
  }
  // 换章防丢:draftRef 只持「实时 text/summary/dirty」(渲染时刷新);seq 不放 ref
  // ——因 draftRef.current.seq=seq 会在换章渲染时先变成新 seq,导致 cleanup 拿错章号。
  // 旧章 seq 改由 effect 闭包捕获(myseq),cleanup 时用它,保证 flush 落到正确的旧章。
  const draftRef = useRef({ text: '', summary: '', dirty: false })
  draftRef.current.text = text
  draftRef.current.summary = summary

  useEffect(() => {
    let alive = true
    const myseq = seq  // 闭包捕获本 effect 的章号,cleanup 用它 = 真旧章号
    setLoading(true)
    api.latestDraft(seq)
      .then((d) => { if (alive) { setText(d?.prose || ''); setSummary(d?.summary || ''); draftRef.current.dirty = false } })
      .catch(() => {})
      .finally(() => { if (alive) setLoading(false) })
    // cleanup(seq 变化/卸载):若旧章 dirty,先 flush 旧章。text/summary 从 draftRef 读——
    // 此刻 state 尚未被新 effect 的 setText 重置(重置是异步),故仍是旧章正文。
    return () => {
      alive = false
      const { text: oldText, summary: oldSummary, dirty } = draftRef.current
      if (dirty && myseq != null) {
        draftRef.current.dirty = false
        api.saveDraft(myseq, oldText, oldSummary)
          .catch(() => { toast(`第 ${myseq} 章草稿自动保存失败,请回该章手动存草稿`, { tone: 'danger' }) })
      }
    }
  }, [seq])

  const saveDraft = async () => {
    setSaving(true)
    try { await api.saveDraft(seq, text, summary); draftRef.current.dirty = false; toast('草稿已存') }
    catch (e) { toast('存草稿失败:' + (e.message || ''), { tone: 'danger' }) }
    finally { setSaving(false) }
  }
  const adopt = async () => {
    setSaving(true)
    try { await api.saveDraft(seq, text, summary); draftRef.current.dirty = false; onAdopt?.(text); toast('已采用为正文,切到正文 tab 继续打磨') }
    catch (e) { toast('采用失败:' + (e.message || ''), { tone: 'danger' }) }
    finally { setSaving(false) }
  }

  if (loading) return <div className="flex items-center justify-center py-16 text-faint"><Loader2 size={18} className="animate-spin mr-2" />加载草稿…</div>

  const wc = text.replace(/\s/g, '').length
  return (
    <div className={STAGE_WRAP}>
      <MetaBar meta={meta} wordCount={wc} />
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-f13 font-semibold text-ink">草稿 · 自由打磨,满意后采用为正文</h3>
        <div className="flex items-center gap-2">
          <span className="text-f11 text-faint tnum">{wc} 字</span>
          <Btn variant="soft" size="sm" onClick={saveDraft} disabled={saving}>
            <Save size={13} />存草稿
          </Btn>
          <Btn variant="primary" size="sm" onClick={adopt} disabled={saving || !text.trim()}>
            <Check size={13} />采用为正文
          </Btn>
        </div>
      </div>
      {pending && (
        <div className="mb-2 rounded-xl border border-brand/20 bg-brand/10 text-brand px-3 py-2 flex items-center gap-2 flex-wrap">
          <Sparkles size={14} className="shrink-0" />
          <span className="text-f13 flex-1 min-w-0">主编生成了本章草稿({pending.prose.replace(/\s/g, '').length} 字),可直接落进草稿框。</span>
          <div className="flex items-center gap-1.5 shrink-0">
            <Btn variant="primary" size="sm" onClick={fillDraft}>填入草稿框</Btn>
            <Btn variant="soft" size="sm" onClick={appendDraft}>追加到草稿</Btn>
          </div>
        </div>
      )}
      <Input
        value={summary}
        onChange={(e) => { setSummary(e.target.value); draftRef.current.dirty = true }}
        placeholder="给这版草稿一句备注(可留空)"
        className="h-8 mb-2"
      />
      <Textarea
        value={text}
        onChange={(e) => { setText(e.target.value); draftRef.current.dirty = true }}
        placeholder="在此自由起草,或在右栏让主编据大纲/节拍生成草稿。满意后『采用为正文』搬进正文 tab 做护栏/QC 打磨。"
        className="flex-1 min-h-0 rounded-xl px-4 py-3 text-f14 resize-none"
      />
      <div className="text-f12 text-faint mt-2 leading-snug">草稿区不跑护栏/QC,放手写;正文区才上全套校验。</div>
    </div>
  )
}

/**
 * 章工作台:顶部四阶段 tab + 章导航。
 * 大纲/节拍/草稿 = ChapterStudio 自带轻量编辑器(patchChapter/saveDraft);
 * 正文 = 整体复用 WriteLayout(护栏/QC/帧/伏笔/版本/检索/主编对话全保留)。
 */
export function ChapterStudio({ work, seq, sceneIdx, onSeqChange }) {
  const toast = useToast()
  const [phase, setPhase] = useState(() => localStorage.getItem('s3.chapter.phase') || 'final')
  const [meta, setMeta] = useState(null)   // {title, synopsis, beats}
  const [loading, setLoading] = useState(true)
  const [refresh, setRefresh] = useState(0)

  // 草稿软门:切到草稿时若有涉及角色未演绎→黄色 toast 提示(不阻断,仍切进)。
  const setPhaseP = (p) => {
    if (p === 'draft' && meta) {
      const deds = meta.deductions || []
      const done = new Set(deds.filter((d) => (d.prose || '').trim()).map((d) => d.character_id))
      const pending = (meta.involved_characters || []).filter((id) => !done.has(id))
      if (pending.length) toast(`还有 ${pending.length} 个涉及角色未演绎,可回「演绎」补(不影响继续)`, { tone: 'warn' })
    }
    setPhase(p); localStorage.setItem('s3.chapter.phase', p)
  }

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
      .then((ch) => { if (alive) setMeta((m) => ({ ...(m || {}), title: ch?.title || '', synopsis: ch?.synopsis || '', beats: ch?.beats || [], focalizer: ch?.focalizer || '', scene_truth: ch?.scene_truth || '', deductions: ch?.deductions || [], involved_characters: ch?.involved_characters || [], proseWords: (ch?.prose || '').replace(/\s/g, '').length })) })
      .catch(() => { if (alive) setMeta((m) => ({ ...(m || {}), title: '', synopsis: '', beats: [], focalizer: '', scene_truth: '', deductions: [], involved_characters: [], proseWords: 0 })) })
      .finally(() => { if (alive) setLoading(false) })
    api.entities().then((es) => { if (alive) setMeta((m) => ({ ...(m || {}), chars: es.filter((e) => e.kind === 'character') })) }).catch(() => {})
    return () => { alive = false }
  }, [seq, phase, refresh])

  // 正文 tab:整体交给 WriteLayout(自带顶栏:章导航/视角/护栏/保存/存为正文)。
  // DeduceProvider 已上提到 BinderLayout,包住左栏演绎树与中区 DeduceStage,共享选中态。
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
      {/* 中区只负责阶段编辑器;数据面板(帧/演绎/伏笔…)已上移到左栏 LeftDock,右栏主编由 RightDock 承载 */}
      <div className="flex-1 min-h-0 overflow-y-auto">
        {loading ? (
          <div className="flex items-center justify-center py-16 text-faint"><Loader2 size={18} className="animate-spin mr-2" />加载…</div>
        ) : phase === 'outline' ? (
          <OutlineTab seq={seq} value={meta?.synopsis} meta={meta} onSaved={() => setRefresh((r) => r + 1)} />
        ) : phase === 'beats' ? (
          <BeatsTab seq={seq} value={meta?.beats} meta={meta} onSaved={() => setRefresh((r) => r + 1)} />
        ) : phase === 'deduce' ? (
          <DeduceStage seq={seq} meta={meta} onSaved={() => setRefresh((r) => r + 1)} />
        ) : phase === 'draft' ? (
          <DraftTab seq={seq} meta={meta} onAdopt={() => setPhaseP('final')} />
        ) : null}
      </div>
    </div>
  )
}

// 顶部:章导航 + 五阶段 tab。
// 去正文双章导航(P2):final 阶段 WriteLayout.topbarMid 自带一套章导航,
// 故此处在 final 隐藏 PhaseBar 的章导航,只留阶段 tab,消除顶部两条 h-11 竖向冗余。
function PhaseBar({ seq, phase, onPhase, onSeqChange }) {
  return (
    <div className="shrink-0 border-b border-line bg-surface h-11 flex items-center gap-3 px-3">
      {phase !== 'final' && (
        <div className="flex items-center gap-1 shrink-0">
          <Btn variant="ghost" size="sm" icon onClick={() => onSeqChange?.(Math.max(1, (seq || 1) - 1))} title="上一章" aria-label="上一章"><ChevronLeft size={16} /></Btn>
          <span className="text-f13 text-ink tnum whitespace-nowrap px-1">第 {seq} 章</span>
          <Btn variant="ghost" size="sm" icon onClick={() => onSeqChange?.((seq || 1) + 1)} title="下一章" aria-label="下一章"><ChevronRight size={16} /></Btn>
        </div>
      )}
      <div className="flex items-center gap-0.5 rounded-lg bg-soft/60 p-0.5">
        {PHASES.map((p) => {
          const Icon = p.icon
          const on = phase === p.key
          return (
            <button key={p.key} onClick={() => onPhase(p.key)}
              className={`h-7 px-2.5 rounded-md text-f13 inline-flex items-center gap-1.5 transition-colors cursor-pointer ${on ? 'bg-surface text-brand shadow-sm ring-1 ring-line' : 'text-faint hover:text-ink'}`}>
              <Icon size={13} />{p.label}
            </button>
          )
        })}
      </div>
    </div>
  )
}
