import { useCallback, useContext, useEffect, useRef, useState } from 'react'
import {
  ChevronLeft, ChevronRight, ChevronUp, ChevronDown, ListChecks, AlignLeft, FileEdit, BookText,
  Plus, Trash2, Check, Save, Loader2, Sparkles, ShieldCheck, Archive, MoreHorizontal,
  ScrollText, Eye, Compass, MessagesSquare, Settings2, Gauge,
} from 'lucide-react'
import { api } from './api'
import { WriteLayout, RestoreContext } from './WriteLayout'
import { DeduceStage } from './DeduceStage'
import { ObjectFrame } from './layout/ObjectFrame'
import { useToast } from './ui/Toast.jsx'
import { useChiefSlot, useStageProposal, ProposalBar } from './ChiefSlotContext'
import { beatsFromMarkdown } from './lib/stageProposal'
import { Btn, Input } from './ui.jsx'
import { seedChiefNarrativeWrite } from './lib/chiefSeed.js'
import { RichEditor, useUnsavedGuard } from './editor/RichEditor.jsx'
import { ConfirmDialog } from './ui/Dialog.jsx'
import { ChapterAuxPanel } from './ChapterAuxPanel'
import { ChapterMetaPane } from './ChapterMetaPane'
import { ScenePaper } from './ScenePaper.jsx'
import { ErrorBoundary } from './ErrorBoundary'
import { SelectionQuoteActions } from './ui/SelectionQuoteActions.jsx'
import { openChiefForEmptyField } from './lib/selAction.js'
import { softGateIssues, softGateSummary } from './lib/deduceGate.js'
import {
  evaluateChapterContract,
  contractNeedsAttention,
  contractSoftSummary,
  isContractBannerDismissed,
  dismissContractBanner,
  mergedSoftBannerSummary,
  shouldShowMergedSoftBanner,
  executionSoftSummary,
} from './lib/chapterContractGate.js'
import { loadIaDensity, saveIaDensity, auxVisibleForDensity } from './lib/iaDensity.js'
import { remainingLaterFromOutline, chapterAccountLine } from './lib/volumeLedger.js'


// 章五阶段(Task 7):大纲→节拍→演绎→草稿→正文。字段分列禁止合并(IA KD-IA-1)。
// 辅助面:简报/关联/评分卡/经验复盘——读着写,不参与阶段时钟。

const PHASES_LEGACY = [
  { key: 'outline', label: '大纲', icon: AlignLeft, duty: '写清本章讲什么：谁、想干什么、会付出什么代价' },
  { key: 'beats', label: '节拍', icon: ListChecks, duty: '把本章拆成几场戏：冲突怎么升级、怎么收' },
  { key: 'deduce', label: '演绎', icon: Sparkles, duty: '写这场戏的字缝：每人要什么、瞒了什么、读者能拼角色拼不出的' },
  { key: 'draft', label: '草稿', icon: FileEdit, duty: '先放开写一版，不急着过严检' },
  { key: 'final', label: '正文', icon: BookText, duty: '定稿用的正文：保存、检查、打磨都在这里' },
]
const PHASES_DESIGN = [
  { key: 'design', label: '章设计', icon: AlignLeft, duty: '先立责任，再写一篇戏；契约从戏里抄出' },
  { key: 'deduce', label: '演绎', icon: Sparkles, duty: '写这场戏的字缝：每人要什么、瞒了什么、读者能拼角色拼不出的' },
  { key: 'draft', label: '草稿', icon: FileEdit, duty: '先放开写一版，不急着过严检' },
  { key: 'final', label: '正文', icon: BookText, duty: '定稿用的正文：保存、检查、打磨都在这里' },
]
const PHASES = PHASES_LEGACY
// 辅助入口：读着写；与顶栏「作品意图」不是同一物。渐进披露见信息密度。
const AUX_ENTRIES = [
  { key: 'brief', label: '简报', icon: ScrollText, tip: '本章写作备忘（只读）：伏笔、提醒等' },
  { key: 'frame', label: '关联', icon: Eye, tip: '本章能用的设定、素材、伏笔，以及视角不能写破的边界' },
  { key: 'northstar', label: '评分卡', icon: Compass, tip: '机器给的参考分，不是你的写作目标' },
  { key: 'pressure', label: '经验复盘', icon: Gauge, tip: '写后复盘提示，不是大纲里的冲突安排' },
]
const PHASE_KEYS = new Set([...PHASES_LEGACY, ...PHASES_DESIGN].map((p) => p.key))
/** 阶段编辑器仍可 loading 占位的 phase；final 也拉契约 meta，但不挡 WriteLayout */
const META_EDITOR_PHASES = new Set(['outline', 'beats', 'design', 'deduce', 'draft'])
const normalizePhase = (phase, designOn = false) => {
  if (designOn && (phase === 'outline' || phase === 'beats' || phase === 'plan')) return 'design'
  return PHASE_KEYS.has(phase) ? phase : 'final'
}

/** 正文顶栏：开写前材料 + 写完对照 合一 banner（不拦聊天；存正式正文仍可能硬拦缺项） */
function ContractSoftBanner({ work, seq, meta, executionSoft, onGoFix, onDismiss }) {
  if (!meta && !executionSoft) return null
  if (!shouldShowMergedSoftBanner(meta, executionSoft)) return null
  if (isContractBannerDismissed(work, seq)) return null
  const summary = mergedSoftBannerSummary(meta, executionSoft)
    || contractSoftSummary(meta)
    || executionSoftSummary(executionSoft)
  const hasContractGap = meta ? contractNeedsAttention(meta) : false
  const title = hasContractGap ? '开写前材料 / 写完对照' : '写完对照'
  return (
    <div
      role="status"
      data-testid="contract-soft-banner"
      className="shrink-0 border-b border-warn/40 bg-warn/10 px-3 py-2 text-f12 text-ink flex items-start gap-2 flex-wrap"
    >
      <span className="font-medium text-warn shrink-0">{title}</span>
      <span className="flex-1 min-w-[12rem] text-faint leading-relaxed">
        {summary || '大纲、节拍、场景真相或写完对照还有缺口'}。
        {hasContractGap ? (
          <>
            <strong className="text-ink font-medium">这场还没定必须发生（不拦先写日子）</strong>
            （本提示不拦聊天；保存正式正文时缺项仍可能被拦住）。
          </>
        ) : (
          <>（仅建议，不拦生成；若正文与大纲/驱动脱节，可到「章节信息」用【强制重写】核对，不会自动清空正文）。</>
        )}
      </span>
      {typeof onGoFix === 'function' && (
        <button
          type="button"
          data-testid="contract-soft-banner-fix"
          onClick={onGoFix}
          className="h-7 px-2 rounded-lg border border-warn/50 bg-canvas text-f12 text-warn hover:bg-warn/10 cursor-pointer"
        >
          去补
        </button>
      )}
      <button
        type="button"
        data-testid="contract-soft-banner-dismiss"
        onClick={onDismiss}
        className="h-7 px-2 rounded-lg text-f12 text-faint hover:bg-canvas cursor-pointer"
      >
        本次关闭
      </button>
    </div>
  )
}
// 正文阶段会令 FourPaneShell 切到阅读布局，DetailPane 因布局重排可能重挂载。
// 章节阶段因此必须按作品+章持久化；不能让目录节点携带的默认 outline 覆盖作者刚点开的正文。
const phaseStorageKey = (work, seq) => `s3.chapter.phase:${work}:${seq}`
const readStoredPhase = (work, seq) =>
  localStorage.getItem(phaseStorageKey(work, seq)) || localStorage.getItem('s3.chapter.phase')

function adoptFailureMessage(error) {
  const detail = error?.body?.detail
  if (typeof detail === 'string' && detail.trim()) return detail
  if (detail && typeof detail === 'object') {
    const primary = [detail.message, detail.reason, detail.code]
      .find((value) => typeof value === 'string' && value.trim())
    const blockers = [detail.blocking, detail.root_causes]
      .flat()
      .map((value) => typeof value === 'string' ? value : value?.message)
      .filter((value) => typeof value === 'string' && value.trim())
    return [primary, ...blockers].filter(Boolean).join('；') || '正文未保存，请检查工艺前置条件后重试'
  }
  return error?.message || '正文未保存，请检查工艺前置条件后重试'
}

// 中区各阶段统一章工作台骨架:同一 max-w / padding / header / meta 节奏,阶段只换内容。
// Upstream 内容岛:浅灰画布上白卡抬升;外层 scroll 仍由章工作台 canvas 承担
// 第三栏内容流:无套娃 elevated 卡,画布上直接排信息,多给字少给框。
const STAGE_WRAP = 'w-full max-w-[64rem] mx-auto px-4 py-2 flex flex-col h-full min-h-0 gap-2'
const STAGE_ACTIONS = 'flex w-full items-center gap-1.5 flex-wrap justify-end'
/** 大纲/节拍/草稿只读与编辑共用 stage 字号，避免阶段间忽大忽小 */
const STAGE_BODY = 'type-stage'
// hover 才显的行内操作(移动/删除):键盘 Tab 聚焦 + 触屏无 hover 时也可达。
const HOVER_ACTIONS = 'opacity-0 group-hover:opacity-100 focus-within:opacity-100 [@media(hover:none)]:opacity-100 transition-opacity'

// ——— 选区聊/改话术模板(大纲/草稿共用;spec 2026-07-12-selection-actions-design.md §2 决策1)———
const selDiscussPrompt = (label, text) => `就本章${label}这段和你聊聊(先不改):「${text}」\n`
const selEditPrompt = (text) => `把这段改一下,直接给出改后的完整段落:「${text}」`
// 选区锚点匹配(spec 决策2):①原文唯一命中;②\n→\n\n 兜底——RichEditor 选区跨段落时块间是
// 单 \n(textBetween(from,to,'\n')),而 md buffer(docToMd)块间是 \n\n,直接 indexOf 不命中。
// 两级都不唯一/不命中 → null,调用方降级为该阶段既有落地方式(追加/整体填入)。
// 唯一性用 indexOf === lastIndexOf:天然覆盖自重叠子串(如「轰轰」在「轰轰轰」里重叠两处)——
// 非重叠扫描(游标跳 needle.length)会漏数重叠命中、误判唯一,String.replace 静默错替第一处。
function matchSelAnchor(buffer, anchor) {
  if (!anchor) return null
  const buf = buffer || ''
  const unique = (needle) => {
    const first = buf.indexOf(needle)
    return first !== -1 && first === buf.lastIndexOf(needle)
  }
  if (unique(anchor)) return anchor
  const alt = anchor.replace(/\n/g, '\n\n')
  if (alt !== anchor && unique(alt)) return alt
  return null
}

// ——— 阶段 meta 摘要条(P1):后端已有 focalizer/涉及角色/演绎/字数,在每个阶段顶部只读呈现 ———
function MetaBar({ meta, wordCount }) {
  if (!meta) return null
  const chars = meta.chars || []
  const focName = meta.focalizer ? ((chars.find((c) => c.id === meta.focalizer) || {}).name || meta.focalizer) : '未设'
  const issues = softGateIssues(meta)
  const involved = meta.involved_characters || []
  const done = Math.max(0, (involved.length || 0) - issues.missing.length)
  const wc = wordCount != null ? wordCount : (meta.synopsis ? null : null)
  return (
    <div data-testid="chapter-stage-meta" className="flex items-center gap-2 flex-wrap pb-1 text-meta text-faint shrink-0">
      <span className="text-brand">视角 · {focName}</span>
      <span>· 涉及角色 {done}/{involved.length} 已演绎</span>
      {issues.stale.length > 0 && <span className="text-warn" data-testid="meta-stale-count">· {issues.stale.length} 过期</span>}
      {wc != null && <span className="tnum">· 字数 {wc}</span>}
    </div>
  )
}

/** 草稿阶段演绎软门条：不阻断写作，提示 missing/stale 并提供去补。 */
function DeduceSoftGateBanner({ meta, onGoDeduce }) {
  const issues = softGateIssues(meta)
  if (!issues.needsAttention) return null
  const summary = softGateSummary(issues)
  return (
    <div
      role="status"
      data-testid="deduce-soft-gate"
      className="rounded-lg border border-warn/40 bg-warn/10 px-3 py-2 text-f12 text-ink flex items-start gap-2 flex-wrap"
    >
      <span className="font-medium text-warn shrink-0">演绎未齐</span>
      <span className="flex-1 min-w-[12rem] text-faint">{summary}（不影响继续写草稿）。</span>
      {typeof onGoDeduce === 'function' && (
        <button
          type="button"
          data-testid="deduce-soft-gate-go"
          onClick={onGoDeduce}
          className="h-7 px-2 rounded-lg border border-warn/50 bg-canvas text-f12 text-warn hover:bg-warn/10 cursor-pointer"
        >
          去补演绎
        </button>
      )}
    </div>
  )
}

function StageTitle({ title, subtitle, actions }) {
  return (
    <div className="flex flex-col items-stretch gap-1.5 min-w-0 shrink-0" data-testid="chapter-stage-title">
      <div className="min-w-0">
        <h3 data-testid="chapter-stage-heading" className="text-f13 font-medium text-ink" title={subtitle}>{title}</h3>
      </div>
      {actions && <div className={STAGE_ACTIONS} data-testid="chapter-stage-actions">{actions}</div>}
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

const SPINE_CARDS = [
  ['setting', '时空'], ['cast', '在场'], ['bite', '咬上章'],
  ['goal', '本章要'], ['obstacle', '挡'], ['inciting', '触发'],
  ['escalation', '升级'], ['choice', '选择'], ['decision', '决断'],
  ['cost', '代价'], ['info_gap', '信息差'], ['lines', '动哪条线'],
  ['hook', '钩'], ['forbid', '禁令'],
]

function spineSlotText(spine, key) {
  if (!spine || typeof spine !== 'object') return ''
  const v = spine[key]
  if (key === 'lines' && Array.isArray(v)) {
    return v.map((it) => {
      if (!it || typeof it !== 'object') return String(it || '')
      return `${it.kind || ''}:${it.id || ''} ${it.delta || ''}`.trim()
    }).filter(Boolean).join('；')
  }
  return String(v || '').trim()
}

// ——— 大纲:13 槽只读卡 + 主编种子 ———
function OutlineTab({ seq, value, meta, designOn = false }) {
  const { setChiefIntent } = useChiefSlot()
  const text = value || ''
  const spine = (meta && meta.chapter_spine && typeof meta.chapter_spine === 'object')
    ? meta.chapter_spine
    : null
  const hasSpine = !!(spine && (spine.goal || spine.choice))
  const askChief = (hint) => seedChiefNarrativeWrite(
    designOn ? 'design' : 'outline',
    designOn ? `第 ${seq} 章设计` : `第 ${seq} 章大纲`,
    hint || (designOn
      ? `请先为第 ${seq} 章立责任，再写一篇戏。`
      : `请用 13 短槽更新第 ${seq} 章章纲（选择 A vs B，动哪条线绑已有 id）。`),
  )
  return (
    <div className={STAGE_WRAP} data-testid="chapter-workbench-shell" data-phase="outline">
      <StageTitle
        title="大纲"
        subtitle="13 短槽章纲：他要什么、选了什么、付了什么、哪条线动了。由主编 / generate-stage 写入。"
        actions={(
          <>
            <Btn variant="ghost" size="sm" onClick={() => {
              setChiefIntent({ phase: 'outline', seq, text: `帮我把第 ${seq} 章写成 13 短槽章纲` })
              try { window.dispatchEvent(new CustomEvent('s3-right-tab', { detail: 'chief' })) } catch { /* */ }
            }} title="把话术带到右栏主编">
              <Sparkles size={13} />让主编生成
            </Btn>
            <Btn variant="primary" size="sm" data-testid="outline-ask-chief" onClick={() => askChief()}>
              让主编写入大纲
            </Btn>
          </>
        )}
      />
      <MetaBar meta={meta} wordCount={meta?.proseWords} />
      {hasSpine ? (
        <div className="flex-1 min-h-0 overflow-y-auto p-3" data-testid="outline-readonly">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            {SPINE_CARDS.map(([key, label]) => {
              const body = spineSlotText(spine, key)
              if (key === 'forbid' && !body) return null
              return (
                <div key={key} className="rounded-md border border-line/40 bg-canvas px-2 py-1.5">
                  <div className="text-f12 text-faint mb-0.5">{label}</div>
                  <div className="text-f13 text-ink whitespace-pre-wrap">{body || '（空）'}</div>
                </div>
              )
            })}
          </div>
        </div>
      ) : text.trim() ? (
        <SelectionQuoteActions
          scopeLabel={`第 ${seq} 章大纲`}
          className={`flex-1 min-h-0 overflow-y-auto ${STAGE_BODY} whitespace-pre-wrap`}
          data-testid="outline-readonly"
        >
          {text}
        </SelectionQuoteActions>
      ) : (
        <div className={`flex-1 min-h-0 ${STAGE_BODY}`} data-testid="outline-readonly">
          <div className="flex items-start gap-2 flex-wrap">
            <span className="text-faint flex-1">（空 · 用 generate-stage 写 13 短槽）</span>
            <button
              type="button"
              data-testid="outline-empty-ask"
              className="shrink-0 h-7 px-2 rounded-md text-f12 text-brand hover:bg-brand/10 cursor-pointer"
              onClick={() => openChiefForEmptyField({
                entityLabel: `第 ${seq} 章`,
                fieldLabel: '大纲',
                fieldKey: 'chapter_spine',
              })}
            >
              聊聊怎么写
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

// ——— 节拍 GCD 戏剧卡(PR-8):展示 goal/conflict/turn/cost/hook;手改经 patchChapter 保存 ———
// 结构增删仍可由主编审批写入;作者可补齐/改写单拍 GCD 字段(不增删条数)。
const GCD_FIELDS = [
  ['goal', '要'],
  ['conflict', '挡'],
  ['turn', '变'],
  ['choice', '选'],
  ['cost', '付'],
  ['underwater', '水下'],
]

function normalizeBeat(b) {
  if (b != null && typeof b === 'object' && !Array.isArray(b)) {
    return { ...b, text: b.text != null ? String(b.text) : '' }
  }
  return { text: b == null ? '' : String(b) }
}

/** 拍上是否已有任一 GCD 字段(非空);用于「有则展卡」与 empty 态区分。 */
function beatHasGcd(b) {
  if (!b || typeof b !== 'object') return false
  return GCD_FIELDS.some(([k]) => String(b[k] ?? '').trim() !== '')
}

function formatBeatForChief(b, i) {
  const t = b?.text || ''
  const gcd = GCD_FIELDS
    .map(([k, label]) => {
      const v = String(b?.[k] ?? '').trim()
      return v ? `${label}:${v}` : null
    })
    .filter(Boolean)
  const gcdPart = gcd.length ? ` | ${gcd.join(' · ')}` : ''
  return `${i + 1}. ${t || '（无摘要）'}${b?.done ? ' [已完成]' : ''}${gcdPart}`
}

function BeatsTab({ seq, work, value, meta, onSaved, embedded = false, allowSave = true }) {
  const toast = useToast()
  const [beats, setBeats] = useState(() => (Array.isArray(value) ? value : []).map(normalizeBeat))
  const [dirty, setDirty] = useState(false)
  const [saving, setSaving] = useState(false)
  // 无 GCD 的旧拍默认折叠;点「戏剧卡」展开空字段以便手填。
  const [forceGcd, setForceGcd] = useState(() => ({}))

  useEffect(() => {
    setBeats((Array.isArray(value) ? value : []).map(normalizeBeat))
    setDirty(false)
    setForceGcd({})
  }, [value, seq])

  useUnsavedGuard(() => dirty)

  const updateField = (i, key, val) => {
    setBeats((prev) => prev.map((b, j) => (j === i ? { ...b, [key]: val } : b)))
    setDirty(true)
  }

  const save = async () => {
    if (saving) return
    setSaving(true)
    try {
      // 整表回写：只改 GCD 短字段。场面纸 text 由主编写厚，本入口锁定。
      // emergency REST 默认关：PATCH /chapters/{seq} 403；GCD 走闸外 gcd-fields
      await api.patchChapterGcdFields(seq, { beats }, work)
      setDirty(false)
      toast('节拍已保存', { tone: 'ok' })
      onSaved?.()
    } catch (e) {
      toast(e?.body?.detail || e?.message || '节拍保存失败', { tone: 'danger' })
    } finally {
      setSaving(false)
    }
  }

  const askChief = () => seedChiefNarrativeWrite(
    embedded ? 'design' : 'beats',
    embedded ? `第 ${seq} 章设计` : `第 ${seq} 章节拍`,
    `请更新第 ${seq} 章节拍列表（每拍可含：目标/冲突/转折/代价/钩子）。当前 ${beats.length} 条:\n`
      + beats.map((b, i) => formatBeatForChief(b, i)).join('\n'),
  )

  const body = (
    <>
      {embedded && allowSave && (
        <div className="flex justify-end px-0">
          <Btn
            variant="ghost"
            size="sm"
            data-testid="beats-save"
            disabled={!dirty || saving}
            onClick={save}
            title={dirty ? '保存节拍摘要与戏核字段' : '无未保存更改'}
          >
            {saving ? <Loader2 size={13} className="animate-spin" /> : <Save size={13} />}
            {saving ? '保存中…' : '保存节拍'}
          </Btn>
        </div>
      )}
      {!embedded && <MetaBar meta={meta} wordCount={meta?.proseWords} />}
      <div
        className={embedded
          ? 'space-y-3'
          : 'flex-1 min-h-0 overflow-y-auto space-y-3'}
        data-testid="beats-list"
      >
        {beats.length === 0 ? (
          <div className={`${STAGE_BODY} flex items-start gap-2 flex-wrap`}>
            <span className="text-faint flex-1">（空 · 由主编审批写入，或让主编展开节拍）</span>
            <button
              type="button"
              data-testid="beats-empty-ask"
              className="shrink-0 h-7 px-2 rounded-md text-f12 text-brand hover:bg-brand/10 cursor-pointer"
              onClick={() => openChiefForEmptyField({
                entityLabel: `第 ${seq} 章`,
                fieldLabel: '节拍',
                fieldKey: 'beats',
              })}
            >
              聊聊怎么写
            </button>
          </div>
        ) : beats.map((b, i) => {
          const showGcd = beatHasGcd(b) || forceGcd[i]
          return (
            <div
              key={b.id || i}
              className={`rounded-lg border border-line/50 bg-surface/40 px-3 py-2.5 ${STAGE_BODY}`}
              data-testid={`beat-card-${i}`}
            >
              <div className="flex gap-2 items-start">
                <span className="text-meta text-faint shrink-0 tnum w-5 pt-1">{i + 1}.</span>
                {b.done ? <span className="text-ok shrink-0 pt-1">✓</span> : null}
                <div className="flex-1 min-w-0 space-y-2">
                  <div
                    className="w-full whitespace-pre-wrap break-words rounded-md border border-line/40 bg-canvas px-2 py-1.5 text-f13 text-ink leading-relaxed"
                    data-testid={`beat-text-${i}`}
                    aria-label={`第 ${i + 1} 拍场面纸`}
                    title="场面纸由主编写厚；这里只改戏核字段"
                  >
                    {(b.text || '').trim() || '场面纸（只读 · 让主编写厚）'}
                  </div>
                  {showGcd ? (
                    <div
                      className="grid grid-cols-1 sm:grid-cols-2 gap-2"
                      data-testid={`beat-gcd-${i}`}
                    >
                      {GCD_FIELDS.map(([key, label]) => (
                        <label key={key} className="block text-meta min-w-0">
                          <span className="mb-0.5 block text-faint text-f12">{label}</span>
                          <textarea
                            className="w-full min-h-[2.75rem] resize-y rounded-md border border-line/40 bg-canvas px-2 py-1 text-f13 text-ink leading-snug outline-none focus:border-brand/50"
                            value={b[key] != null ? String(b[key]) : ''}
                            onChange={(e) => updateField(i, key, e.target.value)}
                            placeholder={label}
                            data-testid={`beat-gcd-${i}-${key}`}
                            aria-label={`第 ${i + 1} 拍${label}`}
                          />
                        </label>
                      ))}
                    </div>
                  ) : (
                    <button
                      type="button"
                      className="text-f12 text-brand hover:underline cursor-pointer"
                      data-testid={`beat-gcd-expand-${i}`}
                      onClick={() => setForceGcd((m) => ({ ...m, [i]: true }))}
                    >
                      补戏核（要/挡/变/选/付/水下）
                    </button>
                  )}
                </div>
              </div>
            </div>
          )
        })}
      </div>
      <div className="text-f12 text-faint leading-snug">
        {dirty
          ? '有未保存更改 · 点「保存节拍」写入。'
          : '已写戏核的拍会自动展开；没有的可点「补戏核」。改完点保存即可。'}
      </div>
    </>
  )
  if (embedded) return body
  return (
    <div className={STAGE_WRAP} data-testid="chapter-workbench-shell" data-phase="beats">
      <StageTitle
        title="节拍"
        subtitle="每拍可补「目标·冲突·转折·代价·钩子」；场面纸只读，改写请让主编。增删条数须审批。"
        actions={(
          <>
            <Btn
              variant="ghost"
              size="sm"
              data-testid="beats-save"
              disabled={!dirty || saving}
              onClick={save}
              title={dirty ? '保存节拍摘要与戏核字段' : '无未保存更改'}
            >
              {saving ? <Loader2 size={13} className="animate-spin" /> : <Save size={13} />}
              {saving ? '保存中…' : '保存节拍'}
            </Btn>
            <Btn variant="primary" size="sm" data-testid="beats-ask-chief" onClick={askChief}>
              让主编写入节拍
            </Btn>
          </>
        )}
      />
      {body}
    </div>
  )
}

function contractFieldText(node) {
  if (!node || typeof node !== 'object') return ''
  return String(node.text || node.quote || '').trim()
}

function missingPlay(err) {
  const code = err?.body?.detail?.code || err?.body?.code
  return err?.status === 404
    || code === 'play_missing'
    || code === 'contract_missing'
    || code === 'duty_missing'
}

function DesignTab({ seq, work, meta, onSaved }) {
  const { setChiefIntent } = useChiefSlot()
  const [duty, setDuty] = useState(null)
  const [later, setLater] = useState([])
  const play = meta?.play ?? null
  const contract = meta?.contract ?? null
  const loadingPlay = !(meta && Object.prototype.hasOwnProperty.call(meta, 'play'))
  const loadErr = meta?.playErr || ''
  useEffect(() => {
    let alive = true
    const dutyFn = typeof api.chapterDuty === 'function' ? api.chapterDuty : null
    if (dutyFn) {
      dutyFn(seq, work)
        .then((d) => { if (alive) setDuty(d) })
        .catch((e) => { if (alive) setDuty(missingPlay(e) ? null : null) })
    }
    if (typeof api.outline === 'function') {
      api.outline()
        .then((data) => {
          if (!alive) return
          setLater(remainingLaterFromOutline(data, seq, { volume: meta?.volume }))
        })
        .catch(() => { if (alive) setLater([]) })
    }
    return () => { alive = false }
  }, [seq, work, meta?.volume])

  const playText = String(play?.text || '').trim()
  const fields = (contract && typeof contract.fields === 'object') ? contract.fields : {}
  const nails = [
    ['他要什么', contractFieldText(fields.goal)],
    ['两难', contractFieldText(fields.choice)],
    ['他做了什么', contractFieldText(fields.decision)],
    ['付了什么', contractFieldText(fields.cost)],
    ['没做完的', contractFieldText(fields.hook)],
  ].filter(([, t]) => t)
  const contractBeats = Array.isArray(contract?.beats) ? contract.beats.filter(Boolean) : []
  const usePlay = !!playText
  const beatRows = usePlay ? contractBeats : []
  const beatN = beatRows.length
  const jumpTo = (id) => {
    const el = document.getElementById(id)
    if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }
  const askChief = (hint) => seedChiefNarrativeWrite(
    'design',
    `第 ${seq} 章设计`,
    hint || `请先为第 ${seq} 章立责任，再写一篇戏。`,
  )
  const happen = String(duty?.must_happen || duty?.body?.must_happen || '').trim()
  return (
    <div className={STAGE_WRAP} data-testid="chapter-workbench-shell" data-phase="design">
      <StageTitle
        title="章设计"
        subtitle="先读这场戏，再看从戏里抄出的要、选、付、钩。"
        actions={(
          <>
            <Btn variant="ghost" size="sm" onClick={() => {
              setChiefIntent({ phase: 'design', seq, text: `帮我把第 ${seq} 章写成戏` })
              try { window.dispatchEvent(new CustomEvent('s3-right-tab', { detail: 'chief' })) } catch { /* */ }
            }} title="把话术带到右栏主编">
              <Sparkles size={13} />让主编生成
            </Btn>
            <Btn variant="primary" size="sm" data-testid="outline-ask-chief" onClick={() => askChief()}>
              让主编写设计
            </Btn>
          </>
        )}
      />
      <MetaBar meta={meta} wordCount={meta?.proseWords} />
      <div className="flex items-center gap-2 px-3 shrink-0" data-testid="design-jump">
        <button
          type="button"
          className="h-7 px-2 rounded-md text-f12 border border-line/50 hover:bg-canvas cursor-pointer"
          data-testid="design-jump-spine"
          onClick={() => jumpTo('chapter-play')}
        >
          这场戏
        </button>
        <button
          type="button"
          className="h-7 px-2 rounded-md text-f12 border border-line/50 hover:bg-canvas cursor-pointer"
          data-testid="design-jump-beats"
          onClick={() => jumpTo('chapter-beats')}
        >
          {usePlay || nails.length ? `从戏里抄出的${beatN ? ` · ${beatN} 拍` : ''}` : '从戏里抄出的'}
        </button>
      </div>
      <div className="flex-1 min-h-0 overflow-y-auto flex flex-col gap-4 p-3">
        {happen ? (
          <div className="text-f13 text-ink" data-testid="design-duty">今晚要办：{happen}</div>
        ) : null}
        {later.length > 0 ? (
          <section data-testid="design-remaining-later" className="space-y-1">
            <div className="text-f12 text-faint">本卷还没办的</div>
            {later.map((ch) => (
              <div key={ch.seq} className="text-f13 text-ink">
                第{ch.seq}章《{ch.title || ''}》：{chapterAccountLine(ch)}
              </div>
            ))}
          </section>
        ) : null}
        <div id="chapter-play" data-testid="outline-readonly">
          {loadingPlay ? (
            <div className="text-faint text-f13">正在载入这场戏…</div>
          ) : loadErr ? (
            <div role="alert" className="text-f13 text-danger">{loadErr}</div>
          ) : usePlay ? (
            <div className="text-f13 text-ink whitespace-pre-wrap leading-relaxed" data-testid="design-play-text">{playText}</div>
          ) : (
            <div className="text-faint text-f13">（还没有这场戏 · 让主编先写设计）</div>
          )}
        </div>
        <section id="chapter-beats" data-testid="design-beats-section" className="shrink-0 space-y-3">
          {usePlay || nails.length ? (
            <>
              {nails.length > 0 && (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2" data-testid="design-contract-nails">
                  {nails.map(([label, body]) => (
                    <div key={label} className="rounded-md border border-line/40 bg-canvas px-2 py-1.5">
                      <div className="text-f12 text-faint mb-0.5">{label}</div>
                      <div className="text-f13 text-ink whitespace-pre-wrap">{body}</div>
                    </div>
                  ))}
                </div>
              )}
              {beatN > 0 && beatRows.map((b, i) => (
                <div key={b.n || b.id || i} className="space-y-1" data-testid={`beat-card-${i}`}>
                  <div className="text-f12 text-faint">第 {b.n || i + 1} 拍</div>
                  <div className="text-f13 text-ink whitespace-pre-wrap">
                    {contractFieldText(b.goal) || contractFieldText(b.turn) || String(b.text || '').trim() || '（这一拍还没从戏里抄出）'}
                  </div>
                </div>
              ))}
            </>
          ) : (
            <div className="text-faint text-f13">（还没有这场戏 · 让主编先写设计）</div>
          )}
        </section>
      </div>
    </div>
  )
}

// ——— 草稿:编辑器,初值 latestDraft,存草稿 saveDraft;采用=进正文(回调切到正文 tab) ———
function DraftTab({ seq, work, meta, onAdopt, onGoDeduce }) {
  const toast = useToast()
  const { setChiefIntent } = useChiefSlot()
  // L1 轻选 pick / 右坞恢复会 bump RestoreContext → 重拉 /latest-draft,否则点选后
  // 已开着的草稿 tab 仍显示旧空稿(onFinalized 只触达 prose 中区时的旧缺口)。
  const restoreTick = useContext(RestoreContext)
  const [text, setText] = useState('')
  const [summary, setSummary] = useState('')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [checking, setChecking] = useState(false)   // 断头修复#22:草稿质检
  const [checkRes, setCheckRes] = useState(null)
  // 待落草稿(块二并入通用 stageProposal 通道):phase/seq 匹配且内容非空才提示(防切章/切阶段串台)。
  const { pending, clear } = useStageProposal('draft', seq)
  // Task 2:选区「改这段」的锚点(阶段级 state,切章/放弃/落地清空)。
  const [selAnchor, setSelAnchor] = useState(null)
  useEffect(() => { setSelAnchor(null) }, [seq])
  const matchedAnchor = selAnchor ? matchSelAnchor(text, selAnchor) : null
  const onSelAction = ({ text: selText, intent }) => {
    if (intent === 'discuss') {
      setChiefIntent({ phase: 'draft', seq, text: selDiscussPrompt('草稿', selText) })
    } else {
      setChiefIntent({ phase: 'draft', seq, text: selEditPrompt(selText) })
      setSelAnchor(selText)
    }
    try { window.dispatchEvent(new CustomEvent('s3-right-tab', { detail: 'chief' })) } catch { /* */ }
  }
  // 落进后置 dirty,靠既有 flush(切章/存草稿)落库;同时清除待落。
  const recordManualMaterialReference = (p) => {
    if (!p?.materialId) return
    api.addMaterialReference(p.materialId, {
      chapter: seq,
      dimension: 'manual_insert',
      reason: '作者采纳素材插稿',
    }).catch((e) => toast('素材溯源记录失败:' + (e?.message || ''), { tone: 'danger' }))
  }
  const fillDraft = () => {
    if (!pending) return
    setText(pending.content); draftRef.current.dirty = true
    recordManualMaterialReference(pending)
    clear(); setSelAnchor(null); toast('已填入草稿框')
  }
  const appendDraft = () => {
    if (!pending) return
    setText((prev) => (prev ? prev + '\n\n' : '') + pending.content); draftRef.current.dirty = true
    recordManualMaterialReference(pending)
    clear(); setSelAnchor(null); toast('已追加到草稿')
  }
  // 替换选中段:仅置 dirty,不强制立即 saveDraft(草稿区放手写,不上保存节奏)。
  const replaceSelection = () => {
    if (!pending || !matchedAnchor) return
    const next = text.replace(matchedAnchor, pending.content)
    setText(next)
    draftRef.current.text = next
    draftRef.current.dirty = true
    recordManualMaterialReference(pending)
    clear(); setSelAnchor(null)
    toast('已替换选中段')
  }
  // 换章防丢:draftRef 只持「实时 text/summary/dirty」(渲染时刷新);seq 不放 ref
  // ——因 draftRef.current.seq=seq 会在换章渲染时先变成新 seq,导致 cleanup 拿错章号。
  // 旧章 seq 改由 effect 闭包捕获(myseq),cleanup 时用它,保证 flush 落到正确的旧章。
  const draftRef = useRef({ text: '', summary: '', dirty: false })
  draftRef.current.text = text
  draftRef.current.summary = summary
  useUnsavedGuard(() => draftRef.current.dirty)

  // 拉取:seq 变或 restoreTick(L1 pick / 版本恢复)变 → 重读 /latest-draft。
  useEffect(() => {
    let alive = true
    setLoading(true)
    api.latestDraft(seq)
      .then((d) => {
        if (!alive) return
        const fromVer = String(d?.prose || '').trim()
        const fromCh = String(meta?.draft || '').trim()
        setText(fromVer || fromCh)
        setSummary(d?.summary || '')
        draftRef.current.dirty = false
      })
      .catch(() => {
        if (alive && meta?.draft) setText(String(meta.draft))
      })
      .finally(() => { if (alive) setLoading(false) })
    return () => { alive = false }
  }, [seq, restoreTick, meta?.draft])

  // 仅换章/卸载 flush 脏稿。不绑 restoreTick——否则 cleanup 会把旧 buffer
  // 经 saveDraft 写回,盖掉 L1 pick / 版本恢复刚落的 stage=draft 种子。
  useEffect(() => {
    const myseq = seq
    const mywork = work
    return () => {
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
    try {
      await api.saveDraft(seq, text, summary)
      draftRef.current.dirty = false
      await onAdopt?.(text)
      toast('已采用为正文,切到正文 tab 继续打磨')
    } catch (e) {
      toast('采用失败:' + adoptFailureMessage(e), { tone: 'danger' })
    }
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
            <Btn variant="ghost" size="sm" onClick={() => {
              setChiefIntent({ phase: 'draft', seq, text: `据大纲和节拍给第 ${seq} 章写一版草稿` })
              try { window.dispatchEvent(new CustomEvent('s3-right-tab', { detail: 'chief' })) } catch { /* */ }
            }} title="把话术带到右栏主编,生成后可一键填入">
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
      <DeduceSoftGateBanner meta={meta} onGoDeduce={onGoDeduce} />
      {pending && (
        <ProposalBar
          text={`主编生成了本章草稿(${pending.content.replace(/\s/g, '').length} 字),可直接落进草稿框。`}
          actions={matchedAnchor
            ? [{ label: '替换选中段', variant: 'primary', onClick: replaceSelection }, { label: '追加到草稿', onClick: appendDraft }]
            : [{ label: '填入草稿框', variant: 'primary', onClick: fillDraft }, { label: '追加到草稿', onClick: appendDraft }]}
          onDismiss={() => { clear(); setSelAnchor(null) }}
        />
      )}
      {pending && selAnchor && !matchedAnchor && (
        <div className="text-f12 text-warn">选中段无法精确定位,按原方式落地</div>
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
              ['全知', cnt(q.god_view)], ['退化', cnt(q.degeneration)],
              ['水字', cnt(q.filler)], ['三连', cnt(q.rule_of_three)],
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
        onSelAction={onSelAction}
        placeholder="在此自由起草,或在右栏让主编据大纲/节拍生成草稿。满意后『采用为正文』搬进正文 tab 做护栏/QC 打磨。"
        className="flex-1 min-h-0"
      />
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
  const [designOn, setDesignOn] = useState(true)
  useEffect(() => {
    let alive = true
    const fetchCaps = api.fetchCapabilities
    if (typeof fetchCaps !== 'function') return undefined
    fetchCaps().then((c) => {
      if (!alive) return
      if (c?.flags && 'chapter_design' in c.flags) setDesignOn(!!c.flags.chapter_design)
    }).catch(() => {})
    return () => { alive = false }
  }, [])
  const visiblePhases = designOn ? PHASES_DESIGN : PHASES_LEGACY
  // 初值优先吃 selection 的 phase 提示(全书大纲点章行→直落大纲阶段,不闪上次阶段)
  const [phase, setPhase] = useState(() => normalizePhase(readStoredPhase(work, seq) || initialPhase || 'final'))
  // 只在真正换章或新的显式阶段指令到达时消费 initialPhase。布局重挂载时 ref
  // 初始化为当前值，不会把刚保存的正文阶段重置为目录默认的大纲。
  const phaseDirectiveRef = useRef({ seq, initialPhase })
  const [meta, setMeta] = useState(null)   // {title, synopsis, beats}
  const [loading, setLoading] = useState(true)
  const [refresh, setRefresh] = useState(0)
  const [archiveOpen, setArchiveOpen] = useState(false)
  const [moreOpen, setMoreOpen] = useState(false)   // 「更多」菜单(归档入口)
  // 章节辅助视图(栏3 内容区切换):null=显示阶段内容,'brief'|'frame'|'northstar'|'pressure'=
  // 内容区替换为 ChapterAuxPanel 并高亮对应头部入口。受控直连 ChapterAuxPanel 的 tab
  // (面板内 tab 互切回写此值,头部高亮永远等于正在看的 tab)。
  // 返回语义(双通道,均不丢 phase):
  //   · 点任一阶段页签 → auxView 置 null,回到该阶段内容(phase state 全程保留);
  //   · 再点当前高亮的辅助入口 → toggle 关闭,回到离开时的阶段。
  const [auxView, setAuxView] = useState(null)
  const [chapterMetaOpen, setChapterMetaOpen] = useState(false)
  // IA 渐进披露:仅 localStorage s3.ia.density；未设置默认 essential
  const [iaDensity, setIaDensity] = useState(() => loadIaDensity())
  const visibleAux = AUX_ENTRIES.filter((e) => auxVisibleForDensity(iaDensity, e.key))
  const cycleDensity = () => {
    const order = ['essential', 'standard', 'full']
    const i = order.indexOf(iaDensity)
    const next = order[(i < 0 ? 0 : i + 1) % order.length]
    setIaDensity(saveIaDensity(next))
    // 若当前辅助 tab 在新密度下不可见，收起
    if (auxView && !auxVisibleForDensity(next, auxView)) setAuxView(null)
  }

  // 草稿软门:切到草稿时若 missing/stale/空真相 → toast + 草稿页常驻 banner(不阻断)。
  // 正文 soft:切到 final 且契约 B1/B2/B3 缺口 → toast；banner 另见 ContractSoftBanner。
  // Task 7:演绎已是章内真阶段,删除派发 s3-open-capability 的 deduce 特例,直接就地切换。
  const setPhaseP = useCallback((p) => {
    const nextPhase = normalizePhase(p, designOn)
    if (p === 'draft' && meta) {
      const issues = softGateIssues(meta)
      if (issues.needsAttention) {
        const summary = softGateSummary(issues)
        toast(`${summary}(不影响继续)`, {
          tone: 'warn',
          action: { label: '去补', onClick: () => setPhaseP('deduce') },
        })
      }
    }
    if (nextPhase === 'final' && meta && contractNeedsAttention(meta)) {
      const summary = contractSoftSummary(meta)
      toast(`这场还没定必须发生（不拦先写日子）${summary ? `：${summary}` : ''}`, {
        tone: 'warn',
        action: {
          label: '去补',
          onClick: () => {
            const c = evaluateChapterContract(meta)
            if (!c.synopsisOk || !c.beatsOk) setPhaseP(designOn ? 'design' : (!c.synopsisOk ? 'outline' : 'beats'))
            else setPhaseP('deduce')
          },
        },
      })
    }
    setPhase(nextPhase)
    localStorage.setItem(phaseStorageKey(work, seq), nextPhase)
    // 保留旧键给未迁移的相邻界面/测试读取；当前 ChapterStudio 以作品+章键为准。
    localStorage.setItem('s3.chapter.phase', nextPhase)
    setAuxView(null)
    setChapterMetaOpen(false)
  }, [meta, toast, work, seq, designOn])

  // L1 轻选 pick 等右坞动作派发 s3-chapter-phase → 切到草稿,作者立刻看到种子。
  useEffect(() => {
    const onPhase = (e) => {
      const ph = e?.detail?.phase
      const targetSeq = e?.detail?.seq
      if (!ph) return
      if (targetSeq != null && Number(targetSeq) !== Number(seq)) return
      setPhaseP(ph)
    }
    window.addEventListener('s3-chapter-phase', onPhase)
    return () => window.removeEventListener('s3-chapter-phase', onPhase)
  }, [seq, setPhaseP])

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
    const previous = phaseDirectiveRef.current
    const changedChapter = Number(previous.seq) !== Number(seq)
    const changedDirective = previous.initialPhase !== initialPhase
    if (changedChapter || changedDirective) {
      phaseDirectiveRef.current = { seq, initialPhase }
      setPhaseP(normalizePhase(initialPhase || readStoredPhase(work, seq) || 'final', designOn))
    }
  }, [work, seq, initialPhase, setPhaseP, designOn])

  useEffect(() => {
    if (!designOn) return
    if (phase === 'outline' || phase === 'beats') setPhase('design')
  }, [designOn, phase])

  // 把当前阶段发布给右栏 ChiefDock:正文=写作槽;大纲/节拍/草稿=讨论(右栏 chat 不再消失)。
  const { setChapterPhase } = useChiefSlot()
  useEffect(() => { setChapterPhase(phase); return () => setChapterPhase(null) }, [phase, setChapterPhase])

  // F-06 场景级跳转:点项目树「场景」节点(sceneIdx 非空)→ 强制切到「正文」tab,
  // 由 WriteLayout 在正文加载后调 focusScene(sceneIdx) 滚到对应场景段。
  useEffect(() => {
    if (sceneIdx != null && phase !== 'final') setPhaseP('final')
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sceneIdx])

  // 契约字段与 phase 解耦：任意 phase（含 final）在 seq/refresh 变化时拉取。
  // final 不 setLoading 挡 WriteLayout；阶段编辑器切章时可用 loading 占位。
  // refresh 静默刷新,不卸载中区编辑器——否则演绎落库 refresh→loading 竞态冲掉 scene_truth。
  const metaKey = useRef('')
  const [bannerTick, setBannerTick] = useState(0) // dismiss 后强制重渲 banner
  const [executionSoft, setExecutionSoft] = useState(null)
  useEffect(() => {
    let alive = true
    const key = String(seq)
    const seqChanged = metaKey.current !== key
    if (seqChanged) {
      metaKey.current = key
      if (META_EDITOR_PHASES.has(phase)) setLoading(true)
      else setLoading(false)
      setExecutionSoft(null)
    }
    const playP = typeof api.chapterPlay === 'function'
      ? api.chapterPlay(seq, work).catch((e) => (missingPlay(e) ? null : Promise.reject(e)))
      : Promise.resolve(null)
    const contractP = typeof api.chapterContract === 'function'
      ? api.chapterContract(seq, work).catch((e) => (missingPlay(e) ? null : Promise.reject(e)))
      : Promise.resolve(null)
    Promise.all([
      api.chapter(seq, work, { includeSuggest: true }),
      playP,
      contractP,
    ])
      .then(([ch, p, c]) => {
        if (!alive) return
        setMeta((m) => ({
          ...(m || {}),
          title: ch?.title || '',
          synopsis: ch?.synopsis || '',
          beats: ch?.beats || [],
          label: ch?.label || '',
          volume: ch?.volume || '',
          focalizer: ch?.focalizer || '',
          scene_truth: ch?.scene_truth || '',
          scene_truth_revision: ch?.scene_truth_revision ?? 0,
          deductions: ch?.deductions || [],
          chars: ch?.chars || [],
          deduce: ch?.deduce || null,
          involved_characters: ch?.involved_characters || [],
          proseWords: (ch?.prose || '').replace(/\s/g, '').length,
          seq,
          narrative_contract: ch?.narrative_contract || {},
          chapter_spine: ch?.chapter_spine || {},
          scene_suggest: ch?.scene_suggest || null,
          play: p,
          contract: c,
          playErr: '',
        }))
      })
      .catch((e) => {
        if (!alive) return
        setMeta((m) => ({
          ...(m || {}),
          title: '', synopsis: '', beats: [], label: '', volume: '',
          focalizer: '', scene_truth: '', scene_truth_revision: 0,
          deductions: [], involved_characters: [], proseWords: 0,
          play: null,
          contract: null,
          playErr: e?.body?.detail?.message || e?.message || '',
        }))
      })
      .finally(() => { if (alive) setLoading(false) })
    api.entities().then((es) => {
      if (alive) setMeta((m) => ({ ...(m || {}), chars: es.filter((e) => e.kind === 'character') }))
    }).catch(() => {})
    // 执行 soft（同源 API · 失败静默 · 仅 advisory）
    if (typeof api.executionSoftStatus === 'function') {
      api.executionSoftStatus(seq)
        .then((s) => { if (alive) setExecutionSoft(s || null) })
        .catch(() => { if (alive) setExecutionSoft(null) })
    }
    return () => { alive = false }
    // phase 变化不重拉；final/冷启动也依赖本 effect 填 meta 以驱动 soft banner
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [seq, refresh])

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
            {visibleAux.map((entry) => {
              const Icon = entry.icon
              const active = auxView === entry.key
              return (
                <button key={entry.key} type="button" aria-pressed={active} aria-label={entry.label}
                  onClick={() => { setChapterMetaOpen(false); setAuxView(active ? null : entry.key) }}
                  title={active ? `${entry.label} · 再点一次回到写作阶段` : (entry.tip || `${entry.label} · 在本栏展开章节辅助`)}
                  className={`inline-flex items-center justify-center h-7 w-7 rounded-md cursor-pointer transition-colors ${
                    active ? 'bg-surface text-brand ring-1 ring-line' : 'text-faint hover:bg-surface hover:text-ink'
                  }`}>
                  <Icon size={13} />
                </button>
              )
            })}
            <button type="button" onClick={cycleDensity}
              data-testid="ia-density-toggle"
              title={`信息密度 ${iaDensity}（localStorage s3.ia.density；点切换）`}
              className="inline-flex items-center h-7 rounded-md px-1.5 text-meta text-faint hover:text-ink cursor-pointer"
            >
              {iaDensity === 'essential' ? '简' : iaDensity === 'standard' ? '标' : '全'}
            </button>
          </div>
          <span className="w-px h-4 bg-line mx-0.5" aria-hidden="true" />
          <Btn variant="ghost" size="sm" icon onClick={() => { setAuxView(null); setChapterMetaOpen(true) }}
            title="章节信息：大纲、节拍、场景真相等摘要" aria-label="章节信息"><Settings2 size={14} /></Btn>
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
  const showChapterMeta = chapterMetaOpen && seq != null
  return (
    <ObjectFrame
      compact
      fill
      breadcrumb="手稿"
      title={meta?.title || `第 ${seq} 章`}
      tabs={visiblePhases.map((p) => ({ value: p.key, label: p.label, title: p.duty }))}
      activeTab={showAux || showChapterMeta ? null : phase}
      onTab={(p) => { setAuxView(null); setChapterMetaOpen(false); setPhaseP(p) }}
      actions={frameActions}
    >
      {showChapterMeta ? (
        <div className="h-full min-h-0 overflow-y-auto bg-canvas">
          <ChapterMetaPane
            seq={seq}
            work={work}
            onClose={() => setChapterMetaOpen(false)}
            onNavigatePhase={(p) => setPhaseP(p)}
            onOpenAux={(key) => {
              setChapterMetaOpen(false)
              setAuxView(key)
            }}
          />
        </div>
      ) : showAux ? (
        <div className="h-full min-h-0" data-testid="chapter-aux-view">
          {/* key 只含章号:切章重挂重拉(角色候选等);受控 tab 切换不重挂,不白重拉数据。
              崩溃只塌辅助视图,头部入口仍在,可切回阶段。 */}
          <ErrorBoundary key={`aux:${seq}`}>
            <ChapterAuxPanel seq={seq} tab={auxView} onTabChange={setAuxView} onSelectNode={onSelectNode} />
          </ErrorBoundary>
        </div>
      ) : phase === 'final' ? (
        <div className="h-full flex flex-col min-h-0">
          <span className="hidden" aria-hidden data-banner-tick={bannerTick} />
          <ScenePaper chapter={meta} seq={seq} />
          <ContractSoftBanner
            work={work}
            seq={seq}
            meta={meta}
            executionSoft={executionSoft}
            onGoFix={() => {
              const c = evaluateChapterContract(meta || {})
              const hasExecGap = executionSoft?.soft_fulfill?.ok_soft === false
                || executionSoft?.drift?.drift
              if (!c.synopsisOk || !c.beatsOk) setPhaseP(designOn ? 'design' : (!c.synopsisOk ? 'outline' : 'beats'))
              else if (!c.sceneTruthOk) setPhaseP('deduce')
              else if (hasExecGap) setChapterMetaOpen(true)
              else setPhaseP('deduce')
            }}
            onDismiss={() => {
              dismissContractBanner(work, seq)
              setBannerTick((t) => t + 1)
            }}
          />
          <ChapterMaterialRefs seq={seq} onSelectMaterial={onSelectNode} />
          <div className="flex-1 min-h-0">
            {/* I4:不再传 onSeqChange——WriteLayout 内部步进器已删,换章单向走外部 seq prop */}
            <WriteLayout key={work} work={work} seq={seq} sceneIdx={sceneIdx} />
          </div>
        </div>
      ) : (
        <div className="h-full min-h-0 overflow-hidden flex flex-col bg-canvas">
          {loading ? (
            <div className="flex items-center justify-center py-16 text-faint"><Loader2 size={18} className="animate-spin mr-2" />加载…</div>
          ) : (phase === 'design' || (designOn && (phase === 'outline' || phase === 'beats'))) ? (
            <DesignTab seq={seq} work={work} meta={meta} onSaved={() => setRefresh((r) => r + 1)} />
          ) : phase === 'outline' ? (
            <OutlineTab seq={seq} work={work} value={meta?.synopsis} meta={meta} onSaved={() => setRefresh((r) => r + 1)} />
          ) : phase === 'beats' ? (
            <BeatsTab seq={seq} work={work} value={meta?.beats} meta={meta} onSaved={() => setRefresh((r) => r + 1)} />
          ) : phase === 'deduce' ? (
            // 演绎就地渲染(Task 7):与左栏演绎能力 deduce_view 两入口互斥不冲突,共用 DeduceProvider 选中态。
            <DeduceStage seq={seq} meta={meta} work={work} onSaved={() => setRefresh((r) => r + 1)} />
          ) : phase === 'draft' ? (
            <div className="h-full min-h-0 flex flex-col">
            <ScenePaper chapter={meta} seq={seq} />
            <div className="flex-1 min-h-0">
            <DraftTab seq={seq} work={work} meta={meta} onGoDeduce={() => setPhaseP('deduce')} onAdopt={async (text) => {
              // 采用为正文=把草稿真搬进 chapter.prose(彻查 B-4:旧实现丢弃 text 只切 tab → 正文空/旧)。
              // 保留本章 title/focalizer;落库成功后再切正文 tab,让 WriteLayout 拉到刚搬入的正文。
              await api.saveChapter(seq, text, meta?.title || '', meta?.focalizer || '')
              setPhaseP('final')
            }} />
            </div>
            </div>
          ) : null}
        </div>
      )}
      {archiveDialog}
    </ObjectFrame>
  )
}
