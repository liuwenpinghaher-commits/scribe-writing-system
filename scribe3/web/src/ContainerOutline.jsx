import { useEffect, useMemo, useState } from 'react'
import { LayoutGrid, Table2, List } from 'lucide-react'
import { api } from './api'
import { Corkboard } from './Corkboard'
import { Outliner } from './Outliner'
import { chapterLabel } from './chapterLabel'
import { wcLabel } from './outlineColors'

function useStrPref(key, def) {
  const [v, setV] = useState(() => {
    try { return localStorage.getItem(key) || def } catch { return def }
  })
  useEffect(() => { try { localStorage.setItem(key, v) } catch { /* */ } }, [key, v])
  return [v, setV]
}

const SEG = [
  { key: 'corkboard', label: '卡片墙', icon: LayoutGrid },
  { key: 'outliner', label: '大纲表', icon: Table2 },
  { key: 'list', label: '列表', icon: List },
]

// 把 outline 数据 → 按卷分组的泳道(只取当前容器节点关心的卷)。
function buildLanes(outline, node) {
  if (!outline) return []
  const { volumes = [], chapters = [] } = outline
  const volTitle = (id) => {
    const v = volumes.find((x) => String(x.id) === String(id))
    return v ? (v.title || '未命名卷') : null
  }
  // 章按卷分组(保持 outline 已排好的 sort_order 顺序)
  const byVol = new Map()
  for (const c of chapters) {
    const vid = c.volume ?? null
    if (!byVol.has(vid)) byVol.set(vid, [])
    byVol.get(vid).push(c)
  }
  const laneFor = (vid) => ({
    volumeId: vid,
    title: vid == null ? '未分卷' : (volTitle(vid) || '未命名卷'),
    chapters: byVol.get(vid) || [],
  })

  if (node?.type === 'volume') {
    // 单卷(node.ref = 卷裸 id 或 null)
    const vid = node.ref ?? null
    return [laneFor(vid)]
  }
  // manuscript_root:所有卷 + 未分卷
  const lanes = volumes.map((v) => laneFor(v.id))
  if (byVol.has(null)) lanes.push(laneFor(null))
  return lanes
}

// 容器节点(卷/手稿根)的多模式视图:卡片墙 / 大纲表 / 列表。
export function ContainerOutline({ node, onOpenChapter, onSelect }) {
  const [outline, setOutline] = useState(null)
  const [err, setErr] = useState(false)
  const [mode, setMode] = useStrPref('s3.container.mode', 'corkboard')
  const [colorMode, setColorMode] = useStrPref('s3.container.color', 'status')

  const isManuscript = node?.type === 'volume' || node?.type === 'manuscript_root'
  const reload = () => api.outline().then((o) => { setOutline(o); setErr(false) }).catch(() => setErr(true))
  useEffect(() => { if (isManuscript) reload() }, [isManuscript])

  const lanes = useMemo(() => buildLanes(outline, node), [outline, node])

  // synopsis inline 编辑:乐观更新 + 失败回滚
  const patchSynopsis = (seq, synopsis) => {
    setOutline((prev) => prev && ({
      ...prev,
      chapters: prev.chapters.map((c) => c.seq === seq ? { ...c, synopsis } : c),
    }))
    api.patchChapter(seq, { synopsis }).catch(() => reload())
  }

  // 拖拽重排:乐观重排该卷章序 + 失败回滚
  const reorder = (volumeId, newSeqs, prevSeqs) => {
    setOutline((prev) => {
      if (!prev) return prev
      const inLane = new Set(newSeqs)
      const pos = new Map(newSeqs.map((s, i) => [s, i]))
      // 仅对该泳道内的章重排,其余保持
      const laneChs = prev.chapters.filter((c) => inLane.has(c.seq))
        .sort((a, b) => pos.get(a.seq) - pos.get(b.seq))
      let li = 0
      const next = prev.chapters.map((c) => inLane.has(c.seq) ? laneChs[li++] : c)
      return { ...prev, chapters: next }
    })
    api.reorderChapters(volumeId, newSeqs).catch(() => reload())
  }

  // 非手稿容器(素材分类等)→ 立即退化为子项列表(不拉 /outline)
  if (!isManuscript) return <PlainList node={node} onSelect={onSelect} />

  if (err) return <div className="p-8 text-[13px] text-danger">大纲加载失败。</div>
  if (!outline) return <div className="p-8 text-[13px] text-faint/60">加载大纲…</div>

  const totalCh = lanes.reduce((s, l) => s + l.chapters.length, 0)
  const totalWc = lanes.reduce((s, l) => s + l.chapters.reduce((a, c) => a + (c.word_count || 0), 0), 0)

  return (
    <div className="h-full flex flex-col min-h-0">
      {/* 工具条:模式 segmented + 色彩编码 */}
      <div className="shrink-0 border-b border-line bg-surface px-5 py-2.5 flex items-center gap-3 flex-wrap">
        <h2 className="text-[15px] font-semibold text-ink">{node.label}</h2>
        <span className="text-[11px] text-faint">{totalCh} 章 · {wcLabel(totalWc)} 字</span>
        <div className="ml-auto flex items-center gap-3">
          <div className="inline-flex rounded-lg border border-line p-0.5 bg-canvas">
            {SEG.map((s) => {
              const Icon = s.icon
              const active = mode === s.key
              return (
                <button key={s.key} onClick={() => setMode(s.key)}
                  className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-[12px] transition-colors cursor-pointer ${active ? 'bg-brand text-brandfg' : 'text-faint hover:text-ink'}`}>
                  <Icon size={13} />{s.label}
                </button>
              )
            })}
          </div>
          {mode !== 'list' && (
            <label className="inline-flex items-center gap-1.5 text-[11px] text-faint">
              色彩
              <select value={colorMode} onChange={(e) => setColorMode(e.target.value)}
                className="h-7 rounded-md border border-line bg-canvas px-1.5 text-[12px] text-ink outline-none cursor-pointer">
                <option value="status">按状态</option>
                <option value="pov">按视角</option>
              </select>
            </label>
          )}
        </div>
      </div>

      <div className="flex-1 min-h-0 overflow-y-auto px-5 py-4">
        {totalCh === 0 ? (
          <div className="text-[13px] text-faint/60 py-10 text-center">暂无章节。</div>
        ) : mode === 'corkboard' ? (
          <Corkboard lanes={lanes} colorMode={colorMode} onOpen={onOpenChapter}
            onPatchSynopsis={patchSynopsis} onReorder={reorder} />
        ) : mode === 'outliner' ? (
          <Outliner lanes={lanes} colorMode={colorMode} onOpen={onOpenChapter}
            onPatchSynopsis={patchSynopsis} onReorder={reorder} />
        ) : (
          <PlainChapterList lanes={lanes} onOpen={onOpenChapter} />
        )}
      </div>
    </div>
  )
}

// 列表模式(轻量,不拖拽)
function PlainChapterList({ lanes, onOpen }) {
  return (
    <div className="max-w-2xl">
      {lanes.map((lane) => (
        <div key={lane.volumeId ?? 'null'} className="mb-5">
          <div className="text-[13px] font-semibold text-ink mb-1.5">{lane.title}
            <span className="ml-2 text-[11px] font-normal text-faint">{lane.chapters.length} 章</span></div>
          <div className="space-y-1">
            {lane.chapters.map((c) => (
              <button key={c.seq} onClick={() => onOpen?.(c)}
                className="w-full text-left rounded-lg border border-line bg-surface px-3 py-2 hover:border-brand/30 transition-colors cursor-pointer flex items-center gap-2">
                <span className="text-[13px] text-ink truncate">{chapterLabel(c.seq, c.title || '')}</span>
                <span className="ml-auto text-[11px] text-faint tnum shrink-0">{wcLabel(c.word_count)}</span>
              </button>
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}

// 非手稿容器(素材分类等)→ 沿用 MVP 子项列表
function PlainList({ node, onSelect }) {
  const kids = node?.children || []
  return (
    <div className="h-full overflow-y-auto">
      <div className="max-w-2xl mx-auto px-6 py-6">
        <h2 className="text-[18px] font-semibold text-ink mb-1">{node?.label}</h2>
        <div className="text-[12px] text-faint mb-4">{kids.length} 项</div>
        {kids.length === 0 ? (
          <div className="text-[13px] text-faint/60 py-8 text-center">暂无子项。</div>
        ) : (
          <div className="space-y-1.5">
            {kids.map((c) => (
              <button key={c.id} onClick={() => onSelect?.(c)}
                className="w-full text-left rounded-xl border border-line bg-surface px-4 py-3 hover:border-brand/30 transition-colors cursor-pointer">
                <span className="text-[14px] text-ink">{c.label}</span>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
