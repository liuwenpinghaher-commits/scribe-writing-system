import { useCallback, useEffect, useRef, useState } from 'react'
import {
  ChevronLeft, ChevronRight, ChevronUp, ChevronDown, ListChecks, AlignLeft, FileEdit, BookText,
  Plus, Trash2, Check, Save, Loader2, Sparkles, ShieldCheck, Archive, MoreHorizontal,
  ScrollText, Eye, Compass,
} from 'lucide-react'
import { api } from './api'
import { WriteLayout } from './WriteLayout'
import { DeduceStage } from './DeduceStage'
import { ObjectFrame } from './layout/ObjectFrame'
import { useToast } from './ui/Toast.jsx'
import { useChiefSlot, useStageProposal, ProposalBar } from './ChiefSlotContext'
import { beatsFromMarkdown } from './lib/stageProposal'
import { Btn, Input } from './ui.jsx'
import { RichEditor, useUnsavedGuard } from './editor/RichEditor.jsx'
import { ConfirmDialog } from './ui/Dialog.jsx'
import { ChapterAuxPanel } from './ChapterAuxPanel'
import { ErrorBoundary } from './ErrorBoundary'

// 章五阶段(Task 7):大纲(synopsis)→ 节拍(beats)→ 演绎(deduce)→ 草稿(draft)→ 正文(prose/WriteLayout)。
// 大纲/节拍 patchChapter;演绎就地渲 DeduceStage(不再改道左栏能力);草稿 saveDraft/latestDraft;
// 正文整体复用 WriteLayout(护栏/QC/帧/伏笔/版本不丢)。
// 简报/关联/北极星是"读着写"的辅助资料而非写作阶段:入口在本工作台头部(章导航旁),
// 点击在【栏3 内容区】切换渲染 ChapterAuxPanel(2026-07-12 修正:撤全宽层——铺满栏2+3+4
// 会挤掉栏4 主编,用户没法边看辅助资料边和主编讨论;栏2 目录、栏4 主编全程不动)。
const PHASES = [
  { key: 'outline', label: '大纲', icon: AlignLeft },
  { key: 'beats', label: '节拍', icon: ListChecks },
  { key: 'deduce', label: '演绎', icon: Sparkles },
  { key: 'draft', label: '草稿', icon: FileEdit },
  { key: 'final', label: '正文', icon: BookText },
]
// 章节辅助三入口(2026-07-12 裁决):从栏4 RightDock capability 迁到章工作台头部——
// 点击在栏3 内容区替换阶段内容展现(与点大纲/正文页签同级的内容切换,四栏结构不动)。
// 图标沿用旧左栏 includeStageTabs 惯例:简报=ScrollText / 关联=Eye / 北极星=Compass。
const AUX_ENTRIES = [
  { key: 'brief', label: '简报', icon: ScrollText },
  { key: 'frame', label: '关联', icon: Eye },
  { key: 'northstar', label: '北极星', icon: Compass },
]
const PHASE_KEYS = new Set(PHASES.map((p) => p.key))
const META_PHASES = new Set(['outline', 'beats', 'deduce', 'draft'])
const normalizePhase = (phase) => PHASE_KEYS.has(phase) ? phase : 'final'

// 中区各阶段统一章工作台骨架:同一 max-w / padding / header / meta 节奏,阶段只换内容。
const STAGE_WRAP = 'w-full max-w-[56rem] mx-auto px-5 py-5 h-full flex flex-col min-h-0 gap-3 bg-canvas'
const STAGE_ACTIONS = 'flex items-center gap-2 shrink-0 flex-wrap justify-end'
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
    <div data-testid="chapter-stage-meta" className="flex items-center gap-1.5 flex-wrap pb-3 border-b border-line">
      <span className="inline-flex items-center h-6 rounded-full border border-brand/20 bg-brand/10 px-2.5 text-meta text-brand">视角 · {focName}</span>
      <span className="inline-flex items-center h-6 rounded-full border border-line bg-surface px-2.5 text-meta text-faint">涉及角色 {done}/{involved.length} 已演绎</span>
      {wc != null && <span className="inline-flex items-center h-6 rounded-full border border-line bg-surface px-2.5 text-meta text-faint tnum">字数 {wc}</span>}
    </div>
  )
}

function StageTitle({ title, subtitle, actions }) {
  return (
    <div className="flex items-start justify-between gap-4 min-w-0">
      <div className="min-w-0">
        <h3 data-testid="chapter-stage-heading" className="text-f20 leading-tight font-semibold text-ink">{title}</h3>
        <div className="mt-1 text-f13 text-faint leading-snug">{subtitle}</div>
      </div>
      {actions && <div className={STAGE_ACTIONS}>{actions}</div>}
    </div>
  )
}

export function ChapterMaterialRefs({ seq, onSelectMaterial }) {
  const [refs, setRefs] = useState(null)
  useEffect(() => {
    if (seq == null) { setRefs([]); return }
    let alive = true
    api.materialRefsByChapter(seq).then((r) => { if (alive) setRefs(Array.isArray(r) ? r : []) }).catch(() => { if (alive) setRefs([]) })
    return () => { alive = false }
  }, [seq])
  if (!refs || refs.length === 0) return null
  return (
    <div className="shrink-0 border-b border-line bg-surface px-4 py-2">
      <div className="mb-1 text-meta font-semibold text-faint">本章参考素材</div>
      <div className="flex flex-wrap gap-1.5">
        {refs.map((r, i) => {
          const title = r.title || r.material_id
          const phase = r.phase || r.dimension || r.via
          return (
            <button key={`${r.material_id}:${i}`} type="button"
              onClick={() => onSelectMaterial?.({ id: `material:${r.material_id}`, type: 'material', ref: r.material_id, label: title, meta: { kind: r.kind } })}
              className="rounded-md border border-line bg-canvas px-2 py-1 text-meta text-ink hover:border-brand/40">
              <span>{title}</span>
              {phase && <span className="ml-1 text-faint">phase:{phase}</span>}
            </button>
          )
        })}
      </div>
    </div>
  )
}

// ——— 大纲:RichEditor(markdown),失焦/切章/切阶段前 flush patchChapter({synopsis}) ———
// work 由 ChapterStudio 透传(实例 key=work,值稳定):卸载兜底 flush 钉死目标书,防切书写错书(F5)。
function OutlineTab({ seq, value, meta, onSaved, work }) {
  const toast = useToast()
  const [text, setText] = useState(value || '')
  const [saving, setSaving] = useState(false)
  // 正文同款范式:dirtyRef 持实时 {key, value, dirty},完全脱离 state 闭包
  const dirtyRef = useRef({ key: `${seq}|synopsis`, value: value || '', dirty: false })

  // 载入/静默刷新:同 key 且 dirty(正在编辑)→ 不被服务端回读冲掉
  useEffect(() => {
    const key = `${seq}|synopsis`
    if (dirtyRef.current.key === key && dirtyRef.current.dirty) return
    setText(value || '')
    dirtyRef.current = { key, value: value || '', dirty: false }
  }, [seq, value])

  // persistFor:只用捕获的 key/value 落库,不读可能已变的 state
  const persistFor = async (key, val) => {
    const sq = Number(key.split('|')[0])
    setSaving(true)
    // 传 work:切书时卸载 flush 走全局 WORK 会把本书大纲写进别的书(F5,同 DraftTab 钉书)
    try { await api.patchChapter(sq, { synopsis: val }, work); onSaved?.() }
    catch (e) {
      if (dirtyRef.current.key === key) dirtyRef.current.dirty = true   // 保留 dirty 可重试
      toast(e?.body?.detail || '大纲保存失败', { tone: 'danger' })
    } finally { setSaving(false) }
  }
  const flush = () => {
    const w = dirtyRef.current
    if (w.dirty) { w.dirty = false; persistFor(w.key, w.value) }
  }
  // 切章(seq 变)/切阶段(卸载)前 flush:cleanup 时 dirtyRef 仍持旧 key 与旧值
  useEffect(() => flush, [seq])  // eslint-disable-line
  useUnsavedGuard(() => dirtyRef.current.dirty)

  // 块二:接主编 stageProposal(phase/seq 匹配才显示);落进编辑器置 dirty,走上面的健壮保存。
  const { pending, clear } = useStageProposal('outline', seq)
  const { setChiefIntent } = useChiefSlot()
  const fillPending = () => {
    if (!pending) return
    setText(pending.content)
    dirtyRef.current = { key: `${seq}|synopsis`, value: pending.content, dirty: true }
    clear(); toast('已填入大纲')
  }
  const appendPending = () => {
    if (!pending) return
    const base = dirtyRef.current.key === `${seq}|synopsis` ? dirtyRef.current.value : text
    const next = (base ? base + '\n\n' : '') + pending.content
    setText(next)
    dirtyRef.current = { key: `${seq}|synopsis`, value: next, dirty: true }
    clear(); toast('已追加到大纲')
  }

  return (
    <div className={STAGE_WRAP} data-testid="chapter-workbench-shell" data-phase="outline">
      <StageTitle
        title="大纲"
        subtitle="本章要发生什么、读者应带走什么、哪些伏笔需要埋下。"
        actions={(
          <>
            <Btn variant="ghost" size="sm" onClick={() => setChiefIntent({ phase: 'outline', seq, text: `帮我把第 ${seq} 章大纲展开成 3-5 句` })} title="把话术带到右栏主编,生成后可一键填入">
              <Sparkles size={13} />让主编生成
            </Btn>
            <span className="text-meta text-faint">{saving ? '保存中…' : '失焦自动保存'}</span>
          </>
        )}
      />
      <MetaBar meta={meta} wordCount={meta?.proseWords} />
      {pending && (
        <ProposalBar
          text={`主编生成了内容(${pending.content.replace(/\s/g, '').length} 字),可落进大纲。`}
          actions={[{ label: '填入', variant: 'primary', onClick: fillPending }, { label: '追加', onClick: appendPending }]}
          onDismiss={clear}
        />
      )}
      <RichEditor
        value={text}
        editorKey={`${seq}|synopsis`}
        ariaLabel="本章大纲"
        onChange={(md) => { setText(md); dirtyRef.current = { key: `${seq}|synopsis`, value: md, dirty: true } }}
        onBlur={flush}
        placeholder="例:焦三被请进炉坊,第一次见到铜炉——他还不知道这炉子认主。本章建立悬念,埋『炉认主』伏笔。"
        className="flex-1 min-h-0"
      />
      <div className="text-f12 text-faint leading-snug">大纲喂给主编当本章写作纲领;在右栏可与主编讨论怎么展开。</div>
    </div>
  )
}

// ——— 节拍:有序条目列表(增/删/打勾/上下移保留),每条 text 用精简 RichEditor,patchChapter({beats}) ———
// 本地稳定 id:仅供 React key / 编辑器实例复用,落库前剥掉。
let beatUid = 0
const withBeatIds = (arr) => (Array.isArray(arr) ? arr : []).map((b) => ({ ...b, _id: `b${++beatUid}` }))
const stripBeatIds = (arr) => arr.map(({ _id, ...b }) => b)

// work 由 ChapterStudio 透传(实例 key=work,值稳定):卸载兜底 flush 钉死目标书,防切书写错书(F5)。
function BeatsTab({ seq, value, meta, onSaved, work }) {
  const toast = useToast()
  const [beats, setBeats] = useState(() => withBeatIds(value))
  const [draft, setDraft] = useState('')
  const [saving, setSaving] = useState(false)
  // dirtyRef:{key:`${seq}|beats`, value:最新条目数组(含_id), dirty}。条目文本编辑只置 dirty,失焦/切换前 flush。
  const dirtyRef = useRef({ key: `${seq}|beats`, value: withBeatIds(value), dirty: false })

  useEffect(() => {
    const key = `${seq}|beats`
    const w = dirtyRef.current
    if (w.key === key && w.dirty) return   // 正在编辑,不被静默刷新冲掉
    const incoming = Array.isArray(value) ? value : []
    // 内容未变(常见于 onSaved 回读)→ 不重置,避免编辑器整列重挂丢焦点
    if (w.key === key && JSON.stringify(incoming) === JSON.stringify(stripBeatIds(w.value))) return
    const next = withBeatIds(incoming)
    setBeats(next)
    dirtyRef.current = { key, value: next, dirty: false }
  }, [seq, value])

  // persistFor:只用捕获的 key/条目落库(剥 _id),不读可能已变的 state
  const persistFor = async (key, arr) => {
    const sq = Number(key.split('|')[0])
    setSaving(true)
    // 传 work:切书时卸载 flush 走全局 WORK 会把本书节拍写进别的书(F5,同 DraftTab 钉书)
    try { await api.patchChapter(sq, { beats: stripBeatIds(arr) }, work); onSaved?.() }
    catch (e) {
      if (dirtyRef.current.key === key) dirtyRef.current.dirty = true
      toast(e?.body?.detail || '节拍保存失败', { tone: 'danger' })
    } finally { setSaving(false) }
  }
  const flush = () => {
    const w = dirtyRef.current
    if (w.dirty) { w.dirty = false; persistFor(w.key, w.value) }
  }
  useEffect(() => flush, [seq])  // eslint-disable-line
  useUnsavedGuard(() => dirtyRef.current.dirty)

  // 结构操作(增/删/勾/移):立即落库(含未失焦的文本改动,state 里已是最新)
  const commit = (next) => {
    setBeats(next)
    dirtyRef.current = { key: `${seq}|beats`, value: next, dirty: false }
    persistFor(`${seq}|beats`, next)
  }
  // 条目文本编辑:只更新 state + 置 dirty,失焦/切换时 flush
  const editText = (id, md) => {
    setBeats((prev) => {
      const next = prev.map((b) => b._id === id ? { ...b, text: md } : b)
      dirtyRef.current = { key: `${seq}|beats`, value: next, dirty: true }
      return next
    })
  }
  const add = () => {
    const t = draft.trim()
    if (!t) return
    setDraft('')
    commit([...beats, { _id: `b${++beatUid}`, text: t, done: false }])
  }
  const toggle = (i) => commit(beats.map((b, idx) => idx === i ? { ...b, done: !b.done } : b))
  const remove = (i) => commit(beats.filter((_, idx) => idx !== i))
  const move = (i, dir) => {
    const j = i + dir
    if (j < 0 || j >= beats.length) return
    const next = [...beats]
    ;[next[i], next[j]] = [next[j], next[i]]
    commit(next)
  }

  // 块二:接主编 stageProposal(phase/seq 匹配才显示);解析成条目「追加为新条目」,
  // 走 commit(结构操作既有健壮路径,立即落库)。基于 dirtyRef 最新条目追加,不吞未 flush 的文本编辑。
  const { pending, clear } = useStageProposal('beats', seq)
  const { setChiefIntent } = useChiefSlot()
  const pendingItems = pending ? beatsFromMarkdown(pending.content) : []
  const appendPending = () => {
    if (!pending) return
    if (!pendingItems.length) { clear(); return }
    const base = dirtyRef.current.key === `${seq}|beats` ? dirtyRef.current.value : beats
    commit([...base, ...pendingItems.map((t) => ({ _id: `b${++beatUid}`, text: t, done: false }))])
    clear(); toast(`已追加 ${pendingItems.length} 条节拍`)
  }

  return (
    <div className={STAGE_WRAP} data-testid="chapter-workbench-shell" data-phase="beats">
      <StageTitle
        title="节拍"
        subtitle="把大纲拆成有序小节点,保持因果顺序和信息释放节奏。"
        actions={(
          <>
            <Btn variant="ghost" size="sm" onClick={() => setChiefIntent({ phase: 'beats', seq, text: `据大纲把第 ${seq} 章拆成有序节拍,一行一条` })} title="把话术带到右栏主编,生成后可一键追加">
              <Sparkles size={13} />让主编生成
            </Btn>
            <span className="text-meta text-faint">{saving ? '保存中…' : `${beats.filter((b) => b.done).length}/${beats.length} 完成`}</span>
          </>
        )}
      />
      <MetaBar meta={meta} wordCount={meta?.proseWords} />
      {pending && (
        <ProposalBar
          text={`主编生成了 ${pendingItems.length} 条节拍,可追加到列表。`}
          actions={[{ label: '追加为新条目', variant: 'primary', onClick: appendPending }]}
          onDismiss={clear}
        />
      )}

      <div className="flex gap-2">
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
        <div className="text-f13 text-faint text-center py-10 rounded-lg border border-dashed border-line bg-surface">还没有节拍。把这章想发生的事一条条列出来。</div>
      ) : (
        <div className="space-y-1.5">
          {beats.map((b, i) => (
            <div key={b._id} className="group flex items-start gap-2 rounded-lg border border-line bg-surface px-2.5 py-2">
              <button onClick={() => toggle(i)}
                className={`w-5 h-5 mt-0.5 rounded-md border shrink-0 inline-flex items-center justify-center cursor-pointer transition-colors ${b.done ? 'bg-brand border-brand text-brandfg' : 'border-line hover:border-brand'}`}>
                {b.done && <Check size={13} />}
              </button>
              <div className={`flex-1 min-w-0 ${b.done ? 'opacity-55 line-through' : ''}`}>
                <RichEditor minimal value={b.text} editorKey={`${seq}|beat:${b._id}`} ariaLabel={`节拍 ${i + 1}`}
                  onChange={(md) => editText(b._id, md)} onBlur={flush} placeholder="节拍内容…" />
              </div>
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
function DraftTab({ seq, work, meta, onAdopt }) {
  const toast = useToast()
  const { setChiefIntent } = useChiefSlot()
  const [text, setText] = useState('')
  const [summary, setSummary] = useState('')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [checking, setChecking] = useState(false)   // 断头修复#22:草稿质检
  const [checkRes, setCheckRes] = useState(null)
  // 待落草稿(块二并入通用 stageProposal 通道):phase/seq 匹配且内容非空才提示(防切章/切阶段串台)。
  const { pending, clear } = useStageProposal('draft', seq)
  // 落进后置 dirty,靠既有 flush(切章/存草稿)落库;同时清除待落。
  const fillDraft = () => {
    if (!pending) return
    setText(pending.content); draftRef.current.dirty = true
    clear(); toast('已填入草稿框')
  }
  const appendDraft = () => {
    if (!pending) return
    setText((prev) => (prev ? prev + '\n\n' : '') + pending.content); draftRef.current.dirty = true
    clear(); toast('已追加到草稿')
  }
  // 换章防丢:draftRef 只持「实时 text/summary/dirty」(渲染时刷新);seq 不放 ref
  // ——因 draftRef.current.seq=seq 会在换章渲染时先变成新 seq,导致 cleanup 拿错章号。
  // 旧章 seq 改由 effect 闭包捕获(myseq),cleanup 时用它,保证 flush 落到正确的旧章。
  const draftRef = useRef({ text: '', summary: '', dirty: false })
  draftRef.current.text = text
  draftRef.current.summary = summary
  useUnsavedGuard(() => draftRef.current.dirty)

  useEffect(() => {
    let alive = true
    const myseq = seq  // 闭包捕获本 effect 的章号,cleanup 用它 = 真旧章号
    const mywork = work  // 同源钉书:切书卸载 flush 走全局 WORK 会写错书(见 WriteLayout Critical 注释)
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
        api.saveDraft(myseq, oldText, oldSummary, mywork)
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
    <div className={STAGE_WRAP} data-testid="chapter-workbench-shell" data-phase="draft">
      <StageTitle
        title="草稿"
        subtitle="放手起草,满意后采用为正文再进入正式校验。"
        actions={(
          <>
            <span className="text-meta text-faint tnum">{wc} 字</span>
            <Btn variant="ghost" size="sm" onClick={() => setChiefIntent({ phase: 'draft', seq, text: `据大纲和节拍给第 ${seq} 章写一版草稿` })} title="把话术带到右栏主编,生成后可一键填入">
              <Sparkles size={13} />让主编生成
            </Btn>
            <Btn variant="ghost" size="sm" disabled={checking || !text.trim()}
              onClick={() => {
                setChecking(true)
                api.draftCheck(seq, text, meta?.focalizer || '')
                  .then(setCheckRes)
                  .catch((e) => setCheckRes({ error: e?.body?.detail || e?.message || '质检失败' }))
                  .finally(() => setChecking(false))
              }} title="确定性轻质检:五类 QC/整行复读/排比/情感直说/泄露预览,不落库不打断">
              {checking ? <Loader2 size={13} className="animate-spin" /> : <ShieldCheck size={13} />}质检
            </Btn>
            <Btn variant="soft" size="sm" onClick={saveDraft} disabled={saving}>
              <Save size={13} />存草稿
            </Btn>
            <Btn variant="primary" size="sm" onClick={adopt} disabled={saving || !text.trim()}>
              <Check size={13} />采用为正文
            </Btn>
          </>
        )}
      />
      <MetaBar meta={meta} wordCount={wc} />
      {pending && (
        <ProposalBar
          text={`主编生成了本章草稿(${pending.content.replace(/\s/g, '').length} 字),可直接落进草稿框。`}
          actions={[{ label: '填入草稿框', variant: 'primary', onClick: fillDraft }, { label: '追加到草稿', onClick: appendDraft }]}
          onDismiss={clear}
        />
      )}
      {checkRes && (
        <div className="rounded-lg border border-line bg-surface px-2.5 py-2 text-f12">
          <div className="flex items-center gap-2">
            <span className="font-medium text-ink">草稿质检</span>
            <button onClick={() => setCheckRes(null)} className="ml-auto text-meta text-faint hover:text-ink cursor-pointer">关闭</button>
          </div>
          {checkRes.error ? <div className="text-danger mt-1">{checkRes.error}</div> : (() => {
            const cnt = (x) => Array.isArray(x) ? x.length : (typeof x === 'number' ? x : 0)
            const q = checkRes.quality || {}
            const bits = [
              ['复读', cnt(q.repetition)], ['排比', cnt(q.structural)], ['升华', cnt(q.purple)],
              ['AI腔', cnt(q.ai_tics)], ['过饱和', cnt(q.oversaturation)],
              ['整行重复', cnt(checkRes.duplicate_lines)], ['情感直说', cnt(checkRes.emotion_telling)],
              ['泄露预览', cnt(checkRes.leaks)],
            ].filter(([, n]) => n > 0)
            return bits.length === 0
              ? <div className="text-ok mt-1">干净——确定性检测零命中</div>
              : <div className="flex flex-wrap gap-x-3 gap-y-0.5 mt-1 text-warn">{bits.map(([l, n]) => <span key={l}>{l} {n}</span>)}</div>
          })()}
        </div>
      )}
      <Input
        value={summary}
        onChange={(e) => { setSummary(e.target.value); draftRef.current.dirty = true }}
        placeholder="给这版草稿一句备注(可留空)"
        className="h-8"
      />
      <RichEditor
        value={text}
        editorKey={`${seq}|draft`}
        ariaLabel="草稿正文"
        onChange={(md) => { setText(md); draftRef.current.text = md; draftRef.current.dirty = true }}
        placeholder="在此自由起草,或在右栏让主编据大纲/节拍生成草稿。满意后『采用为正文』搬进正文 tab 做护栏/QC 打磨。"
        className="flex-1 min-h-0"
      />
      <div className="text-f12 text-faint leading-snug">草稿区不跑护栏/QC,放手写;正文区才上全套校验。</div>
    </div>
  )
}

/**
 * 章工作台(Task 7):ObjectFrame 承载章标题 / 单套章导航 / 五阶段页签。
 * 大纲/节拍/草稿 = ChapterStudio 自带轻量编辑器(patchChapter/saveDraft);演绎就地渲 DeduceStage;
 * 正文 = 整体复用 WriteLayout(护栏/QC/帧/伏笔/版本/检索/主编对话全保留)。
 */
export function ChapterStudio({ work, seq, sceneIdx, initialPhase, onSeqChange, onSelectNode, onArchived }) {
  const toast = useToast()
  // 初值优先吃 selection 的 phase 提示(全书大纲点章行→直落大纲阶段,不闪上次阶段)
  const [phase, setPhase] = useState(() => normalizePhase(initialPhase || localStorage.getItem('s3.chapter.phase') || 'final'))
  const [meta, setMeta] = useState(null)   // {title, synopsis, beats}
  const [loading, setLoading] = useState(true)
  const [refresh, setRefresh] = useState(0)
  const [archiveOpen, setArchiveOpen] = useState(false)
  const [moreOpen, setMoreOpen] = useState(false)   // 「更多」菜单(归档入口)
  // 章节辅助视图(栏3 内容区切换):null=显示阶段内容,'brief'|'frame'|'northstar'=
  // 内容区替换为 ChapterAuxPanel 并高亮对应头部入口。受控直连 ChapterAuxPanel 的 tab
  // (面板内三 tab 互切回写此值,头部高亮永远等于正在看的 tab)。
  // 返回语义(双通道,均不丢 phase):
  //   · 点任一阶段页签 → auxView 置 null,回到该阶段内容(phase state 全程保留);
  //   · 再点当前高亮的辅助入口 → toggle 关闭,回到离开时的阶段。
  const [auxView, setAuxView] = useState(null)

  // 草稿软门:切到草稿时若有涉及角色未演绎→黄色 toast 提示(不阻断,仍切进)。
  // Task 7:演绎已是章内真阶段,删除派发 s3-open-capability 的 deduce 特例,直接就地切换。
  const setPhaseP = useCallback((p) => {
    const nextPhase = normalizePhase(p)
    if (p === 'draft' && meta) {
      const deds = meta.deductions || []
      const done = new Set(deds.filter((d) => (d.prose || '').trim()).map((d) => d.character_id))
      const pending = (meta.involved_characters || []).filter((id) => !done.has(id))
      if (pending.length) {
        // 断头修复#8:软门带可点"去补"入口——就地切到演绎阶段(自引用在点击时才求值,安全)
        toast(`还有 ${pending.length} 个涉及角色未演绎(不影响继续)`, {
          tone: 'warn',
          action: { label: '去补', onClick: () => setPhaseP('deduce') },
        })
      }
    }
    setPhase(nextPhase); localStorage.setItem('s3.chapter.phase', nextPhase)
  }, [meta, toast])

  // 章导航上界(Task 7 自 WriteLayout 上移):下一章到真实末章为止,不再翻出空章 404。
  // I1:初值 null=上界未知——未加载不禁用、不谎报「已是最后一章」(否则每次切章首帧闪禁);
  // 拉取失败保持 null(fail-open,宁可放行也不永久禁死)并 console.warn 留痕。
  const [maxSeq, setMaxSeq] = useState(null)
  useEffect(() => {
    let alive = true
    api.chapters().then((chapters) => {
      if (!alive) return
      const values = Array.isArray(chapters) ? chapters.map((chapter) => Number(chapter.seq)).filter(Number.isFinite) : []
      setMaxSeq(values.length ? Math.max(...values) : seq)
    }).catch((e) => {
      if (!alive) return
      setMaxSeq(null)
      console.warn('[scribe3] 章列表拉取失败,章导航上界未知(下一章不禁用):', e)
    })
    return () => { alive = false }
  }, [work, seq])

  // 单一真相源(块四a-2):从全书大纲点章行进来(selection 带 phase 提示)→ 落该章对应阶段
  // (通常 'outline',与书级大纲读写同一 synopsis 字段)。项目树/章导航不带提示 → 保持上次阶段。
  useEffect(() => {
    if (initialPhase) setPhaseP(normalizePhase(initialPhase))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initialPhase, seq])

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
    if (phase === 'final' || !META_PHASES.has(phase)) { setLoading(false); return }
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

  const archiveChapter = async () => {
    try {
      await api.archiveChapter(seq, '')
      toast('章节已归档', { tone: 'ok' })
      onArchived?.(seq)
    } catch (e) {
      toast(e?.body?.detail || e?.message || '归档章节失败', { tone: 'danger' })
    }
  }

  const archiveDialog = (
    <ConfirmDialog
      open={archiveOpen}
      title={`归档第 ${seq} 章?`}
      body="归档后会从手稿目录隐藏,正文和关联不会删除。"
      danger
      confirmText="归档"
      onConfirm={archiveChapter}
      onClose={() => setArchiveOpen(false)}
    />
  )

  // 「更多」菜单外点关闭(与 WriteLayout 保存菜单同款轻交互,防菜单悬挂)。
  const moreRef = useRef(null)
  useEffect(() => {
    if (!moreOpen) return undefined
    const onDoc = (e) => { if (moreRef.current && !moreRef.current.contains(e.target)) setMoreOpen(false) }
    document.addEventListener('mousedown', onDoc)
    return () => document.removeEventListener('mousedown', onDoc)
  }, [moreOpen])

  // ObjectFrame actions:全 DOM 唯一一套章导航(Task 7)+ 低频操作(归档)收进「更多」。
  // 章节辅助三入口放章导航左侧(actions 是 ObjectFrame 头部唯一动作插槽,tabs 行无右插槽,
  // 不为此改通用外框):轻量 segmented 小钮,选中章(seq 非空)才出现。
  // 激活态 = auxView 命中(aria-pressed + 与 Tabs 选中态同款高亮):辅助视图开着时
  // 当前位置必须可见;再点当前高亮入口 = toggle 关闭回阶段内容。
  // 章导航中间只显位置计数「N / 总数」(tooltip 给全文):标题 <h1> 已是「第 N 章」
  // (title 空时 fallback),此处再写一遍「第 N 章」即重复信息,压缩后一行放得下。
  const frameActions = (
    <div className="flex items-center gap-1 shrink-0">
      {seq != null && (
        <>
          <div role="group" aria-label="章节辅助" className="flex items-center gap-0.5 rounded-lg bg-soft p-0.5">
            {AUX_ENTRIES.map((entry) => {
              const Icon = entry.icon
              const active = auxView === entry.key
              return (
                <button key={entry.key} type="button" aria-pressed={active}
                  onClick={() => setAuxView(active ? null : entry.key)}
                  title={active ? `${entry.label} · 再点一次回到写作阶段` : `${entry.label} · 在本栏展开章节辅助`}
                  className={`inline-flex items-center gap-1 h-7 rounded-md px-2 text-f12 cursor-pointer transition-colors ${
                    active ? 'bg-surface text-brand ring-1 ring-line' : 'text-faint hover:bg-surface hover:text-ink'
                  }`}>
                  <Icon size={13} />{entry.label}
                </button>
              )
            })}
          </div>
          <span className="w-px h-4 bg-line mx-0.5" aria-hidden="true" />
        </>
      )}
      <Btn variant="ghost" size="sm" icon onClick={() => onSeqChange?.(Math.max(1, (seq || 1) - 1))} title="上一章" aria-label="上一章"><ChevronLeft size={16} /></Btn>
      <span className="text-f13 text-ink tnum whitespace-nowrap px-1"
        title={maxSeq != null ? `第 ${seq} 章 / 共 ${maxSeq} 章` : `第 ${seq} 章`}>
        {seq}{maxSeq != null ? ` / ${maxSeq}` : ''}
      </span>
      <Btn variant="ghost" size="sm" icon disabled={maxSeq != null && seq >= maxSeq}
        title={maxSeq != null && seq >= maxSeq ? '已是最后一章' : '下一章'} aria-label="下一章"
        onClick={() => onSeqChange?.((seq || 1) + 1)}><ChevronRight size={16} /></Btn>
      <div ref={moreRef} className="relative">
        <Btn variant="ghost" size="sm" icon onClick={() => setMoreOpen((v) => !v)}
          title="更多操作" aria-label="更多" aria-expanded={moreOpen}><MoreHorizontal size={16} /></Btn>
        {moreOpen && (
          <div className="absolute right-0 top-full mt-1 z-20 min-w-[148px] rounded-lg border border-line bg-surface shadow-lg py-1">
            <button onClick={() => { setMoreOpen(false); setArchiveOpen(true) }}
              title="归档后从目录隐藏,正文和关联保留"
              className="w-full flex items-center gap-2 px-3 h-8 text-f13 text-ink hover:bg-soft cursor-pointer whitespace-nowrap">
              <Archive size={13} className="text-faint shrink-0" />归档章节
            </button>
          </div>
        )}
      </div>
    </div>
  )

  // 单一 ObjectFrame 承载(Task 7):面包屑/章标题/章导航/五阶段页签只此一套,阶段只换 children。
  // 正文阶段整体交给 WriteLayout(视角/护栏/保存/存为正文保留;其内部章导航已删,真身在本外框)。
  // DeduceProvider 已上提到 BinderLayout,包住左栏演绎树与中区 DeduceStage,共享选中态。
  // compact:面包屑+标题合一行「手稿 › 第N章」,头部三行压两行(2026-07-12 空间修正)。
  // 辅助视图与阶段页签激活态互斥:auxView 开着时 activeTab 传 null——阶段页签整体去激活
  // (不显"假激活",当前位置由高亮的辅助入口表达);点任一阶段页签即关辅助视图回该阶段。
  const showAux = auxView != null && seq != null
  return (
    <ObjectFrame
      compact
      breadcrumb="手稿"
      title={meta?.title || `第 ${seq} 章`}
      tabs={PHASES.map((p) => ({ value: p.key, label: p.label }))}
      activeTab={showAux ? null : phase}
      onTab={(p) => { setAuxView(null); setPhaseP(p) }}
      actions={frameActions}
    >
      {showAux ? (
        <div className="h-full min-h-0" data-testid="chapter-aux-view">
          {/* key 只含章号:切章重挂重拉(角色候选等);受控 tab 切换不重挂,不白重拉数据。
              崩溃只塌辅助视图,头部入口仍在,可切回阶段。 */}
          <ErrorBoundary key={`aux:${seq}`}>
            <ChapterAuxPanel seq={seq} tab={auxView} onTabChange={setAuxView} />
          </ErrorBoundary>
        </div>
      ) : phase === 'final' ? (
        <div className="h-full flex flex-col min-h-0">
          <ChapterMaterialRefs seq={seq} onSelectMaterial={onSelectNode} />
          <div className="flex-1 min-h-0">
            {/* I4:不再传 onSeqChange——WriteLayout 内部步进器已删,换章单向走外部 seq prop */}
            <WriteLayout key={work} work={work} seq={seq} sceneIdx={sceneIdx} />
          </div>
        </div>
      ) : (
        <div className="h-full min-h-0 overflow-y-auto bg-canvas">
          {loading ? (
            <div className="flex items-center justify-center py-16 text-faint"><Loader2 size={18} className="animate-spin mr-2" />加载…</div>
          ) : phase === 'outline' ? (
            <OutlineTab seq={seq} work={work} value={meta?.synopsis} meta={meta} onSaved={() => setRefresh((r) => r + 1)} />
          ) : phase === 'beats' ? (
            <BeatsTab seq={seq} work={work} value={meta?.beats} meta={meta} onSaved={() => setRefresh((r) => r + 1)} />
          ) : phase === 'deduce' ? (
            // 演绎就地渲染(Task 7):与左栏演绎能力 deduce_view 两入口互斥不冲突,共用 DeduceProvider 选中态。
            <DeduceStage seq={seq} meta={meta} work={work} onSaved={() => setRefresh((r) => r + 1)} />
          ) : phase === 'draft' ? (
            <DraftTab seq={seq} work={work} meta={meta} onAdopt={(text) => {
              // 采用为正文=把草稿真搬进 chapter.prose(彻查 B-4:旧实现丢弃 text 只切 tab → 正文空/旧)。
              // 保留本章 title/focalizer;落库成功后再切正文 tab,让 WriteLayout 拉到刚搬入的正文。
              api.saveChapter(seq, text, meta?.title || '', meta?.focalizer || '')
                .then(() => setPhaseP('final'))
                .catch((e) => toast('采用为正文失败:' + (e?.body?.detail || e?.message || ''), { tone: 'danger' }))
            }} />
          ) : null}
        </div>
      )}
      {archiveDialog}
    </ObjectFrame>
  )
}
