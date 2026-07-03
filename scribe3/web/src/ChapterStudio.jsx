import { useEffect, useRef, useState } from 'react'
import {
  ChevronLeft, ChevronRight, ChevronUp, ChevronDown, ListChecks, AlignLeft, FileEdit, BookText,
  Plus, Trash2, Check, Save, Loader2, Sparkles,
} from 'lucide-react'
import { api } from './api'
import { WriteLayout } from './WriteLayout'
import { DeduceStage } from './DeduceStage'
import { useToast } from './ui/Toast.jsx'
import { useChiefSlot, useStageProposal, ProposalBar } from './ChiefSlotContext'
import { beatsFromMarkdown } from './lib/stageProposal'
import { Btn, Input } from './ui.jsx'
import { RichEditor, useUnsavedGuard } from './editor/RichEditor.jsx'

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

// ——— 大纲:RichEditor(markdown),失焦/切章/切阶段前 flush patchChapter({synopsis}) ———
function OutlineTab({ seq, value, meta, onSaved }) {
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
    try { await api.patchChapter(sq, { synopsis: val }); onSaved?.() }
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
    <div className={STAGE_WRAP}>
      <MetaBar meta={meta} wordCount={meta?.proseWords} />
      <div className="flex items-center justify-between mb-2 gap-2">
        <h3 className="text-f13 font-semibold text-ink">本章大纲 · 一句话到一段话写清这章要发生什么</h3>
        <div className="flex items-center gap-2 shrink-0">
          <Btn variant="ghost" size="sm" onClick={() => setChiefIntent({ phase: 'outline', seq, text: `帮我把第 ${seq} 章大纲展开成 3-5 句` })} title="把话术带到右栏主编,生成后可一键填入">
            <Sparkles size={13} />让主编生成
          </Btn>
          <span className="text-f11 text-faint">{saving ? '保存中…' : '失焦自动保存'}</span>
        </div>
      </div>
      {pending && (
        <ProposalBar
          text={`主编生成了内容(${pending.content.replace(/\s/g, '').length} 字),可落进大纲。`}
          actions={[{ label: '填入', variant: 'primary', onClick: fillPending }, { label: '追加', onClick: appendPending }]}
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
      <div className="text-f12 text-faint mt-2 leading-snug">大纲喂给主编当本章写作纲领;在右栏可与主编讨论怎么展开。</div>
    </div>
  )
}

// ——— 节拍:有序条目列表(增/删/打勾/上下移保留),每条 text 用精简 RichEditor,patchChapter({beats}) ———
// 本地稳定 id:仅供 React key / 编辑器实例复用,落库前剥掉。
let beatUid = 0
const withBeatIds = (arr) => (Array.isArray(arr) ? arr : []).map((b) => ({ ...b, _id: `b${++beatUid}` }))
const stripBeatIds = (arr) => arr.map(({ _id, ...b }) => b)

function BeatsTab({ seq, value, meta, onSaved }) {
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
    try { await api.patchChapter(sq, { beats: stripBeatIds(arr) }); onSaved?.() }
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
    <div className={STAGE_WRAP}>
      <MetaBar meta={meta} wordCount={meta?.proseWords} />
      <div className="flex items-center justify-between mb-3 gap-2">
        <h3 className="text-f13 font-semibold text-ink">节拍 · 把这章拆成有序的小节点</h3>
        <div className="flex items-center gap-2 shrink-0">
          <Btn variant="ghost" size="sm" onClick={() => setChiefIntent({ phase: 'beats', seq, text: `据大纲把第 ${seq} 章拆成有序节拍,一行一条` })} title="把话术带到右栏主编,生成后可一键追加">
            <Sparkles size={13} />让主编生成
          </Btn>
          <span className="text-f11 text-faint">{saving ? '保存中…' : `${beats.filter((b) => b.done).length}/${beats.length} 完成`}</span>
        </div>
      </div>
      {pending && (
        <ProposalBar
          text={`主编生成了 ${pendingItems.length} 条节拍,可追加到列表。`}
          actions={[{ label: '追加为新条目', variant: 'primary', onClick: appendPending }]}
        />
      )}

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
            <div key={b._id} className="group flex items-start gap-2 rounded-lg border border-line bg-canvas px-2.5 py-2">
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
function DraftTab({ seq, meta, onAdopt }) {
  const toast = useToast()
  const { setChiefIntent } = useChiefSlot()
  const [text, setText] = useState('')
  const [summary, setSummary] = useState('')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
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
          <Btn variant="ghost" size="sm" onClick={() => setChiefIntent({ phase: 'draft', seq, text: `据大纲和节拍给第 ${seq} 章写一版草稿` })} title="把话术带到右栏主编,生成后可一键填入">
            <Sparkles size={13} />让主编生成
          </Btn>
          <Btn variant="soft" size="sm" onClick={saveDraft} disabled={saving}>
            <Save size={13} />存草稿
          </Btn>
          <Btn variant="primary" size="sm" onClick={adopt} disabled={saving || !text.trim()}>
            <Check size={13} />采用为正文
          </Btn>
        </div>
      </div>
      {pending && (
        <ProposalBar
          text={`主编生成了本章草稿(${pending.content.replace(/\s/g, '').length} 字),可直接落进草稿框。`}
          actions={[{ label: '填入草稿框', variant: 'primary', onClick: fillDraft }, { label: '追加到草稿', onClick: appendDraft }]}
        />
      )}
      <Input
        value={summary}
        onChange={(e) => { setSummary(e.target.value); draftRef.current.dirty = true }}
        placeholder="给这版草稿一句备注(可留空)"
        className="h-8 mb-2"
      />
      <RichEditor
        value={text}
        editorKey={`${seq}|draft`}
        ariaLabel="草稿正文"
        onChange={(md) => { setText(md); draftRef.current.text = md; draftRef.current.dirty = true }}
        placeholder="在此自由起草,或在右栏让主编据大纲/节拍生成草稿。满意后『采用为正文』搬进正文 tab 做护栏/QC 打磨。"
        className="flex-1 min-h-0"
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
