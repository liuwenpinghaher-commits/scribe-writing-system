/**
 * TimelineView · 作者工具 F-02 · 时间线视图 MVP
 *
 * 单泳道横铺事件,按 story_chapter 定位 x,点击跳对应章。
 * 纯 CSS 绝对定位 + overflow-x-auto,不引入新依赖,不复用 ELK。
 */
import { useEffect, useRef, useState } from 'react'
import { Clock, RefreshCw, ChevronLeft, ChevronRight } from 'lucide-react'
import { api } from '../api'

// 事件类型配色(与 AtlasView.jsx REL_COLOR 风格一致,按事件类型着色)
const EVENT_TYPE_COLOR = {
  '炼器': '#7c3aed',
  '战斗': '#dc2626',
  '拜师': '#0ea5e9',
  '对话': '#16a34a',
  '决策': '#d97706',
  '失去': '#be185d',
  '获得': '#15803d',
}
const eventColor = (type) => EVENT_TYPE_COLOR[type] || '#64748b'

const COL_W = 140      // 每章宽度(px)
const ROW_H = 120      // 泳道高度(px)
const LABEL_W = 20     // 左侧章号刻度占位(px,极窄,刻度写在轴上)
const CARD_W = 110     // 事件卡宽度
const CARD_H = 72      // 事件卡高度

function EventCard({ item, onJumpChapter }) {
  const color = eventColor(item.event_type)
  const subj = (item.refs?.subj || []).map((s) => s.replace('role:', '')).join('、') || '—'
  const wit  = (item.refs?.witness || []).map((s) => s.replace('role:', '')).join('、')

  return (
    <div
      onClick={() => onJumpChapter?.(item.chapter)}
      title={`第${item.chapter}章 · ${item.label}${item.goal ? ' · ' + item.goal : ''}`}
      style={{
        position: 'absolute',
        left: 0,
        top: (ROW_H - CARD_H) / 2,
        width: CARD_W,
        height: CARD_H,
        borderLeft: `3px solid ${color}`,
        cursor: 'pointer',
      }}
      className="rounded-lg bg-surface border border-line shadow-sm px-2 py-1.5 flex flex-col gap-0.5 hover:shadow-md hover:border-brand/60 transition-shadow select-none"
    >
      <div className="flex items-center gap-1 min-w-0">
        <span
          className="shrink-0 inline-block w-2 h-2 rounded-full"
          style={{ background: color }}
        />
        <span className="text-[11px] font-semibold text-ink truncate">{item.label || item.event_type}</span>
        <span className="ml-auto text-[10px] text-faint shrink-0">ch{item.chapter}</span>
      </div>
      {item.goal && (
        <div className="text-[10.5px] text-faint truncate leading-tight">{item.goal}</div>
      )}
      <div className="text-[10px] text-faint/80 truncate leading-tight">
        主:{subj}{wit ? <span className="opacity-60"> 见:{wit}</span> : null}
      </div>
    </div>
  )
}

function ChapterColumn({ ch, items, onJumpChapter }) {
  return (
    <div
      style={{ width: COL_W, minWidth: COL_W, position: 'relative', height: ROW_H }}
      className="shrink-0 border-r border-line/40"
    >
      {/* 章号刻度 */}
      <div className="absolute top-0 left-0 right-0 h-6 flex items-center justify-center">
        <span className="text-[10px] text-faint font-mono select-none">第{ch}章</span>
      </div>
      {/* 水平轴线 */}
      <div
        className="absolute left-0 right-0 border-t border-line/50"
        style={{ top: ROW_H / 2 }}
      />
      {/* 事件卡:同章多个事件堆叠偏移 */}
      {items.map((item, idx) => (
        <div
          key={item.id}
          style={{
            position: 'absolute',
            left: idx * 6,
            top: (ROW_H - CARD_H) / 2 + idx * 4,
            zIndex: items.length - idx,
          }}
        >
          <EventCard item={item} onJumpChapter={onJumpChapter} />
        </div>
      ))}
      {/* 章节竖线(节拍点) */}
      <div
        className="absolute top-5 bottom-0 left-1/2 border-l border-dashed border-line/30"
        style={{ transform: 'translateX(-50%)' }}
      />
    </div>
  )
}

export function TimelineView({ onJumpChapter }) {
  const [data, setData] = useState(null)   // { from, to, max_chapter, items }
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [chFrom, setChFrom] = useState(1)
  const [chTo, setChTo] = useState(null)   // null = 全量
  const containerRef = useRef(null)

  const load = (from, to) => {
    setLoading(true)
    setError(null)
    api.timeline(from, to)
      .then((d) => { setData(d); setLoading(false) })
      .catch((e) => { setError(e.message || '加载失败'); setLoading(false) })
  }

  useEffect(() => { load(chFrom, chTo) }, [])   // 初次加载

  const reload = () => load(chFrom, chTo)

  const apply = () => load(chFrom, chTo)

  // 按章分组事件
  const chapters = data
    ? [...new Set(data.items.filter((i) => i.kind === 'event').map((i) => i.chapter))].sort((a, b) => a - b)
    : []

  const byChapter = (ch) =>
    (data?.items || []).filter((i) => i.kind === 'event' && i.chapter === ch)

  const maxCh = data?.max_chapter || 0

  return (
    <div className="h-full flex flex-col bg-canvas">
      {/* 顶栏 */}
      <div className="h-11 shrink-0 border-b border-line bg-surface flex items-center gap-3 px-4">
        <Clock size={15} className="text-brand shrink-0" />
        <span className="text-[13px] font-medium text-ink">时间线</span>
        {data && (
          <span className="text-[12px] text-faint tnum">
            {data.items.filter((i) => i.kind === 'event').length} 条事件
            {maxCh > 0 && ` · 共${maxCh}章`}
          </span>
        )}

        {/* 章号范围控件 */}
        <div className="flex items-center gap-1.5 ml-3">
          <span className="text-[11px] text-faint">第</span>
          <input
            type="number" min={1} max={maxCh || 999}
            value={chFrom}
            onChange={(e) => setChFrom(Math.max(1, Number(e.target.value)))}
            className="w-12 h-6 rounded border border-line bg-canvas text-center text-[12px] text-ink outline-none focus:border-brand"
          />
          <span className="text-[11px] text-faint">—</span>
          <input
            type="number" min={chFrom} max={maxCh || 999}
            placeholder={maxCh ? String(maxCh) : '末'}
            value={chTo ?? ''}
            onChange={(e) => setChTo(e.target.value === '' ? null : Math.max(chFrom, Number(e.target.value)))}
            className="w-12 h-6 rounded border border-line bg-canvas text-center text-[12px] text-ink outline-none focus:border-brand"
          />
          <span className="text-[11px] text-faint">章</span>
          <button
            onClick={apply}
            className="h-6 px-2 rounded bg-brand text-brandfg text-[11px] font-medium cursor-pointer hover:opacity-80 transition-opacity"
          >
            应用
          </button>
        </div>

        <div className="ml-auto">
          <button
            onClick={reload}
            disabled={loading}
            title="刷新时间线"
            className="w-7 h-7 grid place-items-center rounded-lg text-faint hover:text-ink hover:bg-soft transition-colors cursor-pointer disabled:opacity-40"
          >
            <RefreshCw size={13} className={loading ? 'animate-spin' : ''} />
          </button>
        </div>
      </div>

      {/* 主体:横向滚动时间线 */}
      <div className="flex-1 min-h-0 overflow-hidden flex flex-col">
        {error && (
          <div className="m-4 text-[13px] text-red-500 bg-red-50 rounded-lg px-3 py-2 border border-red-200">
            {error}
          </div>
        )}

        {!error && !loading && data && chapters.length === 0 && (
          <div className="flex-1 flex items-center justify-center text-[13px] text-faint">
            <div className="text-center">
              <Clock size={32} className="mx-auto mb-2 opacity-30" />
              <div>此区间无事件</div>
              <div className="text-[11px] mt-1 opacity-60">先在写作台录入章节事件,或扩大章号范围</div>
            </div>
          </div>
        )}

        {chapters.length > 0 && (
          <div
            ref={containerRef}
            className="flex-1 min-h-0 overflow-x-auto overflow-y-hidden"
            style={{ paddingLeft: 12, paddingRight: 24 }}
          >
            {/* 泳道标签 + 事件轨道 */}
            <div className="flex items-start" style={{ height: ROW_H, minWidth: chapters.length * COL_W }}>
              {/* 泳道名(左侧固定,此处极窄做占位) */}
              <div
                style={{ width: LABEL_W, minWidth: LABEL_W, height: ROW_H }}
                className="shrink-0 flex items-center justify-center"
              >
                <span
                  className="text-[9px] text-faint font-medium tracking-widest select-none"
                  style={{ writingMode: 'vertical-rl', transform: 'rotate(180deg)' }}
                >
                  事件
                </span>
              </div>

              {/* 章号列 */}
              {chapters.map((ch) => (
                <ChapterColumn
                  key={ch}
                  ch={ch}
                  items={byChapter(ch)}
                  onJumpChapter={onJumpChapter}
                />
              ))}
            </div>

            {/* 图例 */}
            <div className="flex items-center gap-4 px-2 py-2 border-t border-line/30">
              {Object.entries(EVENT_TYPE_COLOR).map(([type, color]) => (
                <span key={type} className="inline-flex items-center gap-1 text-[10px] text-faint">
                  <i className="w-2.5 h-2.5 rounded-sm inline-block shrink-0" style={{ background: color }} />
                  {type}
                </span>
              ))}
              <span className="inline-flex items-center gap-1 text-[10px] text-faint">
                <i className="w-2.5 h-2.5 rounded-sm inline-block shrink-0 bg-[#64748b]" />
                其他
              </span>
            </div>
          </div>
        )}

        {loading && chapters.length === 0 && (
          <div className="flex-1 flex items-center justify-center text-[12px] text-faint gap-2">
            <RefreshCw size={14} className="animate-spin" />加载时间线…
          </div>
        )}
      </div>
    </div>
  )
}
