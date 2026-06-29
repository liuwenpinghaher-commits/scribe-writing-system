import { useEffect, useMemo, useRef, useState } from 'react'
import { useVirtualizer } from '@tanstack/react-virtual'
import { LayoutGrid, Table2, List, Plus, Pencil, Trash2, Check, X } from 'lucide-react'
import { api } from './api'
import { Corkboard } from './Corkboard'
import { Outliner } from './Outliner'
import { chapterLabel } from './chapterLabel'
import { wcLabel } from './outlineColors'
import { useToast } from './ui/Toast'

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

// 卷标题 inline 重命名小组件
function VolumeTitle({ vid, title, onRename, onDelete }) {
  const [editing, setEditing] = useState(false)
  const [val, setVal] = useState(title)
  const ref = useRef(null)
  useEffect(() => { if (editing && ref.current) { ref.current.focus(); ref.current.select() } }, [editing])
  useEffect(() => { if (!editing) setVal(title) }, [title, editing])
  const commit = () => {
    setEditing(false)
    const next = val.trim()
    if (next && next !== title) onRename(vid, next)
  }
  const cancel = () => { setVal(title); setEditing(false) }
  if (editing) {
    return (
      <span className="inline-flex items-center gap-1">
        <input ref={ref} value={val} onChange={(e) => setVal(e.target.value)}
          onBlur={commit}
          onKeyDown={(e) => { if (e.key === 'Enter') commit(); if (e.key === 'Escape') cancel() }}
          className="rounded border border-brand/40 bg-canvas px-1.5 py-0.5 text-[13px] text-ink outline-none focus:border-brand w-32" />
        <button onClick={commit} title="确认" className="text-ok hover:text-ok/80 cursor-pointer"><Check size={13} /></button>
        <button onClick={cancel} title="取消" className="text-faint hover:text-ink cursor-pointer"><X size={13} /></button>
      </span>
    )
  }
  return (
    <span className="inline-flex items-center gap-1 group/vol">
      <span className="text-[15px] font-semibold text-ink">{title}</span>
      <button onClick={() => setEditing(true)} title="重命名卷"
        className="opacity-0 group-hover/vol:opacity-100 ml-1 text-faint hover:text-ink cursor-pointer transition-opacity">
        <Pencil size={12} />
      </button>
      <button onClick={() => onDelete(vid, title)} title="删除卷"
        className="opacity-0 group-hover/vol:opacity-100 text-faint hover:text-danger cursor-pointer transition-opacity">
        <Trash2 size={12} />
      </button>
    </span>
  )
}

// 容器节点(卷/手稿根)的多模式视图:卡片墙 / 大纲表 / 列表。
export function ContainerOutline({ node, onOpenChapter, onSelect }) {
  const [outline, setOutline] = useState(null)
  const [err, setErr] = useState(false)
  const [mode, setMode] = useStrPref('s3.container.mode', 'corkboard')
  const [colorMode, setColorMode] = useStrPref('s3.container.color', 'status')
  const [adding, setAdding] = useState(false)
  const [newTitle, setNewTitle] = useState('')
  const addRef = useRef(null)

  const toast = useToast()
  const isManuscript = node?.type === 'volume' || node?.type === 'manuscript_root'
  const reload = () => api.outline().then((o) => { setOutline(o); setErr(false) }).catch(() => setErr(true))
  useEffect(() => { if (isManuscript) reload() }, [isManuscript])
  useEffect(() => { if (adding && addRef.current) addRef.current.focus() }, [adding])

  const lanes = useMemo(() => buildLanes(outline, node), [outline, node])

  // 新建章:空书/任意手稿容器都能起新章(原本只有「新建卷」,无建章入口→空书没法开写)。
  // 算最大 seq+1,存空章(seq 是故事时间轴主键),reload 后打开进四阶段写作。
  const [addingCh, setAddingCh] = useState(false)
  const addChapter = async () => {
    if (addingCh) return
    setAddingCh(true)
    const maxSeq = (outline?.chapters || []).reduce((m, c) => Math.max(m, c.seq || 0), 0)
    const seq = maxSeq + 1
    try {
      await api.saveChapter(seq, '', `第${seq}章`, '')
      // 若当前在某卷视图,把新章归入该卷(否则进未分卷)
      if (node?.type === 'volume' && node.ref != null) {
        const volSeqs = (outline?.chapters || []).filter((c) => String(c.volume) === String(node.ref)).map((c) => c.seq)
        await api.reorderChapters(node.ref, [...volSeqs, seq]).catch(() => {})
      }
      await reload()
      onOpenChapter?.({ seq, title: `第${seq}章` })
    } catch (e) { toast?.(e?.body?.detail || '新建章失败', { tone: 'danger' }) }
    finally { setAddingCh(false) }
  }

  // synopsis inline 编辑:乐观更新 + 失败回滚
  const patchSynopsis = (seq, synopsis) => {
    setOutline((prev) => prev && ({
      ...prev,
      chapters: prev.chapters.map((c) => c.seq === seq ? { ...c, synopsis } : c),
    }))
    api.patchChapter(seq, { synopsis }).catch((e) => { reload(); toast?.(e?.body?.detail || '梗概保存失败', { tone: 'danger' }) })
  }

  // 卷内拖拽重排:乐观重排该卷章序 + 失败回滚
  const reorder = (volumeId, newSeqs, prevSeqs) => {
    setOutline((prev) => {
      if (!prev) return prev
      const inLane = new Set(newSeqs)
      const pos = new Map(newSeqs.map((s, i) => [s, i]))
      const laneChs = prev.chapters.filter((c) => inLane.has(c.seq))
        .sort((a, b) => pos.get(a.seq) - pos.get(b.seq))
      let li = 0
      const next = prev.chapters.map((c) => inLane.has(c.seq) ? laneChs[li++] : c)
      return { ...prev, chapters: next }
    })
    api.reorderChapters(volumeId, newSeqs).catch((e) => { reload(); toast?.(e?.body?.detail || '排序保存失败', { tone: 'danger' }) })
  }

  // 跨卷拖拽:把章从一个卷移到另一个卷(落到 overSeq 的位置前)
  const crossVolumeMove = (activeSeq, toVolumeId, overSeq) => {
    // 基于当前 outline(不是 lanes useMemo 快照)计算目标卷新顺序,
    // 这样即使 lanes 因为前一次 setOutline 还没 re-render 而过期也不会出错。
    const currentOutline = outline  // 读当前帧的 outline state
    const targetSeqs = (currentOutline?.chapters || [])
      .filter((c) => String(c.volume) === String(toVolumeId) && c.seq !== activeSeq)
      .map((c) => c.seq)
    const overIdxInTarget = targetSeqs.indexOf(overSeq)
    const newOrder = overIdxInTarget >= 0
      ? [...targetSeqs.slice(0, overIdxInTarget), activeSeq, ...targetSeqs.slice(overIdxInTarget)]
      : [...targetSeqs, activeSeq]

    // 乐观更新 UI
    setOutline((prev) => {
      if (!prev) return prev
      const ch = prev.chapters.find((c) => c.seq === activeSeq)
      if (!ch) return prev
      const withoutActive = prev.chapters.filter((c) => c.seq !== activeSeq)
      const overIdx = withoutActive.findIndex((c) => c.seq === overSeq)
      const insertAt = overIdx >= 0 ? overIdx : withoutActive.length
      const updated = { ...ch, volume: toVolumeId }
      const next = [
        ...withoutActive.slice(0, insertAt),
        updated,
        ...withoutActive.slice(insertAt),
      ]
      return { ...prev, chapters: next }
    })

    // 后端:更新 volume + sort_order
    api.reorderChapters(toVolumeId, newOrder)
      .catch((e) => { reload(); toast?.(e?.body?.detail || '跨卷移动失败', { tone: 'danger' }) })
  }

  // 新建卷
  const commitAddVolume = async () => {
    const t = newTitle.trim()
    if (!t) { setAdding(false); setNewTitle(''); return }
    const maxOrder = (outline?.volumes || []).reduce((m, v) => Math.max(m, v.sort_order ?? 0), 0)
    try {
      await api.addVolume(t, maxOrder + 1)
      setNewTitle('')
      setAdding(false)
      await reload()
    } catch (err) {
      console.error('addVolume failed', err)
    }
  }

  // 重命名卷
  const renameVolume = async (vid, title) => {
    try {
      await api.patchVolume(vid, { title })
      await reload()
    } catch (err) {
      console.error('patchVolume failed', err)
    }
  }

  // 删除卷(确认 → 章不删,volume 置空)
  const deleteVolume = async (vid, title) => {
    const vol = outline?.volumes?.find((v) => String(v.id) === String(vid))
    const chCount = lanes.find((l) => String(l.volumeId) === String(vid))?.chapters?.length ?? 0
    const msg = chCount > 0
      ? `删除卷「${title}」?\n该卷下 ${chCount} 章将移至「未分卷」(章内容不丢失)。`
      : `删除卷「${title}」?`
    if (!window.confirm(msg)) return
    try {
      await api.deleteVolume(vid)
      await reload()
    } catch (err) {
      console.error('deleteVolume failed', err)
    }
  }

  // 非手稿容器(素材分类等)→ 立即退化为子项列表(不拉 /outline)
  if (!isManuscript) return <PlainList node={node} onSelect={onSelect} />

  if (err) return <div className="p-8 text-[13px] text-danger">大纲加载失败。</div>
  if (!outline) return <div className="p-8 text-[13px] text-faint/60">加载大纲…</div>

  const totalCh = lanes.reduce((s, l) => s + l.chapters.length, 0)
  const totalWc = lanes.reduce((s, l) => s + l.chapters.reduce((a, c) => a + (c.word_count || 0), 0), 0)

  // 当前容器是单卷节点时,显示重命名/删除操作
  const isVolumeNode = node?.type === 'volume' && node.ref != null
  const currentVol = isVolumeNode ? (outline?.volumes || []).find((v) => String(v.id) === String(node.ref)) : null

  return (
    <div className="h-full flex flex-col min-h-0">
      {/* 工具条:模式 segmented + 色彩编码 + 卷操作 */}
      <div className="shrink-0 border-b border-line bg-surface px-5 py-2.5 flex items-center gap-3 flex-wrap">
        {/* 标题:手稿根 or 单卷 */}
        {isVolumeNode && currentVol ? (
          <VolumeTitle vid={currentVol.id} title={currentVol.title || '未命名卷'}
            onRename={renameVolume} onDelete={deleteVolume} />
        ) : (
          <h2 className="text-[15px] font-semibold text-ink">{node.label}</h2>
        )}
        <span className="text-[11px] text-faint">{totalCh} 章 · {wcLabel(totalWc)} 字</span>

        <div className="ml-auto flex items-center gap-3 flex-wrap">
          {/* 新建章(手稿根/卷都可)——空书起手必需 */}
          <button onClick={addChapter} disabled={addingCh}
            className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-[12px] bg-brand text-brandfg hover:opacity-90 transition-opacity cursor-pointer disabled:opacity-50">
            <Plus size={12} /> 新建章
          </button>
          {/* 手稿根时显示「新建卷」 */}
          {node?.type === 'manuscript_root' && (
            adding ? (
              <span className="inline-flex items-center gap-1">
                <input ref={addRef} value={newTitle} onChange={(e) => setNewTitle(e.target.value)}
                  placeholder="卷标题"
                  onKeyDown={(e) => { if (e.key === 'Enter') commitAddVolume(); if (e.key === 'Escape') { setAdding(false); setNewTitle('') } }}
                  onBlur={commitAddVolume}
                  className="rounded border border-brand/40 bg-canvas px-2 py-1 text-[12px] text-ink outline-none focus:border-brand w-28" />
              </span>
            ) : (
              <button onClick={() => setAdding(true)}
                className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-[12px] border border-line text-faint hover:text-ink hover:border-brand/40 transition-colors cursor-pointer">
                <Plus size={12} /> 新建卷
              </button>
            )
          )}

          {/* 模式切换 segmented */}
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
        {totalCh === 0 && lanes.length === 0 ? (
          <div className="py-12 text-center">
            <div className="text-[13px] text-faint/60 mb-3">还没有章节。</div>
            <button onClick={addChapter} disabled={addingCh}
              className="inline-flex items-center gap-1.5 px-3.5 h-9 rounded-lg bg-brand text-brandfg text-[13px] hover:opacity-90 cursor-pointer disabled:opacity-50">
              <Plus size={15} /> 新建第一章
            </button>
          </div>
        ) : mode === 'corkboard' ? (
          <Corkboard lanes={lanes} colorMode={colorMode} onOpen={onOpenChapter}
            onPatchSynopsis={patchSynopsis} onReorder={reorder} onCrossVolumeMove={crossVolumeMove} />
        ) : mode === 'outliner' ? (
          <Outliner lanes={lanes} colorMode={colorMode} onOpen={onOpenChapter}
            onPatchSynopsis={patchSynopsis} onReorder={reorder} onCrossVolumeMove={crossVolumeMove} />
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

// 素材分类:ref(cat_type)→ 可新建?(全部 7 类均可)
const CODEX_CATS = new Set(['character', 'faction', 'item', 'term', 'world_rule', 'promise', 'motif'])

// 虚拟化阈值:超过则用 react-virtual 渲染(千万字级条目全量可达,不截断、不爆 DOM)
const VIRTUAL_THRESHOLD = 80

// 虚拟化条目列表(单一滚动容器,只渲可视行)
function VirtualItemList({ kids, onSelect }) {
  const parentRef = useRef(null)
  const virt = useVirtualizer({
    count: kids.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 52,   // 卡片高度(px,含间距)约值
    overscan: 8,
  })
  return (
    <div ref={parentRef} className="flex-1 min-h-0 overflow-y-auto px-6 pb-6">
      <div className="max-w-2xl mx-auto relative" style={{ height: virt.getTotalSize() }}>
        {virt.getVirtualItems().map((vi) => {
          const c = kids[vi.index]
          return (
            <div key={c.id} ref={virt.measureElement} data-index={vi.index}
              style={{ position: 'absolute', top: 0, left: 0, width: '100%', transform: `translateY(${vi.start}px)` }}
              className="pb-1.5">
              <button onClick={() => onSelect?.(c)}
                className="w-full text-left rounded-xl border border-line bg-surface px-4 py-3 hover:border-brand/30 transition-colors cursor-pointer">
                <span className="text-[14px] text-ink">{c.label}</span>
              </button>
            </div>
          )
        })}
      </div>
    </div>
  )
}

// 非手稿容器(素材分类等)→ 子项列表 + 「+ 新建」入口 + 角色待确认引用
function PlainList({ node, onSelect }) {
  const kids = node?.children || []
  const catType = node?.ref
  const canCreate = node?.type === 'codex_category' && CODEX_CATS.has(catType)
  const newNode = () => onSelect?.({ id: `new:${catType}`, type: 'codex_new', ref: catType, label: node?.label })
  const virtualize = kids.length > VIRTUAL_THRESHOLD
  return (
    <div className="h-full flex flex-col min-h-0">
      {/* 头部:标题 + 新建 + 计数 + 待确认(不进虚拟滚动) */}
      <div className={`shrink-0 ${virtualize ? 'px-6 pt-6 pb-2' : 'hidden'}`}>
        <div className="max-w-2xl mx-auto">
          <div className="flex items-center gap-3 mb-1">
            <h2 className="text-[18px] font-semibold text-ink">{node?.label}</h2>
            {canCreate && (
              <button onClick={newNode}
                className="ml-auto inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-[12px] border border-brand/40 text-brand hover:bg-brand/10 transition-colors cursor-pointer">
                <Plus size={13} /> 新建
              </button>
            )}
          </div>
          <div className="text-[12px] text-faint">{kids.length} 项</div>
          {catType === 'character' && <UnverifiedRefs onSelect={onSelect} />}
        </div>
      </div>

      {virtualize ? (
        <VirtualItemList kids={kids} onSelect={onSelect} />
      ) : (
        <div className="flex-1 min-h-0 overflow-y-auto">
          <div className="max-w-2xl mx-auto px-6 py-6">
            <div className="flex items-center gap-3 mb-1">
              <h2 className="text-[18px] font-semibold text-ink">{node?.label}</h2>
              {canCreate && (
                <button onClick={newNode}
                  className="ml-auto inline-flex items-center gap-1 px-2.5 py-1 rounded-md text-[12px] border border-brand/40 text-brand hover:bg-brand/10 transition-colors cursor-pointer">
                  <Plus size={13} /> 新建
                </button>
              )}
            </div>
            <div className="text-[12px] text-faint mb-4">{kids.length} 项</div>
            {catType === 'character' && <UnverifiedRefs onSelect={onSelect} />}
            {kids.length === 0 ? (
              <div className="text-[13px] text-faint/60 py-8 text-center">
                暂无子项。{canCreate && <button onClick={newNode} className="text-brand hover:underline cursor-pointer ml-1">点此新建</button>}
              </div>
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
      )}
    </div>
  )
}

// ingest 抽出的库外人物引用 → 接受为角色 / 忽略(复用 /ingest-unverified 端点)
function UnverifiedRefs({ onSelect }) {
  const [items, setItems] = useState(null)
  const toast = useToast()
  const reload = () => api.listUnverified().then(setItems).catch(() => setItems([]))
  useEffect(() => { reload() }, [])
  const remove = (id) => setItems((prev) => (prev || []).filter((p) => p.id !== id))
  const accept = async (p) => {
    try { await api.acceptUnverified(p.id); remove(p.id); toast?.(`已接受「${p.name}」为角色`) }
    catch (e) { toast?.(e?.body?.detail || '接受失败', { tone: 'danger' }) }
  }
  const ignore = async (p) => {
    try { await api.ignoreUnverified(p.id); remove(p.id) }
    catch (e) { toast?.(e?.body?.detail || '忽略失败', { tone: 'danger' }) }
  }
  if (!items || items.length === 0) return null
  return (
    <div className="rounded-2xl border border-warn/30 bg-warn/[0.04] p-4 mb-4">
      <div className="text-[13px] font-medium text-ink mb-3">待确认人物引用 ({items.length})</div>
      <div className="space-y-2">
        {items.map((p) => (
          <div key={p.id} className="flex items-center justify-between gap-2 rounded-xl border border-line bg-canvas px-3 py-2">
            <span className="text-[13px] text-ink flex-1 min-w-0 truncate">
              {p.name} <span className="text-faint">· 第{p.seq}章 · {p.role}</span>
            </span>
            <div className="flex items-center gap-1.5 flex-shrink-0">
              <button onClick={() => accept(p)}
                className="text-[12px] px-2.5 py-1 rounded-lg border border-brand/40 text-brand hover:bg-brand/10 transition-colors cursor-pointer">接受为角色</button>
              <button onClick={() => ignore(p)}
                className="text-[12px] px-2.5 py-1 rounded-lg border border-line text-faint hover:bg-surface hover:text-ink transition-colors cursor-pointer">忽略</button>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
