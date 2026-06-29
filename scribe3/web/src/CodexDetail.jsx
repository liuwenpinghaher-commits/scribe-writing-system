import { useEffect, useState } from 'react'
import { Loader2 } from 'lucide-react'
import { api } from './api'
import { DetailView } from './views/CodexView'
import { ConfirmDialog } from './ui/Dialog.jsx'
import { showToast } from './ui/Toast'

// 项目树「素材叶」类型 → CodexView DetailView 的 type 值。
const TYPE_MAP = {
  character: 'chars',
  faction: 'factions',
  item: 'items',
  term: 'terms',
  world_rule: 'rules',
  promise: 'promises',
  motif: 'motifs',
}

// 裸 id:角色行 id 形如 "role:焦三",取冒号后;其余设定多用 name 作主键。
const localOf = (row) => (row.id || '').includes(':') ? row.id.split(':').slice(1).join(':') : (row.id || row.name || '')

// 按 type 拉「该分类全部条目」,再按 ref 选中一条(复用 CodexView 的多端点读路径)。
async function loadRows(nodeType) {
  if (nodeType === 'character') {
    const es = await api.entities()
    return es.filter((e) => e.kind === 'character')
  }
  if (nodeType === 'faction') return api.get('/factions').catch(() => [])
  if (nodeType === 'item') return api.get('/items').catch(() => [])
  if (nodeType === 'term') return api.get('/terms').catch(() => [])
  if (nodeType === 'world_rule') return api.get('/world-rules').catch(() => [])
  if (nodeType === 'promise') return api.promises().catch(() => [])
  if (nodeType === 'motif') return api.motifs().catch(() => [])
  return []
}

// 选中条目:角色用裸 id(local)匹配,其余用 name 匹配(与 /project-tree 的 ref 约定一致)。
function pickRow(nodeType, rows, ref) {
  if (nodeType === 'character') return rows.find((r) => localOf(r) === ref || r.id === `role:${ref}`)
  if (nodeType === 'promise' || nodeType === 'motif') return rows.find((r) => r.id === ref)
  return rows.find((r) => r.name === ref)
}

async function persist(detailType, updated) {
  if (detailType === 'chars') await api.editChar(localOf(updated), updated)
  else if (detailType === 'rules') await api.post('/world-rules', updated)
  else if (detailType === 'factions') await api.post('/factions', updated)
  else if (detailType === 'items') await api.post('/items', updated)
  else if (detailType === 'terms') await api.post('/terms', updated)
  else if (detailType === 'promises') await api.editPromise(updated.id, updated)
  else if (detailType === 'motifs') await api.editMotif(updated.id, updated)
}

async function remove(detailType, row) {
  if (detailType === 'chars') await api.delChar(localOf(row))
  else if (detailType === 'rules') await api.del(`/world-rules?name=${encodeURIComponent(row.name)}`)
  else if (detailType === 'factions') await api.del(`/factions?name=${encodeURIComponent(row.name)}`)
  else if (detailType === 'items') await api.del(`/items?name=${encodeURIComponent(row.name)}`)
  else if (detailType === 'terms') await api.del(`/terms?name=${encodeURIComponent(row.name)}`)
  else if (detailType === 'promises') await api.delPromise(row.id)
  else if (detailType === 'motifs') await api.delMotif(row.id)
}

/**
 * 素材叶节点的中间栏详情卡:复用 CodexView 的 DetailView(角色档案/通用字段表/弧光/关系),
 * 自己负责按 node 懒加载该条全字段 + 落库回写。
 */
export function CodexDetail({ node, onChanged, onDeleted }) {
  const [row, setRow] = useState(null)
  const [loading, setLoading] = useState(true)
  const [delOpen, setDelOpen] = useState(false)
  const detailType = TYPE_MAP[node?.type]

  const reload = () => {
    if (!node || !detailType) { setLoading(false); return }
    setLoading(true)
    loadRows(node.type)
      .then((rows) => { setRow(pickRow(node.type, rows, node.ref) || null); setLoading(false) })
      .catch(() => { setRow(null); setLoading(false) })
  }
  useEffect(() => { reload() }, [node?.id])

  if (!detailType) return <div className="p-6 text-[13px] text-faint">未知设定类型:{node?.type}</div>
  if (loading) return <div className="flex items-center justify-center py-12 text-faint"><Loader2 size={20} className="animate-spin mr-2" />加载中…</div>
  if (!row) return <div className="p-6 text-[13px] text-faint">未找到该条目(可能已删除)。</div>

  const doDelete = async () => {
    try { await remove(detailType, row); onDeleted?.() }
    catch (e) { showToast(e?.body?.detail || e?.message || '删除失败', { tone: 'danger' }) }
  }

  return (
    <div className="h-full overflow-y-auto">
      <div className="max-w-2xl mx-auto px-6 py-5">
        <DetailView
          type={detailType}
          row={row}
          isNew={false}
          onBack={null}
          onUpdate={async (updated) => {
            try { await persist(detailType, updated); reload(); onChanged?.() }
            catch (e) { showToast(e?.body?.detail || e?.message || '保存失败', { tone: 'danger' }) }
          }}
          onDelete={() => setDelOpen(true)}
        />
      </div>
      <ConfirmDialog
        open={delOpen}
        title="确认删除?"
        body={`将删除「${row.name || row.text || node.ref}」,此操作不可撤销。`}
        danger
        confirmText="删除"
        onConfirm={doDelete}
        onClose={() => setDelOpen(false)}
      />
    </div>
  )
}
