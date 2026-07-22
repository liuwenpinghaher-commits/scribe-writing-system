/**
 * TimelineView · 作者工具 F-02 · 时间线泳道(vis-timeline 重写,波A)
 *
 * 根治三痛点(替代原手搓 SVG 网格):
 *   1. 信息叠加 —— 同章多事件交给 vis-timeline groups 内的自动堆叠(stack),不再 left+=idx*5。
 *   2. 节点不可点看详情 —— select 事件 → 右侧详情面板展示该 item 完整字段;双击/按钮再跳章。
 *   3. 千万字横向无虚拟化 —— vis-timeline 原生窗口化(只渲染可视区间)+ 滚轮缩放 + 拖动。
 *
 * 章号轴:scribe3 以「章号」(整数)为时间轴。vis-timeline 偏好 Date,故把
 *   第 N 章 映射为合成时间 chapterToDate(N) = 2000-01-01 + (N-1) 天;
 *   反向 dateToChapter 用于 select/缩放窗口。轴标签经 format.minorLabels 显示「第N章」。
 *
 * 泳道(groups,可切换):
 *   - kind(默认):事件 / 伏笔 / 弧光 / 关系 四类各一道。
 *   - char:按焦点角色(参与/见证)分道 + 固定「伏笔」道。
 *   - type:按事件类型分道(仅事件)。
 * item:
 *   - 事件 / 弧光 / 伏笔收点 / 关系失效 → 点类型(type:'point' / 'box')。
 *   - 伏笔(setup→payoff)、关系(since→until)→ 区间(type:'range',带 start+end)。
 *     未收 / 未失效 → end = 全书末章(开口区间)。
 *
 * 数据源:api.timeline(from,to,axis) → /timeline(store.timeline)。
 * 对外接口不变:<TimelineView onJumpChapter={fn} />(DetailPane 在用)。
 * spec: docs/系统文档/作者工具/02-时间线视图.md
 */
import { useEffect, useRef, useState, useMemo, useCallback } from 'react'
import { Timeline } from 'vis-timeline/standalone'
import { DataSet } from 'vis-data/standalone'
import 'vis-timeline/styles/vis-timeline-graph2d.css'
import { Clock, RefreshCw, X, CornerDownRight, AlertTriangle, List } from 'lucide-react'
import { api } from '../api'
import { relColor, relLabel } from '../lib/relColors'
import { hasNarrativeData } from '../lib/timelineAxis'
import { prefersReducedMotion } from '../lib/utils'
import { useSelection } from '../selectionContext'

// ── 章号 ⇄ 合成时间 ─────────────────────────────────────────────────────────
// 第 N 章 → 2000-01-01 起第 (N-1) 天。一天一章,vis 缩放/堆叠按天粒度天然贴合。
const EPOCH = Date.UTC(2000, 0, 1)
const DAY = 86400000
const chToDate = (ch) => new Date(EPOCH + (ch - 1) * DAY)
const dateToCh = (d) => Math.round((d.getTime() - EPOCH) / DAY) + 1

// ── 配色(对齐产品 token 家族:brand / irony / secret / fore / ok / danger / faint) ──
// vis-timeline 要可序列化的色值;运行时从 CSS 变量读,缺省回落到 light 真源。
function tok(name, fallback) {
  if (typeof window === 'undefined') return fallback
  const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim()
  return v || fallback
}
const palette = () => ({
  brand: tok('--color-brand', '#2f6b5d'),
  irony: tok('--color-irony', '#4f76a3'),
  secret: tok('--color-secret', '#9c5f86'),
  fore: tok('--color-fore', '#c2683a'),
  ok: tok('--color-ok', '#2f6b4f'),
  danger: tok('--color-danger', '#9d3838'),
  faint: tok('--color-faint', '#65706a'),
})
const EVENT_TYPE_COLOR = () => {
  const p = palette()
  return {
    炼器: p.secret, 战斗: p.danger, 拜师: p.irony,
    对话: p.ok, 决策: p.fore, 失去: p.secret, 获得: p.ok,
  }
}
const evColor = (t) => EVENT_TYPE_COLOR()[t] || palette().faint
const ARC_COLORS = () => {
  const p = palette()
  return { ability: p.secret, relation: p.irony, personality: p.secret, composite: p.fore }
}
const arcColor = (ct) => ARC_COLORS()[ct] || palette().faint
const PROMISE_COLOR = () => palette().fore
const PROMISE_HERRING = () => palette().faint

const stripRole = (id) => (id || '').replace(/^role:/, '')
const esc = (s) => String(s ?? '').replace(/[&<>"]/g, (c) => (
  { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]
))

// 固定 group id(kind 模式 / char 模式的伏笔道)
const G_EVENT = '__event__'
const G_PROMISE = '__promise__'
const G_ARC = '__arc__'
const G_RELATION = '__relation__'

// ── items / groups 构建 ─────────────────────────────────────────────────────
/**
 * 把 timeline items(后端结构)转成 vis DataSet 的 items + groups。
 * 返回 { items, groups }。每个 vis item 挂 `_raw`(原始 item)+ `_jump`(跳章号)
 * 供 select 详情面板与跳章使用。
 */
function buildVis(rawItems, laneMode, maxCh) {
  const groups = new Map()   // id → {id, content, _order}
  const items = []
  const endCh = maxCh || 1

  const ensureGroup = (id, content, order) => {
    if (!groups.has(id)) groups.set(id, { id, content, _order: order })
  }

  // 关系配对(start id 形如 "src->dst@sc";end id "src->dst@end{uc}")
  const relStarts = rawItems.filter((i) => i.kind === 'relation_start')
  const promSetups = rawItems.filter((i) => i.kind === 'promise_setup')
  const promPayoffs = rawItems.filter((i) => i.kind === 'promise_payoff')

  // 角色道排序辅助:char 模式下角色名稳定排序
  const charOrder = new Map()
  if (laneMode === 'char') {
    const chars = new Set()
    for (const it of rawItems) for (const lk of it.lane_keys || []) {
      if (lk !== G_PROMISE) chars.add(lk)
    }
    ;[...chars].sort().forEach((c, i) => charOrder.set(c, i))
  }

  // 给一个 item 决定它落到哪些 group(可多道)
  const groupsFor = (it) => {
    if (laneMode === 'kind') {
      if (it.kind === 'event') return [G_EVENT]
      if (it.kind === 'arc') return [G_ARC]
      if (it.kind === 'promise_setup' || it.kind === 'promise_payoff') return [G_PROMISE]
      return [G_RELATION] // relation_start/end
    }
    if (laneMode === 'type') {
      if (it.kind !== 'event') return [] // type 模式只看事件
      return ['et:' + (it.event_type || '其他')]
    }
    // char 模式:伏笔进固定伏笔道;其余进各 lane_keys 角色道
    if (it.kind === 'promise_setup' || it.kind === 'promise_payoff') return [G_PROMISE]
    return (it.lane_keys || []).filter((k) => k !== G_PROMISE)
  }

  const registerGroupsFor = (it) => {
    for (const gid of groupsFor(it)) {
      if (laneMode === 'kind') {
        const content = gid === G_EVENT ? '事件' : gid === G_ARC ? '弧光'
          : gid === G_PROMISE ? '◇伏笔' : '关系'
        const order = gid === G_EVENT ? 0 : gid === G_ARC ? 1 : gid === G_PROMISE ? 2 : 3
        ensureGroup(gid, content, order)
      } else if (laneMode === 'type') {
        ensureGroup(gid, gid.slice(3), 0)
      } else {
        if (gid === G_PROMISE) ensureGroup(gid, '◇伏笔', 9999)
        else ensureGroup(gid, stripRole(gid), charOrder.get(gid) ?? 5000)
      }
    }
  }

  // 已配对的伏笔/关系 id,避免 payoff/end 重复出条
  const pairedPromise = new Set()
  const pairedRelation = new Set()

  // ── 事件 ──
  for (const ev of rawItems.filter((i) => i.kind === 'event')) {
    registerGroupsFor(ev)
    const color = evColor(ev.event_type)
    const sc = ev.story_chapter ?? ev.chapter
    const np = ev.narrative_position
    const isFlashback = np != null && np !== sc
    const subj = (ev.refs?.subj || []).map(stripRole).join('、') || '—'
    for (const gid of groupsFor(ev)) {
      items.push({
        id: 'ev:' + ev.id + ':' + gid,
        group: gid,
        start: chToDate(ev.chapter),
        type: 'box',
        content: esc(ev.label || ev.event_type) + (isFlashback ? ' ⟲' : ''),
        title: `第${ev.chapter}章 · ${esc(ev.label || ev.event_type)}　主:${esc(subj)}`,
        style: `border-color:${color};box-shadow:inset 3px 0 0 ${color};`,
        _raw: ev, _jump: sc, _cat: 'event',
      })
    }
  }

  // ── 弧光(◆点) ──
  for (const a of rawItems.filter((i) => i.kind === 'arc')) {
    registerGroupsFor(a)
    const color = arcColor(a.refs?.change_type)
    for (const gid of groupsFor(a)) {
      items.push({
        id: 'arc:' + a.id + ':' + gid,
        group: gid,
        start: chToDate(a.chapter),
        type: 'point',
        content: '◆ ' + esc(a.refs?.arc_phase || a.label || ''),
        title: `第${a.chapter}章 弧光 · ${esc(a.refs?.arc_phase || '')}${a.label ? ' · ' + esc(a.label) : ''}`,
        style: `color:${color};border-color:${color};`,
        className: 'tl-arc',
        _raw: a, _jump: a.chapter, _cat: 'arc',
      })
    }
  }

  // ── 伏笔(setup→payoff 区间) ──
  const payoffById = new Map(promPayoffs.map((p) => [p.id, p]))
  for (const s of promSetups) {
    registerGroupsFor(s)
    pairedPromise.add(s.id)
    const payoff = payoffById.get(s.id)
    const isHerring = s.refs?.promise_kind === 'red_herring'
    const isOverdue = s.refs?.overdue && !payoff
    const color = isHerring ? PROMISE_HERRING() : PROMISE_COLOR()
    const sc = s.chapter
    const pc = payoff?.chapter ?? null
    const endChapter = pc != null ? pc : endCh
    for (const gid of groupsFor(s)) {
      items.push({
        id: 'pr:' + s.id + ':' + gid,
        group: gid,
        start: chToDate(sc),
        end: chToDate(Math.max(endChapter, sc + 0.4)),
        type: 'range',
        content: '◇ ' + esc(s.label?.length > 18 ? s.label.slice(0, 17) + '…' : s.label)
          + (isHerring ? ' (障)' : '') + (pc == null ? (isOverdue ? ' 超期未收' : ' …待收') : ''),
        title: `伏笔 ch${sc}${pc != null ? '→ch' + pc + ' 已收' : isOverdue ? ' · 超期未收' : ' · 待收'} · ${esc(s.label)}`,
        style: `background-color:${color}33;border-color:${color};color:#7c5a10;`
          + (isHerring ? 'border-style:dashed;' : '') + (isOverdue ? 'border-color:var(--color-danger);' : ''),
        _raw: { ...s, _payoff: payoff }, _jump: sc, _cat: 'promise',
      })
    }
  }

  // ── 关系(since→until 区间) ──
  const relEndByPrefix = new Map()
  for (const e of rawItems.filter((i) => i.kind === 'relation_end')) {
    relEndByPrefix.set(e.id.split('@')[0], e)
  }
  for (const r of relStarts) {
    registerGroupsFor(r)
    pairedRelation.add(r.id)
    const prefix = r.id.split('@')[0]
    const end = relEndByPrefix.get(prefix)
    const rel = r.refs?.relation || r.label
    const color = relColor(rel)
    const sc = r.chapter
    const uc = end?.chapter ?? r.refs?.until_chapter ?? null
    const endChapter = uc != null ? uc : endCh
    const srcName = r.refs?.src ? stripRole(r.refs.src) : ''
    const dstName = r.refs?.dst ? stripRole(r.refs.dst) : ''
    for (const gid of groupsFor(r)) {
      items.push({
        id: 'rel:' + r.id + ':' + gid,
        group: gid,
        start: chToDate(sc),
        end: chToDate(Math.max(endChapter, sc + 0.4)),
        type: 'range',
        content: esc(relLabel(rel)) + (srcName ? ` ${esc(srcName)}→${esc(dstName)}` : '')
          + (uc != null ? ' ✗' : ''),
        title: `关系 ${esc(relLabel(rel))} ${esc(srcName)}→${esc(dstName)} · ch${sc}${uc != null ? '→ch' + uc + ' 失效' : ' 起'}`,
        style: `background-color:${color}26;border-color:${color};border-style:dashed;color:${color};`,
        _raw: { ...r, _end: end }, _jump: sc, _cat: 'relation',
      })
    }
  }

  const groupArr = [...groups.values()].sort((a, b) => a._order - b._order)
    .map(({ id, content }) => ({ id, content }))
  return { items, groups: groupArr }
}

// 块三:时间线选中项 → 通用选中总线 focus(伏笔→promise;事件/弧光/关系→event,payload.cat 细分)。
function visItemFocus(it) {
  const raw = it._raw || {}
  const isPromise = it._cat === 'promise'
  return {
    type: isPromise ? 'promise' : 'event',
    id: String(raw.id || it.id),
    label: raw.label || raw.event_type || '',
    payload: isPromise
      ? {
          cat: it._cat,
          setup_chapter: raw.chapter,
          payoff_chapter: raw._payoff?.chapter ?? raw.refs?.payoff_chapter ?? null,
          overdue: !!(raw.refs?.overdue && !raw._payoff),
        }
      : { cat: it._cat, chapter: raw.chapter },
    origin: 'timeline',
  }
}

function timelineTarget(raw, cat) {
  const ch = raw?._jump ?? raw?.story_chapter ?? raw?.chapter
  if (cat === 'promise') {
    const id = raw?.id ? (String(raw.id).startsWith('promise:') ? raw.id : `promise:${raw.id}`) : ''
    return {
      id,
      type: 'promise',
      label: raw?.label || '伏笔',
      chapter: ch,
      ref: 'open',
    }
  }
  if (cat === 'relation') {
    return {
      id: raw?.id || '',
      type: 'relation',
      label: raw?.label || raw?.refs?.relation || '关系',
      chapter: ch,
    }
  }
  return {
    id: raw?.id || '',
    type: 'event',
    label: raw?.label || raw?.event_type || '事件',
    chapter: ch,
  }
}

// ── 详情面板 ────────────────────────────────────────────────────────────────
function Field({ k, v }) {
  if (v == null || v === '' || (Array.isArray(v) && !v.length)) return null
  const val = Array.isArray(v) ? v.map(stripRole).join('、') : String(v)
  return (
    <div className="flex gap-2 text-f12 leading-relaxed">
      <span className="shrink-0 w-16 text-faint">{k}</span>
      <span className="text-ink break-words min-w-0">{val}</span>
    </div>
  )
}

function DetailPanel({ raw, cat, onJump, onNavigate, onClose }) {
  if (!raw) return null
  const r = raw.refs || {}
  const sc = raw.story_chapter ?? raw.chapter
  const np = raw.narrative_position
  let title = '', headColor = palette().faint, body = null

  if (cat === 'event') {
    title = raw.label || raw.event_type; headColor = evColor(raw.event_type)
    body = (
      <>
        <Field k="类型" v={raw.event_type} />
        <Field k="故事章" v={sc} />
        {np != null && np !== sc && <Field k="叙事位" v={np} />}
        <Field k="主体" v={r.subj} />
        <Field k="客体" v={r.obj} />
        <Field k="见证" v={r.witness} />
        <Field k="目标" v={raw.goal} />
        <Field k="地点" v={r.location} />
        <Field k="效果" v={r.effects} />
        <Field k="因果前驱" v={(r.causal_in || []).map((c) => (typeof c === 'string' ? c : `${c.id}${c.chapter != null ? '(ch' + c.chapter + ')' : ''}`))} />
      </>
    )
  } else if (cat === 'arc') {
    title = raw.label || '弧光'; headColor = arcColor(r.change_type)
    body = (
      <>
        <Field k="章号" v={raw.chapter} />
        <Field k="质变类型" v={r.change_type} />
        <Field k="弧光阶段" v={r.arc_phase} />
        <Field k="角色" v={r.character ? stripRole(r.character) : null} />
        <Field k="影响声音" v={r.affects_voice ? '是' : null} />
        <Field k="摘要" v={raw.label} />
      </>
    )
  } else if (cat === 'promise') {
    title = raw.label || '伏笔'; headColor = r.promise_kind === 'red_herring' ? PROMISE_HERRING() : PROMISE_COLOR()
    const payoff = raw._payoff
    body = (
      <>
        <Field k="文本" v={raw.label} />
        <Field k="埋设章" v={raw.chapter} />
        <Field k="收束章" v={payoff?.chapter ?? r.payoff_chapter} />
        <Field k="状态" v={r.status} />
        <Field k="种类" v={r.promise_kind === 'red_herring' ? '障眼法' : r.promise_kind} />
        {r.overdue && !payoff && <Field k="提示" v="超期未收" />}
      </>
    )
  } else if (cat === 'relation') {
    title = relLabel(r.relation || raw.label); headColor = relColor(r.relation || raw.label)
    const end = raw._end
    body = (
      <>
        <Field k="关系" v={relLabel(r.relation || raw.label)} />
        <Field k="源" v={r.src ? stripRole(r.src) : null} />
        <Field k="目标" v={r.dst ? stripRole(r.dst) : null} />
        <Field k="建立章" v={raw.chapter} />
        <Field k="失效章" v={end?.chapter ?? r.until_chapter} />
        <Field k="备注" v={r.note} />
      </>
    )
  }

  return (
    <div className="w-64 shrink-0 border-l border-line bg-surface flex flex-col">
      <div className="flex items-center gap-2 px-3 h-10 border-b border-line">
        <span className="w-2.5 h-2.5 rounded-full shrink-0" style={{ background: headColor }} />
        <span className="text-f13 font-semibold text-ink truncate flex-1" title={title}>{title}</span>
        <button onClick={onClose} className="shrink-0 text-faint hover:text-ink cursor-pointer" title="关闭">
          <X size={14} />
        </button>
      </div>
      <div className="flex-1 min-h-0 overflow-auto px-3 py-3 flex flex-col gap-1.5">{body}</div>
      <div className="shrink-0 border-t border-line p-2">
        <button
          onClick={() => {
            if (onNavigate) onNavigate(timelineTarget(raw, cat))
            else onJump?.(raw._jump ?? raw.chapter)
          }}
          className="w-full h-8 rounded-lg bg-brand text-brandfg text-f12 font-medium cursor-pointer hover:opacity-85 flex items-center justify-center gap-1.5"
        >
          <CornerDownRight size={13} /> 跳到第{raw._jump ?? raw.chapter}章
        </button>
      </div>
    </div>
  )
}

// ── 主组件 ────────────────────────────────────────────────────────────────────
export function TimelineView({ onJumpChapter, onNavigateToObject }) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [laneMode, setLaneMode] = useState('kind')   // 'kind' | 'char' | 'type'
  const [axis, setAxis] = useState('story')            // 'story' | 'narrative'
  const [selected, setSelected] = useState(null)       // { raw, cat }

  const containerRef = useRef(null)
  const timelineRef = useRef(null)       // vis Timeline 实例
  const itemsDsRef = useRef(null)        // vis DataSet(items)
  const groupsDsRef = useRef(null)       // vis DataSet(groups)
  const onJumpRef = useRef(onJumpChapter)
  onJumpRef.current = onJumpChapter
  // 块三:选中事件/伏笔/弧光/关系 → 发通用 focus(主编聚焦);取消选中 → 清空(回退视图级话术)。
  // vis 事件处理器只注册一次,经 ref 取最新 setFocus/focus/suppressNextMirror。
  const { focus, setFocus, suppressNextMirror } = useSelection()
  const setFocusRef = useRef(setFocus)
  setFocusRef.current = setFocus
  const focusRef = useRef(focus)
  focusRef.current = focus
  const suppressRef = useRef(suppressNextMirror)
  suppressRef.current = suppressNextMirror
  // 跳章统一入口:跳前置一次性 suppress 标记——跳章引发的 sel 镜像被消费掉,
  // 保住刚选中的 event/promise 聚焦(与 InsightView 卡内跳章行为对齐)。
  const jumpKeepFocus = (ch) => { suppressRef.current(); onJumpRef.current?.(ch) }

  const load = useCallback((ax = axis) => {
    setLoading(true); setError(null)
    api.timeline(1, null, ax)
      .then((d) => { setData(d); setLoading(false) })
      .catch((e) => { setError(e.message || '加载失败'); setLoading(false) })
  }, [axis])

  useEffect(() => { load() }, [])  // eslint-disable-line react-hooks/exhaustive-deps

  const switchAxis = (ax) => { setAxis(ax); load(ax) }

  const maxCh = data?.max_chapter || 0

  const counts = useMemo(() => {
    if (!data) return { events: 0, promises: 0, arcs: 0, relations: 0 }
    const it = data.items || []
    return {
      events: it.filter((i) => i.kind === 'event').length,
      promises: it.filter((i) => i.kind === 'promise_setup').length,
      arcs: it.filter((i) => i.kind === 'arc').length,
      relations: it.filter((i) => i.kind === 'relation_start').length,
    }
  }, [data])

  const { items, groups } = useMemo(
    () => (data ? buildVis(data.items || [], laneMode, maxCh) : { items: [], groups: [] }),
    [data, laneMode, maxCh]
  )

  const hasContent = items.length > 0 && groups.length > 0

  // 键盘/读屏等价路径:与 vis 画布同一份 data.items 的命名列表(WebGL 时间线不可聚焦时的可达替代)。
  // 选列表项 = 与画布 select→详情面板跳转相同的 onNavigateToObject(timelineTarget)。
  const listItems = useMemo(() => {
    const its = data?.items || []
    const catOf = (k) => k === 'event' ? 'event' : k === 'arc' ? 'arc'
      : k === 'promise_setup' ? 'promise' : k === 'relation_start' ? 'relation' : null
    return its.map((it) => ({ raw: it, cat: catOf(it.kind) })).filter((x) => x.cat)
  }, [data])

  // #74:仅当确有「叙事位 ≠ 故事章」的事件时,「叙事顺序」轴才有意义(否则两轴投影一致=空操作)。
  // 判定与 axis 无关(每事件恒带 story_chapter/narrative_position),默认 story 轴加载即可判。
  const canNarrative = useMemo(() => hasNarrativeData(data?.items || []), [data])
  // 防御:若因外部数据变更陷在无叙事数据的 narrative 轴,回落 story(正常经禁用按钮到不了此态)。
  useEffect(() => {
    if (data && !canNarrative && axis === 'narrative') switchAxis('story')
  }, [canNarrative, data])  // eslint-disable-line react-hooks/exhaustive-deps

  // ── 初始化 / 更新 vis-timeline ────────────────────────────────────────────
  useEffect(() => {
    if (!containerRef.current || !hasContent) return

    if (!timelineRef.current) {
      // 首次创建
      itemsDsRef.current = new DataSet(items)
      groupsDsRef.current = new DataSet(groups)
      const tl = new Timeline(containerRef.current, itemsDsRef.current, groupsDsRef.current, {
        stack: true,                 // 同组自动堆叠防重叠(根治叠加)
        stackSubgroups: true,
        orientation: { axis: 'top', item: 'top' },
        zoomable: true,
        moveable: true,
        selectable: true,
        horizontalScroll: true,
        zoomKey: 'ctrlKey',          // ctrl+滚轮缩放,普通滚轮垂直滚动
        margin: { item: { horizontal: 4, vertical: 6 }, axis: 6 },
        groupHeightMode: 'auto',
        minHeight: '100%',
        maxHeight: '100%',
        zoomMin: 1000 * 60 * 60 * 24 * 2,        // 最细约 2 章
        zoomMax: 1000 * 60 * 60 * 24 * 100000,   // 最粗整书
        // 轴标签:把合成日期换算回章号显示「第N章」
        format: {
          minorLabels: (date) => '第' + dateToCh(new Date(date)) + '章',
          majorLabels: () => '',
        },
        tooltip: { followMouse: true, overflowMethod: 'cap' },
      })

      // 单击选中 → 详情面板 + 通用选中总线(主编聚焦)
      tl.on('select', (props) => {
        const id = props.items?.[0]
        if (!id) { setSelected(null); setFocusRef.current(null); return }
        const it = itemsDsRef.current.get(id)
        if (it) { setSelected({ raw: it._raw, cat: it._cat }); setFocusRef.current(visItemFocus(it)) }
      })
      // 双击 → 跳章(保聚焦:suppress 掉跳章引发的 sel 镜像)
      tl.on('doubleClick', (props) => {
        if (!props.item) return
        const it = itemsDsRef.current.get(props.item)
        if (it) jumpKeepFocus(it._jump ?? it._raw?.chapter)
      })

      timelineRef.current = tl
    } else {
      // 更新数据(laneMode / axis / 刷新)——保留实例避免重建闪烁
      itemsDsRef.current.clear()
      groupsDsRef.current.clear()
      groupsDsRef.current.add(groups)
      itemsDsRef.current.add(items)
      setSelected(null)
      // 数据重载(泳道/轴切换/刷新):旧选中失效——仅当当前 focus 确为时间线所发时才清空,
      // 不误清别处(面板/图谱等)刚设的聚焦。
      if (focusRef.current?.origin === 'timeline') setFocusRef.current(null)
    }

    // 默认窗口:大书只看最近 ~40 章(虚拟化生效);小书看全书概览
    const tl = timelineRef.current
    const hi = maxCh || 1
    const lo = Math.max(1, hi - 40)
    // 右端多留 ~1.5 章余白,末章不贴边(避免被右栏视觉挤压);左端留 0.5 章。
    tl.setWindow(chToDate(Math.max(1, lo - 0.5)), chToDate(hi + 2.5), { animation: false })
    // 容器尺寸在挂载后可能变化,强制重绘
    requestAnimationFrame(() => tl.redraw())
  }, [items, groups, hasContent, maxCh])

  // 卸载销毁
  useEffect(() => () => {
    if (timelineRef.current) { timelineRef.current.destroy(); timelineRef.current = null }
  }, [])

  // 无障碍:系统「减弱动态」时全览缩放不做动画。
  const fitAll = () => timelineRef.current?.fit({ animation: !prefersReducedMotion() })

  return (
    <div className="h-full flex flex-col bg-canvas" style={{ minHeight: 0 }}>
      {/* ── 顶栏:Upstream 胶囊切换 ── */}
      <div className="h-11 shrink-0 border-b border-line/60 bg-surface/95 backdrop-blur-sm flex items-center gap-2 px-4 overflow-x-auto">
        <Clock size={15} className="text-brand shrink-0" />
        <span className="text-f13 font-semibold tracking-tight text-ink shrink-0">时间线</span>
        {data && (
          <span className="text-meta text-faint tnum shrink-0">
            {counts.events}事件·{counts.promises}伏笔·{counts.arcs}弧光·{counts.relations}关系
            {maxCh > 0 && ` · 共${maxCh}章`}
            {data.truncated && <span className="text-warn"> · 已截断(缩小区间)</span>}
          </span>
        )}

        {/* 泳道切换 — 胶囊组 */}
        <div className="flex items-center gap-0.5 ml-1 shrink-0 rounded-xl bg-soft/80 p-0.5">
          <span className="text-meta text-faint px-1.5">泳道</span>
          {[{ v: 'kind', l: '四类' }, { v: 'char', l: '角色' }, { v: 'type', l: '事件类型' }].map(({ v, l }) => (
            <button key={v}
              onClick={() => setLaneMode(v)}
              className={`h-6 px-2 rounded-lg text-meta font-medium transition-colors cursor-pointer
                ${laneMode === v ? 'bg-surface text-brand shadow-sm' : 'text-faint hover:text-ink'}`}
            >{l}</button>
          ))}
        </div>

        {/* 故事/叙事双轴 —— #74:无「叙事位≠故事章」事件时禁用「叙事顺序」 */}
        <div className="flex items-center gap-0.5 ml-1 shrink-0 rounded-xl bg-soft/80 p-0.5">
          <span className="text-meta text-faint px-1.5">轴</span>
          {[{ v: 'story', l: '故事编年' }, { v: 'narrative', l: '叙事顺序' }].map(({ v, l }) => {
            const disabled = v === 'narrative' && !canNarrative
            return (
              <button key={v}
                onClick={() => { if (!disabled) switchAxis(v) }}
                disabled={disabled}
                title={disabled
                  ? '暂无倒叙/闪回事件(全部事件叙事位=故事章)——录入含「叙事位」的事件后可切叙事顺序轴'
                  : v === 'narrative' ? '叙事顺序:事件按被讲述的位置横铺,倒叙/闪回落到叙事位' : '故事编年:事件按实际发生章号横铺'}
                className={`h-6 px-2 rounded-lg text-meta font-medium transition-colors
                  ${disabled ? 'text-faint/40 cursor-not-allowed'
                    : axis === v ? 'bg-surface text-brand shadow-sm cursor-pointer' : 'text-faint hover:text-ink cursor-pointer'}`}
              >{l}</button>
            )
          })}
        </div>

        <button onClick={fitAll}
          className="ml-1 h-6 px-2.5 rounded-xl text-meta font-medium bg-soft/80 text-faint hover:text-ink hover:bg-soft transition-colors cursor-pointer shrink-0"
          title="缩放至全书概览(滚轮按 Ctrl 缩放,拖动平移)"
        >全览</button>

        <div className="ml-auto shrink-0">
          <button onClick={() => load()} disabled={loading}
            className="w-7 h-7 grid place-items-center rounded-xl text-faint hover:text-ink hover:bg-soft transition-colors cursor-pointer disabled:opacity-40">
            <RefreshCw size={13} className={loading ? 'animate-spin' : ''} />
          </button>
        </div>
      </div>

      {/* ── 主体 ── */}
      <div className="flex-1 min-h-0 flex">
        {listItems.length > 0 && (
          <div role="region" aria-label="时间线事件列表"
            className="w-56 shrink-0 border-r border-line bg-surface overflow-y-auto hidden md:block">
            <div className="sticky top-0 bg-surface/95 backdrop-blur px-3 py-2 border-b border-line flex items-center gap-1.5 text-meta font-medium text-faint">
              <List size={12} />事件列表 · {listItems.length}
            </div>
            <ul className="py-1">
              {listItems.map(({ raw, cat }) => {
                const ch = raw.story_chapter ?? raw.chapter
                const label = raw.label || raw.event_type || relLabel(raw.refs?.relation) || raw.id
                return (
                  <li key={`${cat}:${raw.id}`}>
                    <button onClick={() => onNavigateToObject?.(timelineTarget(raw, cat))}
                      className="w-full text-left px-3 py-1.5 text-f12 text-ink hover:bg-soft/60 flex items-center gap-1.5 transition-colors">
                      {ch != null && <span className="shrink-0 text-meta text-faint tnum">第{ch}章</span>}
                      <span className="truncate">{label}</span>
                    </button>
                  </li>
                )
              })}
            </ul>
          </div>
        )}
        <div className="flex-1 min-w-0 relative">
          {error && (
            <div className="absolute inset-0 flex items-center justify-center p-4">
              <div className="text-f13 text-red-500 bg-red-50 rounded-lg px-3 py-2 border border-red-200">{error}</div>
            </div>
          )}
          {!error && loading && !data && (
            <div className="absolute inset-0 flex items-center justify-center text-f12 text-faint gap-2">
              <RefreshCw size={14} className="animate-spin" />加载时间线…
            </div>
          )}
          {!error && data && !hasContent && (
            <div className="absolute inset-0 flex items-center justify-center text-f13 text-faint">
              <div className="text-center">
                <Clock size={32} className="mx-auto mb-2 opacity-30" />
                <div>暂无时间线数据</div>
                <div className="text-meta mt-1 opacity-60">先在写作台录入章节事件</div>
              </div>
            </div>
          )}
          {/* vis-timeline 挂载容器(始终在 DOM,有内容才可见) */}
          <div
            ref={containerRef}
            className="tl-vis absolute inset-0"
            style={{ visibility: hasContent ? 'visible' : 'hidden' }}
          />
        </div>

        {/* 详情面板 */}
        {selected && (
          <DetailPanel
            raw={selected.raw}
            cat={selected.cat}
            onJump={jumpKeepFocus}
            onNavigate={onNavigateToObject}
            onClose={() => { setSelected(null); if (focus?.origin === 'timeline') setFocus(null); timelineRef.current?.setSelection([]) }}
          />
        )}
      </div>

      {/* 图例 + 操作提示 */}
      {hasContent && (
        <div className="shrink-0 flex items-center gap-3 px-4 py-1.5 border-t border-line bg-surface/50 overflow-x-auto text-meta text-faint">
          <span className="shrink-0 font-medium">图例:</span>
          <span className="shrink-0 inline-flex items-center gap-1">
            <i className="inline-block w-3 h-3 rounded border border-line bg-surface" style={{ boxShadow: `inset 3px 0 0 ${palette().secret}` }} />事件
          </span>
          <span className="shrink-0 inline-flex items-center gap-1">
            <i className="inline-block w-2.5 h-2.5 bg-purple-600" style={{ transform: 'rotate(45deg)' }} />弧光◆
          </span>
          <span className="shrink-0 inline-flex items-center gap-1">
            <i className="inline-block w-3 h-2 rounded bg-amber-400/25 border border-amber-400" />伏笔条◇
          </span>
          <span className="shrink-0 inline-flex items-center gap-1">
            <i className="inline-block w-3 h-2 rounded border border-dashed border-sky-500" />关系条
          </span>
          <span className="shrink-0 text-red-500 inline-flex items-center gap-1"><AlertTriangle size={11} />超期未收</span>
          <span className="shrink-0">✗ 失效</span>
          <span className="shrink-0 ml-auto opacity-70">单击看详情 · 双击跳章 · Ctrl+滚轮缩放 · 拖动平移</span>
        </div>
      )}

      {/* vis-timeline 主题微调(贴 tailwind/CSS 变量) */}
      <style>{`
        .tl-vis .vis-timeline { border: none; font-family: inherit; }
        .tl-vis .vis-panel.vis-left,
        .tl-vis .vis-panel.vis-center,
        .tl-vis .vis-panel.vis-top,
        .tl-vis .vis-panel.vis-bottom { border-color: var(--color-line); }
        .tl-vis .vis-labelset .vis-label,
        .tl-vis .vis-foreground .vis-group { border-color: var(--color-line); }
        .tl-vis .vis-labelset .vis-label { color: var(--color-faint); font-size: 11px; }
        .tl-vis .vis-labelset .vis-label .vis-inner { padding: 4px 8px; font-weight: 500; }
        .tl-vis .vis-time-axis .vis-text { color: var(--color-faint); font-size: 10px; }
        .tl-vis .vis-time-axis .vis-grid.vis-minor { border-color: color-mix(in srgb, var(--color-line) 60%, transparent); }
        .tl-vis .vis-item {
          border-radius: 6px; border-width: 1px;
          background-color: var(--color-surface); color: var(--color-ink);
          font-size: 11px;
        }
        .tl-vis .vis-item.vis-selected {
          box-shadow: 0 0 0 2px var(--color-brand); z-index: 5;
        }
        .tl-vis .vis-item.vis-box { padding: 2px 6px; }
        .tl-vis .vis-item.vis-dot { border-width: 5px; }
        .tl-vis .vis-item.tl-arc.vis-point .vis-item-content { font-weight: 600; }
        .tl-vis .vis-item .vis-item-content { padding: 1px 2px; white-space: nowrap; }
        .tl-vis .vis-current-time { background-color: var(--color-brand); }
        .tl-vis .vis-tooltip {
          background: var(--color-surface); color: var(--color-ink);
          border: 1px solid var(--color-line); border-radius: 6px;
          padding: 4px 8px; font-size: 11px; box-shadow: 0 2px 8px rgba(0,0,0,.12);
        }
      `}</style>
    </div>
  )
}
