import { useCallback, useEffect, useRef, useState } from 'react'
import { api } from './api'
import { ProjectTree, CONTAINER_TYPES } from './ProjectTree'
import { DetailPane } from './DetailPane'

// 宽度持久化(同 shell.jsx 范式)
function useNumPref(key, def) {
  const [v, setV] = useState(() => {
    try { const s = localStorage.getItem(key); return s == null ? def : Number(s) || def } catch { return def }
  })
  useEffect(() => { try { localStorage.setItem(key, String(v)) } catch { /* */ } }, [key, v])
  return [v, setV]
}

// 收集容器节点 id(默认展开两根 + 各分类容器折叠;手稿支卷默认展开)
function defaultExpanded(tree) {
  const s = new Set(['manuscript_root', 'codex_root'])
  for (const v of tree?.manuscript?.children || []) s.add(v.id)   // 卷默认展开
  return s
}

/**
 * 混合 Binder 顶层布局:左侧常驻项目树 + 中间 DetailPane(按 sel 路由)。
 * sel 单一真相源:{mode:'node', node} | {mode:'view', viewKey}。
 * sel 由父层(App)持有,以便横切顶栏 tab 也能切 sel。
 */
export function BinderLayout({ work, sel, onSel, onJumpChapter }) {
  const [tree, setTree] = useState(null)
  const [expanded, setExpanded] = useState(() => new Set(['manuscript_root', 'codex_root']))
  const [lw, setLw] = useNumPref('s3.binder.lw', 264)
  const initedRef = useRef(false)

  const reload = useCallback(() => api.projectTree().then((t) => {
    setTree(t)
    if (!initedRef.current) { setExpanded(defaultExpanded(t)); initedRef.current = true }
  }).catch(() => {}), [])

  useEffect(() => { initedRef.current = false; reload() }, [work])

  // live SSE:别处改数据后服务端推事件 → 防抖 600ms 重拉项目树,保持树/大纲不 stale。
  useEffect(() => {
    let timer = null
    const es = api.live(() => {
      clearTimeout(timer)
      timer = setTimeout(reload, 600)
    })
    return () => {
      clearTimeout(timer)
      es.close()
    }
  }, [reload])

  const toggle = (id) => setExpanded((prev) => {
    const n = new Set(prev)
    n.has(id) ? n.delete(id) : n.add(id)
    return n
  })

  const onSelectNode = (node) => {
    if (node.type === 'view') { onSel({ mode: 'view', viewKey: node.id.split(':')[1] }); return }
    onSel({ mode: 'node', node })
  }

  const startResize = (e) => {
    e.preventDefault()
    const x0 = e.clientX, w0 = lw
    const move = (ev) => setLw(Math.max(190, Math.min(480, w0 + (ev.clientX - x0))))
    const up = () => {
      document.removeEventListener('mousemove', move); document.removeEventListener('mouseup', up)
      document.body.style.cursor = ''; document.body.style.userSelect = ''
    }
    document.addEventListener('mousemove', move); document.addEventListener('mouseup', up)
    document.body.style.cursor = 'col-resize'; document.body.style.userSelect = 'none'
  }

  // 卷 CRUD 回调(ProjectTree 发起 → BinderLayout 执行 → 树重载)
  const handleVolumeRename = async (vid, newTitle) => {
    try { await api.patchVolume(vid, { title: newTitle }); reload() } catch (e) { console.error(e) }
  }

  const handleVolumeDelete = async (vid, label) => {
    // 找该卷下章数
    const vols = tree?.manuscript?.children || []
    const volNode = vols.find((v) => v.ref === vid)
    const chCount = volNode?.children?.length ?? 0
    const msg = chCount > 0
      ? `删除卷「${label}」?\n该卷下 ${chCount} 章将移至「未分卷」(章内容不丢失)。`
      : `删除卷「${label}」?`
    if (!window.confirm(msg)) return
    try { await api.deleteVolume(vid); reload() } catch (e) { console.error(e) }
  }

  const handleAddVolume = async () => {
    const title = window.prompt('新建卷标题:')
    if (!title?.trim()) return
    try {
      const vols = tree?.manuscript?.children || []
      const maxOrder = vols.reduce((m, v) => Math.max(m, v.sort_order ?? 0), 0)
      await api.addVolume(title.trim(), maxOrder + 1)
      reload()
    } catch (e) { console.error(e) }
  }

  const selId = sel?.mode === 'node' ? sel.node?.id : null

  return (
    <div className="h-full flex bg-canvas min-h-0">
      <div className="shrink-0 bg-surface border-r border-line overflow-y-auto overflow-x-hidden" style={{ width: lw }}>
        <ProjectTree tree={tree} selId={selId} expanded={expanded} onToggle={toggle} onSelect={onSelectNode}
          onVolumeRename={handleVolumeRename}
          onVolumeDelete={handleVolumeDelete}
          onAddVolume={handleAddVolume} />
      </div>
      <div onMouseDown={startResize}
        className="w-px shrink-0 bg-line hover:bg-brand/50 cursor-col-resize transition-colors"
        style={{ marginInline: '-1px', width: 3 }} />
      <main className="flex-1 min-w-0 overflow-hidden flex flex-col">
        <DetailPane sel={sel} work={work} onSelectNode={onSelectNode}
          onTreeChanged={reload} onJumpChapter={onJumpChapter} />
      </main>
    </div>
  )
}

export { CONTAINER_TYPES }
