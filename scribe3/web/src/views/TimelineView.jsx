/**
 * TimelineView · 作者工具 F-02 完整期 · 多泳道时间线 + SVG 因果弧线
 *
 * 横轴=章号,纵向多泳道:事件 / 伏笔(setup→payoff 横条) / 弧光(◆点) / 关系(since→until 甘特条)
 * 泳道切换:按角色 / 按情节线(promise) / 按事件类型
 * 完整期新增:SVG 因果弧线叠层——事件卡间的 causal_in 弧线(event→event, 跨泳道/跨章)
 *   - 坐标用确定值:x = (chapter - chFrom) * COL_W + COL_W/2, y = laneIndex * LANE_H + LANE_H/2
 *   - 贝塞尔弧线 + 箭头 marker,可开关(默认关,密集时避免乱)
 *
 * spec: docs/系统文档/作者工具/02-时间线视图.md §完整
 * 关键:关系全史用 _all_relations()(后端无时间门),不漏已失效历史关系。
 */
import { useEffect, useRef, useState, useMemo, useCallback } from 'react'
import { Clock, RefreshCw, GitFork } from 'lucide-react'
import { api } from '../api'
import { relColor, relLabel } from '../lib/relColors'

// ── 布局常量 ──────────────────────────────────────────────────────────────────
const COL_W    = 150  // 每章列宽(px)
const LANE_H   = 90   // 每条泳道高度(px)
const LABEL_W  = 80   // 左侧泳道标签宽(px)
const HEADER_H = 28   // 章号表头高度(px)
const CARD_W   = 110  // 事件卡宽
const CARD_H   = 66   // 事件卡高
const BAR_H    = 14   // 甘特条高度

// ── 配色 ─────────────────────────────────────────────────────────────────────
const EVENT_TYPE_COLOR = {
  '炼器': '#7c3aed', '战斗': '#dc2626', '拜师': '#0ea5e9',
  '对话': '#16a34a', '决策': '#d97706', '失去': '#be185d', '获得': '#15803d',
}
const evColor  = (t) => EVENT_TYPE_COLOR[t] || '#64748b'

const ARC_COLORS = {
  ability: '#7c3aed', relation: '#0ea5e9', personality: '#ec4899', composite: '#f97316',
}
const arcColor = (ct) => ARC_COLORS[ct] || '#64748b'

const PROMISE_COLOR   = '#f59e0b'
const PROMISE_HERRING = '#94a3b8'
const CAUSAL_COLOR    = '#6366f1'  // 因果弧线:靛紫色,与事件卡不冲突

// ── 工具函数 ──────────────────────────────────────────────────────────────────
const stripRole = (id) => (id || '').replace(/^role:/, '')

/** 从 items 推导泳道 key 列表(有序) */
function deriveLaneKeys(items, laneMode) {
  if (laneMode === 'promise') return ['__promise__']
  if (laneMode === 'type') {
    const types = [...new Set(
      items.filter((i) => i.kind === 'event').map((i) => i.event_type || '其他')
    )].sort()
    return types.length ? types : ['其他']
  }
  // char 模式:角色泳道 + 固定伏笔道
  const chars = new Set()
  const hasPromise = items.some((i) => i.lane_keys?.includes('__promise__'))
  for (const item of items) {
    for (const lk of item.lane_keys || []) {
      if (lk !== '__promise__') chars.add(lk)
    }
  }
  const sorted = [...chars].sort()
  return hasPromise ? [...sorted, '__promise__'] : sorted
}

/** Separated 语义:一 item 可落到多泳道 */
function buildLanes(items, laneMode, allLaneKeys) {
  const map = {}
  for (const lk of allLaneKeys) map[lk] = []
  for (const item of items) {
    const keys = item.lane_keys || []
    let relevant
    if (laneMode === 'char') relevant = keys  // 含 __promise__
    else if (laneMode === 'promise') relevant = keys.filter((k) => k === '__promise__')
    else relevant = keys.slice(0, 1)  // type 模式:第一个 key
    for (const lk of relevant) {
      if (map[lk] !== undefined) map[lk].push(item)
    }
  }
  return map
}

// ── 子组件 ────────────────────────────────────────────────────────────────────

/**
 * CausalArrowLayer · 跨泳道 SVG 因果弧线叠层(完整期)
 *
 * 绝对定位在整个网格内容区(HEADER_H 以下),覆盖 allLaneKeys.length * LANE_H 高度。
 * 坐标计算(确定值,不依赖 DOM):
 *   x = (event.chapter - chFrom) * COL_W + COL_W/2  → 列中心
 *   y = laneIndex * LANE_H + LANE_H/2                → 泳道中心
 * 弧线方向:因(cause)→果(effect),箭头指向果事件。
 * 悬浮高亮:hover 某条弧线时高亮该弧线及两端事件 id。
 *
 * props:
 *   items         - timeline items 完整列表(仅用 kind=event)
 *   allLaneKeys   - 当前模式的泳道 key 顺序
 *   chFrom        - 显示区间起章
 *   totalCols     - 列数(chRange.length)
 *   hiddenLanes   - Set<laneKey> 隐藏的泳道(隐藏泳道里的弧线也不画)
 *   laneMode      - 'char'|'promise'|'type'(非 char 模式下泳道切换会变,y 随之变)
 */
function CausalArrowLayer({ items, allLaneKeys, chFrom, totalCols, hiddenLanes, laneMode }) {
  const [hoveredId, setHoveredId] = useState(null)

  // 建立 event id → (chapter, laneIndex) 的查找表
  // 一个事件可在多条泳道,取第一个可见泳道的 index 作为 y 基准
  const evPos = useMemo(() => {
    const map = {}
    for (const item of items) {
      if (item.kind !== 'event') continue
      const ch = item.chapter
      const x = (ch - chFrom) * COL_W + COL_W / 2
      // 找第一个可见 lane
      let laneIdx = -1
      for (const lk of (item.lane_keys || [])) {
        const idx = allLaneKeys.indexOf(lk)
        if (idx !== -1 && !hiddenLanes.has(lk)) { laneIdx = idx; break }
      }
      if (laneIdx === -1) continue  // 无可见泳道,跳过
      const y = laneIdx * LANE_H + LANE_H / 2
      map[item.id] = { x, y, chapter: ch }
    }
    return map
  }, [items, allLaneKeys, chFrom, hiddenLanes])

  // 收集所有因果弧线:果事件 → 因事件
  const arcs = useMemo(() => {
    const result = []
    for (const item of items) {
      if (item.kind !== 'event') continue
      const causalIn = item.refs?.causal_in || []
      if (!causalIn.length) continue
      const effectPos = evPos[item.id]
      if (!effectPos) continue

      for (const ci of causalIn) {
        // ci 格式:{id, chapter} (完整期后端补全)
        // 兼容旧格式(字符串):若 ci 是字符串,转为 {id: ci, chapter: null}
        const causeId = typeof ci === 'string' ? ci : ci.id
        const causeChapter = typeof ci === 'string' ? null : ci.chapter
        if (!causeId) continue

        // 如果前驱事件在 evPos 里(在当前显示区间内),直接用其坐标
        // 否则用 causeChapter(可能在区间外,仍可算 x,但无 y → 画到边界)
        const causePos = evPos[causeId]
        if (!causePos && causeChapter == null) continue  // 完全无坐标信息

        const cx = causePos ? causePos.x : (causeChapter - chFrom) * COL_W + COL_W / 2
        const cy = causePos ? causePos.y : effectPos.y  // 无泳道信息时与果事件同行
        const ex = effectPos.x
        const ey = effectPos.y

        result.push({
          id: `${causeId}→${item.id}`,
          cx, cy, ex, ey,
          causeId, effectId: item.id,
          label: item.label || item.event_type || '',
        })
      }
    }
    return result
  }, [items, evPos, chFrom])

  if (!arcs.length) return null

  const svgW = totalCols * COL_W
  const svgH = allLaneKeys.length * LANE_H
  const markerId = 'causal-arrow-head'
  const markerIdHover = 'causal-arrow-head-hover'

  return (
    <svg
      style={{
        position: 'absolute',
        top: 0,
        left: 0,
        width: svgW,
        height: svgH,
        pointerEvents: 'all',  // 覆盖父 div 的 none,让 hover 事件能传到 <g>
        zIndex: 20,
        overflow: 'visible',
      }}
    >
      <defs>
        {/* 普通箭头 marker */}
        <marker id={markerId} markerWidth={8} markerHeight={8}
          refX={7} refY={3} orient="auto" markerUnits="strokeWidth">
          <path d="M0,0 L0,6 L8,3 z" fill={CAUSAL_COLOR} opacity={0.65} />
        </marker>
        {/* 高亮箭头 marker */}
        <marker id={markerIdHover} markerWidth={8} markerHeight={8}
          refX={7} refY={3} orient="auto" markerUnits="strokeWidth">
          <path d="M0,0 L0,6 L8,3 z" fill={CAUSAL_COLOR} opacity={1} />
        </marker>
      </defs>

      {arcs.map((arc) => {
        const isHovered = hoveredId === arc.id
        // 贝塞尔控制点:在两点中间,垂直偏上(避免遮挡卡片)
        // 若同一泳道(cy≈ey):弧线向上凸;跨泳道:用 S 曲线
        const midX = (arc.cx + arc.ex) / 2
        const dy = arc.ey - arc.cy
        // 弓高:同行至少 30px,跨行等比例增加,但不超过 LANE_H/2
        const bow = Math.min(Math.abs(dy) / 2 + 30, LANE_H * 0.6)
        // 控制点在上方(y 减小=向上)
        const cpY = Math.min(arc.cy, arc.ey) - bow
        // 路径:从 cause(cx,cy) 经控制点 到 effect(ex,ey)
        const d = `M ${arc.cx} ${arc.cy} Q ${midX} ${cpY} ${arc.ex} ${arc.ey}`

        return (
          <g key={arc.id}
            onMouseEnter={() => setHoveredId(arc.id)}
            onMouseLeave={() => setHoveredId(null)}
            style={{ pointerEvents: 'stroke', cursor: 'default' }}
          >
            {/* 透明宽带方便 hover */}
            <path d={d} fill="none" stroke="transparent" strokeWidth={12} />
            {/* 实际弧线 */}
            <path
              d={d}
              fill="none"
              stroke={CAUSAL_COLOR}
              strokeWidth={isHovered ? 2 : 1.2}
              strokeDasharray={isHovered ? undefined : '6 3'}
              opacity={isHovered ? 1 : 0.55}
              markerEnd={`url(#${isHovered ? markerIdHover : markerId})`}
            />
            {/* hover 时显示标签 */}
            {isHovered && (
              <text
                x={midX}
                y={cpY - 4}
                textAnchor="middle"
                fontSize={9}
                fill={CAUSAL_COLOR}
                style={{ pointerEvents: 'none', userSelect: 'none' }}
              >
                {arc.label}
              </text>
            )}
          </g>
        )
      })}
    </svg>
  )
}

/**
 * NarrativeEditor · 叙事位内联编辑小控件(尾1)
 * 点击闪回角标或"叙@N"字样弹出数字框;支持清除(空值→ null,回退 story_chapter)。
 */
function NarrativeEditor({ eventId, storyChapter, currentNp, onDone }) {
  const [val, setVal] = useState(currentNp != null ? String(currentNp) : '')
  const [saving, setSaving] = useState(false)

  const commit = useCallback((e) => {
    e && e.stopPropagation()
    const parsed = val.trim() === '' ? null : parseInt(val, 10)
    if (val.trim() !== '' && isNaN(parsed)) return   // 非法数字,忽略
    setSaving(true)
    api.patchEventNarrative(eventId, parsed)
      .then(() => onDone(parsed))
      .catch(() => { setSaving(false) })
  }, [val, eventId, onDone])

  const onKeyDown = (e) => {
    if (e.key === 'Enter') { e.preventDefault(); commit() }
    if (e.key === 'Escape') { e.preventDefault(); onDone(currentNp) }
  }

  return (
    <div
      onClick={(e) => e.stopPropagation()}
      className="absolute inset-0 z-30 flex items-center justify-center bg-surface/90 rounded-lg"
    >
      <div className="flex flex-col gap-1 px-2 w-full">
        <span className="text-[9px] text-faint">叙事位(空=清除,回退故事章{storyChapter})</span>
        <div className="flex items-center gap-1">
          <input
            autoFocus
            type="number"
            value={val}
            onChange={(e) => setVal(e.target.value)}
            onKeyDown={onKeyDown}
            placeholder={String(storyChapter)}
            className="w-14 h-5 rounded border border-brand bg-canvas text-center text-[11px] text-ink outline-none"
            disabled={saving}
          />
          <button
            onClick={commit}
            disabled={saving}
            className="h-5 px-1.5 rounded bg-brand text-brandfg text-[10px] font-medium cursor-pointer disabled:opacity-50"
          >{saving ? '…' : '确认'}</button>
          <button
            onClick={(e) => { e.stopPropagation(); onDone(currentNp) }}
            className="h-5 px-1 rounded text-faint text-[10px] hover:text-ink cursor-pointer"
          >✕</button>
        </div>
      </div>
    </div>
  )
}

function EventCard({ item, onJumpChapter, stacked, onTimelineRefresh }) {
  const color = evColor(item.event_type)
  const subj  = (item.refs?.subj || []).map(stripRole).join('、') || '—'
  const wit   = (item.refs?.witness || []).map(stripRole).join('、')
  // 双轴(完整期):story_chapter / narrative_position 不同 → 闪回/倒叙事件
  const sc = item.story_chapter ?? item.chapter
  const np = item.narrative_position
  const isFlashback = np != null && np !== sc
  // 点事件卡始终跳故事章正文(chapter.seq = story_chapter)
  const jumpCh = sc

  // 叙事位内联编辑状态
  const [editingNp, setEditingNp] = useState(false)

  const handleNpDone = useCallback((newNp) => {
    setEditingNp(false)
    // 批了写后刷新时间线(newNp 变化才重拉)
    if (newNp !== np) {
      onTimelineRefresh?.()
    }
  }, [np, onTimelineRefresh])

  return (
    <div
      onClick={() => !editingNp && onJumpChapter?.(jumpCh)}
      title={isFlashback
        ? `闪回 · 故事@${sc}章 / 叙事@${np} · ${item.label}${item.goal ? ' · ' + item.goal : ''}`
        : `第${sc}章 · ${item.label}${item.goal ? ' · ' + item.goal : ''}`}
      style={{
        position: 'absolute',
        left: stacked * 5,
        top: (LANE_H - CARD_H) / 2 + stacked * 3,
        width: CARD_W,
        height: CARD_H,
        borderLeft: `3px solid ${color}`,
        zIndex: 10 - stacked,
      }}
      className="rounded-lg bg-surface border border-line shadow-sm px-2 py-1 flex flex-col gap-0.5 hover:shadow-md hover:border-brand/60 transition-shadow cursor-pointer select-none"
    >
      {/* 叙事位内联编辑浮层 */}
      {editingNp && (
        <NarrativeEditor
          eventId={item.id}
          storyChapter={sc}
          currentNp={np}
          onDone={handleNpDone}
        />
      )}

      <div className="flex items-center gap-1 min-w-0">
        <span className="shrink-0 w-2 h-2 rounded-full inline-block" style={{ background: color }} />
        <span className="text-[11px] font-semibold text-ink truncate">{item.label || item.event_type}</span>
        {isFlashback && (
          <span
            className="shrink-0 text-[8px] font-medium px-1 rounded bg-indigo-100 text-indigo-600 leading-tight cursor-pointer hover:bg-indigo-200"
            title={`故事@${sc} / 叙事@${np} · 点击编辑叙事位`}
            onClick={(e) => { e.stopPropagation(); setEditingNp(true) }}
          >闪回</span>
        )}
        <span
          className="ml-auto text-[10px] text-faint shrink-0 cursor-pointer hover:text-brand"
          title="点击编辑叙事位(narrative_position)"
          onClick={(e) => { e.stopPropagation(); setEditingNp(true) }}
        >
          {isFlashback ? `故@${sc}/叙@${np}` : `ch${sc}`}
        </span>
      </div>
      {item.goal && <div className="text-[10px] text-faint truncate">{item.goal}</div>}
      <div className="text-[10px] text-faint/80 truncate">
        主:{subj}{wit ? <span className="opacity-60"> 见:{wit}</span> : null}
      </div>
      {(item.refs?.causal_in || []).length > 0 && (
        <div className="text-[9px] text-faint/60 truncate">⤴ {item.refs.causal_in.join('、')}</div>
      )}
    </div>
  )
}

/** 伏笔 setup→payoff 横条(SVG) */
function PromiseBar({ setupItem, payoffItem, chFrom, totalCols, onJumpChapter }) {
  const isHerring = setupItem.refs?.promise_kind === 'red_herring'
  const isOverdue  = setupItem.refs?.overdue && !payoffItem
  const color = isHerring ? PROMISE_HERRING : PROMISE_COLOR
  const sc = setupItem.chapter
  const pc = payoffItem?.chapter ?? null
  const barY = LANE_H / 2 - BAR_H / 2
  const startX = (sc - chFrom) * COL_W + COL_W / 2
  const endX   = pc != null ? (pc - chFrom) * COL_W + COL_W / 2 : totalCols * COL_W - 8
  const barW   = Math.max(endX - startX, 4)

  return (
    <g>
      <rect x={startX} y={barY} width={barW} height={BAR_H} rx={3}
        fill={color} fillOpacity={isHerring ? 0.3 : 0.22}
        stroke={color} strokeWidth={1.5}
        strokeDasharray={isHerring ? '4 3' : undefined}
        style={{ cursor: 'pointer' }} onClick={() => onJumpChapter?.(sc)}
      />
      {/* setup 菱形 ◇ */}
      <rect x={startX - 5} y={barY + BAR_H / 2 - 5} width={10} height={10}
        rx={1} transform={`rotate(45,${startX},${barY + BAR_H / 2})`}
        fill={color} stroke="#fff" strokeWidth={1}
        style={{ cursor: 'pointer' }} onClick={() => onJumpChapter?.(sc)}
      ><title>{`ch${sc} 埋:${setupItem.label}`}</title></rect>
      {/* payoff 圆 ● */}
      {pc != null ? (
        <circle cx={endX} cy={barY + BAR_H / 2} r={5}
          fill={color} stroke="#fff" strokeWidth={1}
          style={{ cursor: 'pointer' }} onClick={() => onJumpChapter?.(pc)}
        ><title>{`ch${pc} 收:${setupItem.label}`}</title></circle>
      ) : (
        <>
          <polygon
            points={`${endX},${barY + 2} ${endX + 7},${barY + BAR_H / 2} ${endX},${barY + BAR_H - 2}`}
            fill={isOverdue ? '#ef4444' : color} fillOpacity={0.7}
          />
          {isOverdue && (
            <text x={endX + 9} y={barY + BAR_H - 1} fontSize={10} fill="#ef4444" fontWeight="bold">⚠</text>
          )}
        </>
      )}
      <text x={startX + 8} y={barY + BAR_H - 3} fontSize={9}
        fill={isHerring ? '#94a3b8' : '#92400e'}
        style={{ pointerEvents: 'none', userSelect: 'none' }}
      >
        {setupItem.label.length > 14 ? setupItem.label.slice(0, 13) + '…' : setupItem.label}
        {isHerring ? ' (障)' : ''}
      </text>
    </g>
  )
}

/** 关系 since→until 甘特条(SVG) */
function RelationBar({ startItem, endItem, chFrom, totalCols, onJumpChapter }) {
  const rel    = startItem.refs?.relation || startItem.label
  const color  = relColor(rel)
  const sc     = startItem.chapter
  const uc     = endItem?.chapter ?? null
  const barY   = LANE_H / 2 - BAR_H / 2
  const startX = (sc - chFrom) * COL_W + COL_W / 2
  const endX   = uc != null ? (uc - chFrom) * COL_W + COL_W / 2 : totalCols * COL_W - 8
  const barW   = Math.max(endX - startX, 4)
  const srcName = startItem.refs?.src ? stripRole(startItem.refs.src) : ''
  const dstName = startItem.refs?.dst ? stripRole(startItem.refs.dst) : ''

  return (
    <g>
      <rect x={startX} y={barY} width={barW} height={BAR_H} rx={3}
        fill={color} fillOpacity={0.16}
        stroke={color} strokeWidth={1.5} strokeDasharray="5 3"
        style={{ cursor: 'pointer' }} onClick={() => onJumpChapter?.(sc)}
      />
      {/* 建立点 ● */}
      <circle cx={startX} cy={barY + BAR_H / 2} r={4}
        fill={color} stroke="#fff" strokeWidth={1}
        style={{ cursor: 'pointer' }} onClick={() => onJumpChapter?.(sc)}
      ><title>{`ch${sc} 建立: ${relLabel(rel)}  ${srcName}→${dstName}`}</title></circle>
      {/* 失效点 ✗ */}
      {uc != null && (
        <>
          <line x1={endX - 4} y1={barY + 2} x2={endX + 4} y2={barY + BAR_H - 2} stroke={color} strokeWidth={2} />
          <line x1={endX + 4} y1={barY + 2} x2={endX - 4} y2={barY + BAR_H - 2} stroke={color} strokeWidth={2} />
        </>
      )}
      <text x={startX + 8} y={barY + BAR_H - 3} fontSize={9} fill={color}
        style={{ pointerEvents: 'none', userSelect: 'none' }}
      >
        {relLabel(rel)}{srcName ? ` ${srcName}→${dstName}` : ''}
      </text>
    </g>
  )
}

/** 单条泳道内容 */
function LaneRow({ laneKey, items, chFrom, chRange, onJumpChapter, laneMode, onTimelineRefresh }) {
  const totalCols = chRange.length
  const svgW = totalCols * COL_W

  const eventItems  = items.filter((i) => i.kind === 'event')
  const arcItems    = items.filter((i) => i.kind === 'arc')
  const promSetups  = items.filter((i) => i.kind === 'promise_setup')
  const promPayoffs = items.filter((i) => i.kind === 'promise_payoff')
  const relStarts   = items.filter((i) => i.kind === 'relation_start')
  const relEnds     = items.filter((i) => i.kind === 'relation_end')

  // 配对伏笔(同 id)
  const promPairs = promSetups.map((s) => ({
    setup: s, payoff: promPayoffs.find((p) => p.id === s.id) || null,
  }))

  // 配对关系(id prefix 同 "src->dst")
  const relPairs = relStarts.map((s) => {
    const prefix = s.id.split('@')[0]
    return { start: s, end: relEnds.find((e) => e.id.startsWith(prefix)) || null }
  })

  // 按章分组事件(同章堆叠)
  const evByChapter = {}
  for (const ev of eventItems) {
    if (!evByChapter[ev.chapter]) evByChapter[ev.chapter] = []
    evByChapter[ev.chapter].push(ev)
  }

  return (
    <div style={{ position: 'relative', width: svgW, height: LANE_H }}>
      {/* 轴线 */}
      <div style={{
        position: 'absolute', top: LANE_H / 2, left: 0, right: 0,
        height: 1, background: 'var(--color-line)', opacity: 0.35,
      }} />

      {/* SVG 叠层 */}
      <svg style={{ position: 'absolute', top: 0, left: 0, width: svgW, height: LANE_H, overflow: 'visible' }}
        pointerEvents="none"
      >
        {/* 伏笔横条(只在伏笔泳道显示) */}
        {laneKey === '__promise__' && promPairs.map(({ setup, payoff }) => (
          <PromiseBar key={setup.id} setupItem={setup} payoffItem={payoff}
            chFrom={chFrom} totalCols={totalCols} onJumpChapter={onJumpChapter} />
        ))}
        {/* 关系甘特条(角色泳道 + char 模式) */}
        {laneKey !== '__promise__' && laneMode === 'char' && relPairs.map(({ start, end }) => (
          <RelationBar key={start.id} startItem={start} endItem={end}
            chFrom={chFrom} totalCols={totalCols} onJumpChapter={onJumpChapter} />
        ))}
        {/* 弧光◆点 */}
        {arcItems.map((item) => {
          const color = arcColor(item.refs?.change_type)
          const cx = (item.chapter - chFrom) * COL_W + COL_W / 2
          const cy = LANE_H / 2
          return (
            <g key={item.id} style={{ cursor: 'pointer' }} onClick={() => onJumpChapter?.(item.chapter)}>
              <rect x={cx - 6} y={cy - 6} width={12} height={12} rx={1}
                transform={`rotate(45,${cx},${cy})`}
                fill={color} stroke="#fff" strokeWidth={1.5}
              ><title>{`ch${item.chapter} ${item.refs?.arc_phase || ''} · ${item.label}`}</title></rect>
              <text x={cx + 9} y={cy + 4} fontSize={9} fill={color}
                style={{ pointerEvents: 'none', userSelect: 'none' }}>
                {item.refs?.arc_phase || ''}
              </text>
            </g>
          )
        })}
      </svg>

      {/* 事件卡(绝对定位) */}
      {Object.entries(evByChapter).map(([ch, evs]) =>
        evs.map((ev, idx) => (
          <div key={ev.id + '_' + laneKey + '_' + idx}
            style={{
              position: 'absolute',
              left: (parseInt(ch) - chFrom) * COL_W + (COL_W - CARD_W) / 2 + idx * 5,
              top: 0,
            }}
          >
            <EventCard item={ev} onJumpChapter={onJumpChapter} stacked={idx}
              onTimelineRefresh={onTimelineRefresh} />
          </div>
        ))
      )}
    </div>
  )
}

// ── 主组件 ────────────────────────────────────────────────────────────────────
export function TimelineView({ onJumpChapter }) {
  const [data, setData]       = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError]     = useState(null)
  const [chFrom, setChFrom]   = useState(1)
  const [chTo, setChTo]       = useState(null)
  const [laneMode, setLaneMode] = useState('char')  // 'char' | 'promise' | 'type'
  const [axis, setAxis] = useState('story')          // 'story'(故事编年) | 'narrative'(叙事顺序)
  const [hiddenLanes, setHiddenLanes] = useState(new Set())
  const [showCausal, setShowCausal] = useState(false)  // 因果弧线开关(默认关,密集时避免乱)
  const containerRef = useRef(null)

  const load = (from, to, ax = axis) => {
    setLoading(true); setError(null)
    api.timeline(from, to, ax)
      .then((d) => { setData(d); setLoading(false) })
      .catch((e) => { setError(e.message || '加载失败'); setLoading(false) })
  }

  useEffect(() => { load(chFrom, chTo) }, [])

  const apply = () => load(chFrom, chTo)

  // 切换故事/叙事轴:立即重拉(事件 x 坐标随轴重排)
  const switchAxis = (ax) => { setAxis(ax); load(chFrom, chTo, ax) }

  const maxCh = data?.max_chapter || 0

  const chRange = useMemo(() => {
    if (!data) return []
    const lo = data.from || 1
    const hi = data.to || maxCh
    return lo <= hi ? Array.from({ length: hi - lo + 1 }, (_, i) => lo + i) : []
  }, [data])

  const allLaneKeys = useMemo(() => {
    if (!data) return []
    return deriveLaneKeys(data.items || [], laneMode)
  }, [data, laneMode])

  const laneMap = useMemo(() => {
    if (!data) return {}
    return buildLanes(data.items || [], laneMode, allLaneKeys)
  }, [data, laneMode, allLaneKeys])

  const counts = useMemo(() => {
    if (!data) return { events: 0, promises: 0, arcs: 0, relations: 0 }
    const it = data.items || []
    return {
      events:    it.filter((i) => i.kind === 'event').length,
      promises:  it.filter((i) => i.kind === 'promise_setup').length,
      arcs:      it.filter((i) => i.kind === 'arc').length,
      relations: it.filter((i) => i.kind === 'relation_start').length,
    }
  }, [data])

  const toggleLane = (lk) => setHiddenLanes((prev) => {
    const next = new Set(prev)
    if (next.has(lk)) next.delete(lk); else next.add(lk)
    return next
  })

  const hasContent = chRange.length > 0 && allLaneKeys.length > 0

  return (
    <div className="h-full flex flex-col bg-canvas" style={{ minHeight: 0 }}>

      {/* ── 顶栏 ──────────────────────────────────────────────────────── */}
      <div className="h-11 shrink-0 border-b border-line bg-surface flex items-center gap-2 px-4 overflow-x-auto">
        <Clock size={15} className="text-brand shrink-0" />
        <span className="text-[13px] font-medium text-ink shrink-0">时间线</span>

        {data && (
          <span className="text-[11px] text-faint tnum shrink-0">
            {counts.events}事件·{counts.promises}伏笔·{counts.arcs}弧光·{counts.relations}关系
            {maxCh > 0 && ` · 共${maxCh}章`}
          </span>
        )}

        {/* 泳道切换 */}
        <div className="flex items-center gap-1 ml-2 shrink-0">
          <span className="text-[11px] text-faint">泳道:</span>
          {[{ v: 'char', l: '角色' }, { v: 'promise', l: '伏笔线' }, { v: 'type', l: '类型' }].map(({ v, l }) => (
            <button key={v}
              onClick={() => { setLaneMode(v); setHiddenLanes(new Set()) }}
              className={`h-6 px-2 rounded text-[11px] font-medium transition-colors cursor-pointer
                ${laneMode === v ? 'bg-brand text-brandfg' : 'bg-soft text-faint hover:text-ink'}`}
            >{l}</button>
          ))}
        </div>

        {/* 故事/叙事双轴切换(完整期 spec §3.1):narrative 时事件按 narrative_position 重排 */}
        <div className="flex items-center gap-1 ml-2 shrink-0">
          <span className="text-[11px] text-faint">轴:</span>
          {[{ v: 'story', l: '故事编年' }, { v: 'narrative', l: '叙事顺序' }].map(({ v, l }) => (
            <button key={v}
              onClick={() => switchAxis(v)}
              title={v === 'narrative'
                ? '叙事顺序:事件按被讲述的位置横铺,倒叙/闪回落到叙事位'
                : '故事编年:事件按实际发生章号横铺'}
              className={`h-6 px-2 rounded text-[11px] font-medium transition-colors cursor-pointer
                ${axis === v ? 'bg-indigo-500 text-white' : 'bg-soft text-faint hover:text-ink'}`}
            >{l}</button>
          ))}
        </div>

        {/* 章号范围 */}
        <div className="flex items-center gap-1 ml-2 shrink-0">
          <span className="text-[11px] text-faint">第</span>
          <input type="number" min={1} max={maxCh || 999} value={chFrom}
            onChange={(e) => setChFrom(Math.max(1, Number(e.target.value)))}
            className="w-11 h-6 rounded border border-line bg-canvas text-center text-[12px] text-ink outline-none focus:border-brand"
          />
          <span className="text-[11px] text-faint">—</span>
          <input type="number" min={chFrom} max={maxCh || 999}
            placeholder={maxCh ? String(maxCh) : '末'} value={chTo ?? ''}
            onChange={(e) => setChTo(e.target.value === '' ? null : Math.max(chFrom, Number(e.target.value)))}
            className="w-11 h-6 rounded border border-line bg-canvas text-center text-[12px] text-ink outline-none focus:border-brand"
          />
          <span className="text-[11px] text-faint">章</span>
          <button onClick={apply}
            className="h-6 px-2 rounded bg-brand text-brandfg text-[11px] font-medium cursor-pointer hover:opacity-80"
          >应用</button>
        </div>

        {/* 因果弧线开关 */}
        <button
          onClick={() => setShowCausal((v) => !v)}
          title={showCausal ? '关闭因果弧线' : '显示事件因果弧线(causal_in)'}
          className={`ml-2 h-6 px-2 rounded text-[11px] font-medium transition-colors cursor-pointer shrink-0 flex items-center gap-1
            ${showCausal ? 'bg-indigo-500 text-white' : 'bg-soft text-faint hover:text-ink'}`}
        >
          <GitFork size={11} />
          因果线
        </button>

        <div className="ml-auto shrink-0">
          <button onClick={() => load(chFrom, chTo)} disabled={loading}
            className="w-7 h-7 grid place-items-center rounded-lg text-faint hover:text-ink hover:bg-soft transition-colors cursor-pointer disabled:opacity-40">
            <RefreshCw size={13} className={loading ? 'animate-spin' : ''} />
          </button>
        </div>
      </div>

      {/* ── 主体 ──────────────────────────────────────────────────────── */}
      <div className="flex-1 min-h-0 overflow-hidden flex flex-col">
        {error && (
          <div className="m-4 text-[13px] text-red-500 bg-red-50 rounded-lg px-3 py-2 border border-red-200">{error}</div>
        )}
        {!error && !loading && data && !hasContent && (
          <div className="flex-1 flex items-center justify-center text-[13px] text-faint">
            <div className="text-center">
              <Clock size={32} className="mx-auto mb-2 opacity-30" />
              <div>此区间无数据</div>
              <div className="text-[11px] mt-1 opacity-60">先在写作台录入章节事件,或扩大章号范围</div>
            </div>
          </div>
        )}
        {loading && !hasContent && (
          <div className="flex-1 flex items-center justify-center text-[12px] text-faint gap-2">
            <RefreshCw size={14} className="animate-spin" />加载时间线…
          </div>
        )}

        {hasContent && (
          <div className="flex-1 min-h-0 overflow-auto" ref={containerRef}>
            <div style={{ display: 'flex', minWidth: 'max-content' }}>

              {/* 左侧泳道标签(固定宽) */}
              <div style={{ width: LABEL_W, minWidth: LABEL_W, flexShrink: 0, borderRight: '1px solid var(--color-line)' }}>
                <div style={{ height: HEADER_H }} />
                {allLaneKeys.map((lk) => {
                  const visible = !hiddenLanes.has(lk)
                  return (
                    <div key={lk} style={{
                      height: LANE_H, borderTop: '1px solid var(--color-line)',
                      display: 'flex', alignItems: 'center', padding: '0 6px', gap: 4,
                      opacity: visible ? 1 : 0.35,
                    }}>
                      <button onClick={() => toggleLane(lk)}
                        title={visible ? '隐藏' : '显示'}
                        style={{
                          width: 14, height: 14, borderRadius: 3, flexShrink: 0, cursor: 'pointer',
                          border: '1px solid var(--color-line)',
                          background: visible ? 'var(--color-brand)' : 'transparent',
                          color: visible ? '#fff' : 'var(--color-faint)',
                          fontSize: 8, display: 'flex', alignItems: 'center', justifyContent: 'center',
                        }}
                      >●</button>
                      <span style={{
                        fontSize: 10, color: 'var(--color-faint)', userSelect: 'none',
                        overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                        maxWidth: LABEL_W - 28,
                      }} title={lk === '__promise__' ? '伏笔' : stripRole(lk)}>
                        {lk === '__promise__' ? '◇伏笔' : stripRole(lk)}
                      </span>
                    </div>
                  )
                })}
              </div>

              {/* 右侧:表头 + 泳道内容 */}
              <div style={{ position: 'relative', flexShrink: 0, isolation: 'isolate' }}>
                {/* 章号表头 */}
                <div style={{
                  display: 'flex', height: HEADER_H,
                  width: chRange.length * COL_W,
                  borderBottom: '1px solid var(--color-line)',
                }}>
                  {chRange.map((ch) => (
                    <div key={ch} style={{
                      width: COL_W, minWidth: COL_W, height: HEADER_H,
                      borderRight: '1px solid var(--color-line)',
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      opacity: 0.5,
                    }}>
                      <span style={{ fontSize: 10, fontFamily: 'monospace', userSelect: 'none' }}>第{ch}章</span>
                    </div>
                  ))}
                </div>

                {/* 泳道行 */}
                {allLaneKeys.map((lk) => {
                  if (hiddenLanes.has(lk)) {
                    return (
                      <div key={lk} style={{
                        height: LANE_H, borderTop: '1px solid var(--color-line)',
                        width: chRange.length * COL_W, opacity: 0.15,
                        background: 'repeating-linear-gradient(45deg, transparent, transparent 8px, var(--color-soft) 8px, var(--color-soft) 9px)',
                      }} />
                    )
                  }
                  return (
                    <div key={lk} style={{
                      borderTop: '1px solid var(--color-line)',
                      position: 'relative',
                      width: chRange.length * COL_W,
                    }}>
                      {/* 列竖线 */}
                      <div style={{ position: 'absolute', top: 0, left: 0, display: 'flex', height: '100%', pointerEvents: 'none', zIndex: 0 }}>
                        {chRange.map((ch) => (
                          <div key={ch} style={{
                            width: COL_W, minWidth: COL_W, height: '100%',
                            borderRight: '1px dashed var(--color-line)', opacity: 0.25,
                          }} />
                        ))}
                      </div>
                      <LaneRow
                        laneKey={lk}
                        items={laneMap[lk] || []}
                        chFrom={data.from || chFrom}
                        chRange={chRange}
                        onJumpChapter={onJumpChapter}
                        laneMode={laneMode}
                        onTimelineRefresh={() => load(chFrom, chTo)}
                      />
                    </div>
                  )
                })}

                {/* 因果弧线叠层(完整期):覆盖全部泳道区域,绝对定位在 HEADER_H 以下 */}
                {showCausal && (
                  <div style={{
                    position: 'absolute',
                    top: HEADER_H,
                    left: 0,
                    width: chRange.length * COL_W,
                    height: allLaneKeys.length * LANE_H,
                    pointerEvents: 'none',
                    zIndex: 25,
                  }}>
                    <CausalArrowLayer
                      items={data.items || []}
                      allLaneKeys={allLaneKeys}
                      chFrom={data.from || chFrom}
                      totalCols={chRange.length}
                      hiddenLanes={hiddenLanes}
                      laneMode={laneMode}
                    />
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* 图例 */}
        {hasContent && (
          <div className="shrink-0 flex items-center gap-3 px-4 py-1.5 border-t border-line bg-surface/50 overflow-x-auto text-[10px] text-faint">
            <span className="shrink-0 font-medium">图例:</span>
            <span className="shrink-0 inline-flex items-center gap-1">
              <i className="inline-block w-3 h-3 rounded border-l-2 border-brand bg-surface shrink-0" />事件卡
            </span>
            <span className="shrink-0 inline-flex items-center gap-1">
              <i className="inline-block w-2.5 h-2.5 bg-purple-600 shrink-0" style={{ transform: 'rotate(45deg)' }} />弧光◆
            </span>
            <span className="shrink-0 inline-flex items-center gap-1">
              <i className="inline-block w-3 h-2 rounded bg-amber-400/25 border border-amber-400 shrink-0" />伏笔条
            </span>
            <span className="shrink-0 inline-flex items-center gap-1">
              <i className="inline-block w-3 h-2 rounded border border-dashed border-sky-500 shrink-0" />关系甘特
            </span>
            <span className="shrink-0 text-red-500">⚠ 超期未收</span>
            <span className="shrink-0">✗ 失效</span>
            <span className="shrink-0 inline-flex items-center gap-1">
              <i className="inline-block w-3 h-2 rounded border border-dashed border-slate-400 bg-slate-100/30 shrink-0" />障眼法
            </span>
            <span className="shrink-0 inline-flex items-center gap-1" style={{ color: CAUSAL_COLOR }}>
              <svg width={20} height={10} viewBox="0 0 20 10" style={{ display: 'inline' }}>
                <defs>
                  <marker id="leg-causal" markerWidth={5} markerHeight={5} refX={4} refY={2.5} orient="auto">
                    <path d="M0,0 L0,5 L5,2.5 z" fill={CAUSAL_COLOR} opacity={0.7} />
                  </marker>
                </defs>
                <path d="M 1 8 Q 10 2 19 8" fill="none" stroke={CAUSAL_COLOR} strokeWidth={1.5}
                  strokeDasharray="4 2" opacity={0.65} markerEnd="url(#leg-causal)" />
              </svg>
              因果弧线(开关见顶栏)
            </span>
          </div>
        )}
      </div>
    </div>
  )
}
