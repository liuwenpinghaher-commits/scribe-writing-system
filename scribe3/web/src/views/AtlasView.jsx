import { useEffect, useState } from 'react'
import { ReactFlow, Background, Controls } from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import ELK from 'elkjs/lib/elk.bundled.js'
import { Eye } from 'lucide-react'
import { api } from '../api'

// 关系图谱 = scribe3 真知识图:角色 —knows→ 命题(谁知道什么)+ 角色关系边。ELK 布局 + 类型着色。
const elk = new ELK()

const REL_COLOR = {
  // 亲缘类 — amber
  '父子': '#d97706', '母子': '#d97706', '兄弟': '#b45309', '姐妹': '#b45309',
  '夫妻': '#c2410c', '养父子': '#92400e',
  // 友善类 — green
  '知己': '#16a34a', '战友': '#15803d', '盟友': '#166534',
  '同门': '#4ade80', '恩人': '#22c55e',
  // 普通类 — sky
  '同行': '#0ea5e9', '熟人': '#38bdf8', '上下级': '#0284c7', '雇主雇员': '#0369a1',
  // 敌对类 — red
  '仇敌': '#dc2626', '宿敌': '#b91c1c', '竞争者': '#f87171', '利益对立': '#ef4444',
  // 情感类 — pink/rose
  '爱恨交织': '#db2777', '前恋人': '#ec4899', '背叛者': '#be185d',
  // 师徒类 — purple
  '师徒': '#7c3aed',
  // 英文兼容(保持原色)
  ally: '#16a34a', enemy: '#dc2626', kin: '#d97706',
  master_disciple: '#7c3aed', lover: '#db2777',
  // knows edge
  knows: 'var(--color-line)',
}
const relColor = (rel) => REL_COLOR[rel] || '#0ea5e9'

const REL_LABEL = {
  // 亲缘类
  '父子': '父子', '母子': '母子', '兄弟': '兄弟', '姐妹': '姐妹',
  '夫妻': '夫妻', '养父子': '养父子',
  // 友善类
  '知己': '知己', '战友': '战友', '盟友': '盟友', '同门': '同门', '恩人': '恩人',
  // 普通类
  '同行': '同行', '熟人': '熟人', '上下级': '上下级', '雇主雇员': '雇主雇员',
  // 敌对类
  '仇敌': '仇敌', '宿敌': '宿敌', '竞争者': '竞争者', '利益对立': '利益对立',
  // 情感类
  '爱恨交织': '爱恨交织', '前恋人': '前恋人', '背叛者': '背叛者',
  // 师徒
  '师徒': '师徒',
  // 英文兼容
  ally: '盟友', enemy: '敌对', kin: '血亲', master_disciple: '师徒', lover: '恋人',
}

function nodeStyle(n) {
  const isChar = n.type === 'character'
  const bg = isChar ? 'var(--color-brand)' : n.secret ? 'var(--color-secret)' : 'var(--color-irony)'
  return {
    background: bg, color: '#fff', border: 'none', borderRadius: isChar ? 999 : 8,
    padding: isChar ? '6px 14px' : '5px 10px', fontSize: isChar ? 13 : 11.5,
    fontWeight: isChar ? 600 : 400, width: 'auto', maxWidth: 180, textAlign: 'center',
    boxShadow: '0 1px 3px rgba(0,0,0,.18)',
  }
}

async function elkLayout(nodes, edges) {
  const g = {
    id: 'root',
    layoutOptions: {
      'elk.algorithm': 'force',
      'elk.force.iterations': '300',
      'elk.spacing.nodeNode': '40',
    },
    children: nodes.map((n) => ({ id: n.id, width: 160, height: 38 })),
    edges: edges.map((e) => ({ id: e.id, sources: [e.source], targets: [e.target] })),
  }
  const res = await elk.layout(g)
  const pos = {}
  res.children.forEach((c) => { pos[c.id] = { x: c.x, y: c.y } })
  return nodes.map((n) => ({ ...n, position: pos[n.id] || { x: 0, y: 0 } }))
}

function RelLegend({ edges }) {
  const present = [...new Set(edges.map((e) => e.rel).filter((r) => r && r !== 'knows'))]
  if (present.length === 0) return null
  return (
    <div className="absolute bottom-10 right-3 z-10 rounded-lg border border-line bg-surface/90 backdrop-blur px-3 py-2 flex flex-col gap-1 shadow-sm">
      <span className="text-[11px] font-medium text-faint mb-0.5">角色关系</span>
      {present.map((rel) => (
        <span key={rel} className="inline-flex items-center gap-1.5 text-[11px] text-ink">
          <i className="w-3 h-[2px] rounded-full inline-block" style={{ background: relColor(rel) }} />
          {REL_LABEL[rel] || rel}
        </span>
      ))}
    </div>
  )
}

export function AtlasView() {
  const [nodes, setNodes] = useState([])
  const [edges, setEdges] = useState([])
  const [stat, setStat] = useState({ c: 0, p: 0, e: 0 })
  const [raw, setRaw] = useState(null)
  const [focus, setFocus] = useState('') // '' = 全部

  useEffect(() => {
    let alive = true
    api.graph().then((g) => {
      if (!alive) return
      setRaw(g)
      setStat({ c: g.nodes.filter((n) => n.type === 'character').length, p: g.nodes.filter((n) => n.type === 'proposition').length, e: g.edges.length })
    })
    return () => { alive = false }
  }, [])

  useEffect(() => {
    if (!raw) return
    let alive = true
    let srcNodes = raw.nodes
    let srcEdges = raw.edges
    if (focus !== '') {
      // 聚焦:只保留 focus 角色 + 与之直连的命题节点 + 这些边
      const keep = new Set([focus])
      const focusEdges = raw.edges.filter((e) => e.src === focus || e.dst === focus)
      focusEdges.forEach((e) => { keep.add(e.src); keep.add(e.dst) })
      srcNodes = raw.nodes.filter((n) => keep.has(n.id))
      srcEdges = focusEdges
    }
    const rfNodes = srcNodes.map((n) => ({ id: n.id, data: { label: n.label || n.id }, style: nodeStyle(n), position: { x: 0, y: 0 } }))
    const rfEdges = srcEdges.map((e, i) => ({
      id: 'e' + i,
      source: e.src,
      target: e.dst,
      label: e.rel === 'knows' ? undefined : (REL_LABEL[e.rel] || e.rel),
      style: { stroke: relColor(e.rel), strokeWidth: e.rel === 'knows' ? 1.5 : 2 },
    }))
    elkLayout(rfNodes, rfEdges).then((laid) => {
      if (!alive) return
      setNodes(laid); setEdges(rfEdges)
    })
    return () => { alive = false }
  }, [raw, focus])

  return (
    <div className="h-full flex flex-col bg-canvas">
      <div className="h-11 shrink-0 border-b border-line bg-surface flex items-center gap-3 px-4">
        <Eye size={15} className="text-brand" />
        <span className="text-[13px] font-medium text-ink">知识图谱</span>
        <span className="text-[12px] text-faint tnum">{stat.c} 角色 · {stat.p} 命题 · {stat.e} 条「知道」</span>
        <select
          value={focus}
          onChange={(e) => setFocus(e.target.value)}
          className="h-7 rounded-lg border border-line bg-canvas px-2 text-[12.5px]"
        >
          <option value="">全部角色</option>
          {(raw?.nodes || []).filter((n) => n.type === 'character').map((n) => (
            <option key={n.id} value={n.id}>{n.label || n.id}</option>
          ))}
        </select>
        <div className="ml-auto flex items-center gap-3 text-[11px] text-faint">
          <span className="inline-flex items-center gap-1.5"><i className="w-2.5 h-2.5 rounded-full" style={{ background: 'var(--color-brand)' }} />角色</span>
          <span className="inline-flex items-center gap-1.5"><i className="w-2.5 h-2.5 rounded" style={{ background: 'var(--color-irony)' }} />命题</span>
          <span className="inline-flex items-center gap-1.5"><i className="w-2.5 h-2.5 rounded" style={{ background: 'var(--color-secret)' }} />私密</span>
        </div>
      </div>
      <div className="flex-1 min-h-0 relative">
        <ReactFlow nodes={nodes} edges={edges} fitView proOptions={{ hideAttribution: true }}
          nodesDraggable nodesConnectable={false} minZoom={0.2}>
          <Background color="var(--color-line)" gap={22} />
          <Controls showInteractive={false} />
        </ReactFlow>
        <RelLegend edges={raw?.edges || []} />
      </div>
    </div>
  )
}
