import { useEffect, useState } from 'react'
import { Loader2, GitBranch, Trash2, Plus, AudioLines, Boxes, Lock, History, EyeOff, Heart } from 'lucide-react'
import { api } from './api'
import { DetailView, seedChiefCodexWrite } from './views/CodexView'
import { ConfirmDialog } from './ui/Dialog.jsx'
import { AsyncState } from './ui/AsyncState.jsx'
import { showToast } from './ui/Toast'
import { Btn, SectionTitle, Empty, Tag } from './ui'
import { ReadOnlyText } from './ui/EditableText.jsx'

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

function lifecycleDeleteBody(impact, fallback) {
  if (!impact) return fallback
  const refs = (Array.isArray(impact.references) ? impact.references : [])
    .filter((r) => Number(r?.count || 0) > 0)
  const refText = refs.length ? refs.map((r) => `${r.kind}: ${r.count}`).join('; ') : '未发现引用'
  const action = impact.recommended_action === 'archive' ? '归档' : '删除'
  const suffix = impact.recommended_action === 'archive'
    ? '确认归档只会从默认列表和召回中隐藏,不会清理相关引用。'
    : '确认删除会同步清理相关引用。'
  return `影响范围: ${refText}。建议操作: ${action}。${suffix}`
}

// 按 type 拉「该分类全部条目」,再按 ref 选中一条(复用 CodexView 的多端点读路径)。
// 注意不 catch 吞错:请求失败必须冒泡到调用方的 error 态,
// 否则失败被压成空列表 → 界面谎称「未找到该条目(可能已删除)」。
async function loadRows(nodeType) {
  if (nodeType === 'character') {
    const es = await api.entities()
    return es.filter((e) => e.kind === 'character')
  }
  if (nodeType === 'faction') return api.get('/factions')
  if (nodeType === 'item') return api.get('/items')
  if (nodeType === 'term') return api.get('/terms')
  if (nodeType === 'world_rule') return api.get('/world-rules')
  if (nodeType === 'promise') return api.promises()
  if (nodeType === 'motif') return api.motifs()
  return []
}

// 选中条目:角色用裸 id(local)匹配,其余用 name 匹配(与 /project-tree 的 ref 约定一致)。
function pickRow(nodeType, rows, ref) {
  if (nodeType === 'character') return rows.find((r) => localOf(r) === ref || r.id === `role:${ref}`)
  if (nodeType === 'promise' || nodeType === 'motif') return rows.find((r) => r.id === ref)
  return rows.find((r) => r.name === ref)
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

// ═══ 弧光锚编辑(M3):ghost/lie/truth/want/need + arc_type + private_agenda ═══
// 七键静态锚,存于 character 记录,经 PATCH /char-anchors 局部更新(不碰角色档案其它字段)。
const ARC_TYPES = [
  { v: 'positive', label: '正向成长(positive)' },
  { v: 'flat', label: '平稳弧(flat)' },
  { v: 'disillusionment', label: '幻灭(disillusionment)' },
  { v: 'fall', label: '坠落(fall)' },
  { v: 'corruption', label: '腐化(corruption)' },
]
// 锚文本键(不含 arc_type 下拉),渲染成一列小 textarea。
const ANCHOR_TEXT = [
  ['ghost', '心魔 / 前史创伤(Ghost)', '过去某件事在角色心里留下的阴影'],
  ['lie', '错误信念(Lie)', '角色因创伤而信奉、需被击穿的谎言'],
  ['truth', '真相(Truth)', '角色最终须领悟的、与 Lie 相对的真相'],
  ['want', '表层渴望(Want)', '角色自以为想要的外在目标'],
  ['need', '深层需求(Need)', '角色真正需要、往往与 Want 冲突的东西'],
]

// lie_belief 历史小曲线:纯 SVG 折线,无图表库。数据优先取 /char-states 的 lie_belief 实测,
// 无实测则回退 arc_plan 的 lie_belief_target 计划轨迹;不足 2 点不渲染(与"无数据不渲染"一致)。
function LieBeliefSpark({ states, arcPlan }) {
  const actual = (states || [])
    .filter((s) => typeof s.lie_belief === 'number')
    .map((s) => ({ chapter: s.chapter, value: s.lie_belief }))
  const planned = (arcPlan || [])
    .filter((b) => typeof b.lie_belief_target === 'number')
    .map((b) => ({ chapter: b.target_chapter, value: b.lie_belief_target }))
  const useActual = actual.length >= 2
  const pts = (useActual ? actual : planned).slice().sort((a, b) => a.chapter - b.chapter)
  if (pts.length < 2) return null   // 无数据不渲染

  const W = 260, H = 72, PX = 6, PY = 8
  const chs = pts.map((p) => p.chapter)
  const cMin = Math.min(...chs), cMax = Math.max(...chs)
  const span = cMax - cMin || 1
  const x = (c) => PX + ((c - cMin) / span) * (W - PX * 2)
  const y = (v) => PY + (1 - Math.max(0, Math.min(100, v)) / 100) * (H - PY * 2)
  const line = pts.map((p) => `${x(p.chapter).toFixed(1)},${y(p.value).toFixed(1)}`).join(' ')
  return (
    <div className="mt-4">
      <div className="flex items-center gap-2 mb-1.5">
        <span className="text-meta text-faint uppercase tracking-wider">信奉度曲线(Lie belief)</span>
        <span className="text-meta text-faint/60">{useActual ? '实测' : '计划轨迹'} · {pts.length} 点</span>
      </div>
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full max-w-[280px]" preserveAspectRatio="xMidYMid meet" role="img" aria-label="信奉度曲线">
        {/* 0 / 50 / 100 三条参考线 */}
        {[0, 50, 100].map((v) => (
          <line key={v} x1={PX} x2={W - PX} y1={y(v)} y2={y(v)} className="stroke-line" strokeWidth="0.5" strokeDasharray="2 3" />
        ))}
        <polyline points={line} fill="none" className="stroke-brand" strokeWidth="1.5" strokeLinejoin="round" strokeLinecap="round" />
        {pts.map((p, i) => (
          <g key={i}>
            <circle cx={x(p.chapter)} cy={y(p.value)} r="2.4" className="fill-brand" />
            <text x={x(p.chapter)} y={y(p.value) - 4} textAnchor="middle" className="fill-faint" fontSize="6">{p.value}</text>
          </g>
        ))}
        {/* 章号轴:首末标注 */}
        <text x={x(cMin)} y={H - 1} textAnchor="start" className="fill-faint/70" fontSize="6">第{cMin}章</text>
        <text x={x(cMax)} y={H - 1} textAnchor="end" className="fill-faint/70" fontSize="6">第{cMax}章</text>
      </svg>
    </div>
  )
}

// 弧光锚:只读展示 + 主编写入(与档案字段同一政策,禁止常驻表单墙)
function CharArcAnchors({ characterId, characterName }) {
  const [anchors, setAnchors] = useState(null)   // null=加载中
  const [arcPlan, setArcPlan] = useState([])
  const [states, setStates] = useState([])

  useEffect(() => {
    setAnchors(null)
    api.charAnchors(characterId)
      .then((r) => {
        setAnchors(r?.anchors || {})
        setArcPlan(Array.isArray(r?.arc_plan) ? r.arc_plan : [])
      })
      .catch(() => { setAnchors({}); setArcPlan([]) })
    api.charStates(characterId).then((s) => setStates(Array.isArray(s) ? s : [])).catch(() => setStates([]))
  }, [characterId])

  if (anchors === null) return <div className="mt-6 text-f12 text-faint/50">弧光锚加载中…</div>
  const name = characterName || String(characterId || '').split(':').pop()
  const arcTypeLabel = ARC_TYPES.find((t) => t.v === anchors.arc_type)?.label || anchors.arc_type
  return (
    <div className="mt-6 pt-4 border-t border-line" data-testid="char-arc-anchors">
      <SectionTitle icon={GitBranch} right={
        <button type="button" data-testid="arc-ask-chief"
          onClick={() => seedChiefCodexWrite('chars', { id: characterId, name },
            '请更新弧光锚(ghost/lie/truth/want/need/arc_type/private_agenda)与弧光里程碑;用 PATCH 锚与节拍写工具提交审批。')}
          className="text-meta text-brand hover:text-brand/80 cursor-pointer normal-case tracking-normal font-normal">
          让主编写入弧光
        </button>
      }>弧光锚 · 角色内核</SectionTitle>
      <div className="space-y-0.5">
        {ANCHOR_TEXT.map(([k, label]) => (
          <ReadOnlyText key={k} label={label} value={anchors?.[k]} emptyHint="—" entityLabel={name || characterId} fieldKey={k} />
        ))}
        <ReadOnlyText label="弧型(Arc type)" value={arcTypeLabel} emptyHint="—" entityLabel={name || characterId} fieldKey="arc_type" />
        <ReadOnlyText label="私密日程(Private agenda)" value={anchors?.private_agenda} emptyHint="—" entityLabel={name || characterId} fieldKey="private_agenda" />
      </div>

      <div className="mt-5">
        <div className="flex items-center gap-2 mb-2">
          <span className="text-meta text-faint uppercase tracking-wider">弧光里程碑</span>
          <span className="text-meta text-faint/50">{arcPlan.length} 个节拍</span>
        </div>
        {arcPlan.length === 0 ? <Empty>尚无里程碑——由主编规划弧光行进(目标章 + 信奉度)</Empty> : (
          <div className="space-y-1">
            {arcPlan.map((b) => (
              <div key={b.id} className="flex items-center gap-2 py-1 px-1.5 rounded hover:bg-soft/40">
                <span className="text-meta text-faint tnum shrink-0">第{b.target_chapter}章</span>
                <span className="text-f13 text-ink min-w-0 truncate">{b.beat_name}</span>
                {typeof b.lie_belief_target === 'number' && <span className="text-meta text-brand shrink-0">信奉度→{b.lie_belief_target}</span>}
                {b.trigger_event && <span className="text-meta text-faint/60 truncate">· {b.trigger_event}</span>}
              </div>
            ))}
          </div>
        )}
      </div>

      <LieBeliefSpark states={states} arcPlan={arcPlan} />
    </div>
  )
}

// ═══ 声音演变消费端(P1-11 后半环):voice_profile 声线指纹 + open voice_evolution_flag ═══
// 后端只有三个端点:GET /voice-flags(全书 open,前端按角色过滤)、POST /voice-flags/{id}/resolve、
// POST /voice-flags/fold(把该角色 open flags 折进 voice_profile,LLM 演化,返回演化后 profile)。
// 注意 无 GET voice_profile 端点——初次加载只能拉 flags;声线指纹在「一键折叠」成功后由 fold 响应展示。
// characterId=row.id(带前缀 role:xxx); characterName=row.name(裸名,兼容历史 flag)。
// 声音演变:只读列表 + 主编折叠/处理(禁止详情页直写)
function CharVoice({ characterId, characterName, refreshKey = 0 }) {
  const [flags, setFlags] = useState(null)   // null=加载中

  const mine = (f) => {
    const c = f?.character
    return c === characterId || c === characterName
      || c === (characterId || '').split(':').slice(1).join(':')
  }
  useEffect(() => {
    setFlags(null)
    api.voiceFlags()
      .then((all) => setFlags((Array.isArray(all) ? all : []).filter(mine)))
      .catch(() => setFlags([]))
  }, [characterId, characterName, refreshKey])  // eslint-disable-line react-hooks/exhaustive-deps

  if (flags === null) return <div className="mt-6 text-f12 text-faint/50">声音演变加载中…</div>
  const openCount = flags.length
  const name = characterName || String(characterId || '').split(':').pop()

  return (
    <div className="mt-6 pt-4 border-t border-line" data-testid="char-voice">
      <SectionTitle icon={AudioLines} right={
        <span className="inline-flex items-center gap-2 normal-case tracking-normal font-normal">
          {openCount > 0 && <span className="text-meta text-faint">{openCount} 条待折叠</span>}
          <button type="button" data-testid="voice-ask-chief"
            onClick={() => seedChiefCodexWrite('chars', { id: characterId, name },
              openCount > 0
                ? `请处理声音演变:当前有 ${openCount} 条 open flag,可一键折叠进 voice_profile 或标记已处理;用 voice-flags 写工具提交审批。`
                : '请查阅并维护该角色声线指纹 / 声音演变记录;用对应写工具提交审批。')}
            className="text-meta text-brand hover:text-brand/80 cursor-pointer">
            让主编处理声音
          </button>
        </span>
      }>声音演变 · 角色声线</SectionTitle>

      {openCount > 0 ? (
        <div className="space-y-1.5">
          {flags.map((f) => (
            <div key={f.id} className="flex items-start gap-2 py-1.5 px-1.5 rounded hover:bg-soft/40">
              <span className="text-meta text-faint tnum shrink-0 mt-0.5">第{f.trigger_chapter}章</span>
              <span className="text-f13 text-ink min-w-0 flex-1 leading-relaxed">{f.reason}</span>
            </div>
          ))}
        </div>
      ) : (
        <Empty>暂无声音演变记录——写作中标记「影响声音」的角色质变会在此累积,由主编折叠进声线指纹。</Empty>
      )}
    </div>
  )
}

// ═══ 命题详情(批D 件1):限知引擎核心素材的独立详情块 ═══
// 注意 GET /facts 有损:私密命题 value 被后端屏蔽为 null(_facts),且不回 valid_from/valid_to/leak_markers,
// 亦无单条 reveal 端点 —— 故此处【不做整行 PATCH 回写】(会把私密值 null 掉/抹掉 leak_markers,同 F-1/F-2 坑),
// 改为时态正确的三动作:超越(改值·保历史)/ 让 knower 遗忘(知识边)/ 删除。全字段生产在「+ 新建命题」。
const FACT_SCAN_CHAPTER = 100000

// 命题详情:只读展示 + 写入走主编(与设定档案政策一致)。删除仍可本地确认(生命周期门控)。
export function PropositionDetail({ node, onDeleted }) {
  const [row, setRow] = useState(null)
  const [loading, setLoading] = useState(true)
  const [loadErr, setLoadErr] = useState('')
  const [delOpen, setDelOpen] = useState(false)
  const [delLoading, setDelLoading] = useState(false)
  const [deleteImpact, setDeleteImpact] = useState(null)

  const reload = () => {
    setLoading(true); setLoadErr('')
    api.facts(FACT_SCAN_CHAPTER)
      .then((rows) => {
        const r = (rows || []).find((x) => x.id === `fact:${node.ref}`
          || String(x.id || '').split(':').pop() === node.ref)
        setRow(r || null); setLoading(false)
      })
      .catch((e) => { setRow(null); setLoadErr(e?.body?.detail || e?.message || '加载失败'); setLoading(false) })
  }
  useEffect(() => { setDeleteImpact(null); reload() }, [node?.id])

  const openDelete = async () => {
    if (delLoading) return
    setDelLoading(true)
    try {
      const impact = await api.objectImpact('fact', node.ref)
      setDeleteImpact(impact || null)
      setDelOpen(true)
    } catch (e) {
      showToast(e?.body?.detail || e?.message || '读取删除影响失败', { tone: 'danger' })
    } finally {
      setDelLoading(false)
    }
  }

  const doDelete = async () => {
    const shouldArchive = deleteImpact?.recommended_action === 'archive'
    try {
      if (shouldArchive) await api.archiveObject('fact', node.ref)
      else await api.deleteObject('fact', node.ref, deleteImpact?.confirm_impact_token || '')
      onDeleted?.()
    } catch (e) { showToast(e?.body?.detail || e?.message || (shouldArchive ? '归档失败' : '删除失败'), { tone: 'danger' }) }
  }

  if (loading) return <div className="flex items-center justify-center py-12 text-faint"><Loader2 size={20} className="animate-spin mr-2" />加载命题…</div>
  if (loadErr) return (
    <div className="p-4">
      <AsyncState state="error" title="命题加载失败" message={loadErr} onRetry={reload} />
    </div>
  )
  if (!row) return <div className="p-6 text-f13 text-faint">未找到该命题(可能已被超越或删除)。项目树只投影仍处开区间的命题。</div>

  const entLocal = String(row.entity || '').split(':').pop() || '—'
  const seedBase = { name: `${entLocal}·${row.attribute || ''}`, id: row.id, text: row.value }

  return (
    <div className="h-full overflow-y-auto bg-canvas" data-testid="proposition-detail">
      <div className="max-w-2xl mx-auto px-5 py-4">
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2 py-1" data-testid="proposition-readonly-banner">
          <span className="text-meta text-faint">只读检视 · 超越/遗忘走主编审批写</span>
          <button type="button" data-testid="proposition-ask-chief"
            onClick={() => seedChiefCodexWrite('facts', seedBase,
              `请处理命题「${entLocal}·${row.attribute || ''}」:可超越改值(保历史)或设置 knower 遗忘;用 s3_ 写工具提交审批。`)}
            className="inline-flex items-center gap-1 h-7 px-2.5 rounded-lg text-f12 bg-brand text-brandfg hover:opacity-90 cursor-pointer">
            让主编写入
          </button>
        </div>

        <SectionTitle icon={Boxes}>命题详情</SectionTitle>
        <div className="space-y-0.5 mt-1">
          <ReadOnlyText label="主体" value={entLocal} entityLabel={`${entLocal}·${row.attribute || ''}`} fieldKey="entity" />
          <ReadOnlyText label="属性" value={row.attribute} entityLabel={`${entLocal}·${row.attribute || ''}`} fieldKey="attribute" />
          <ReadOnlyText
            label="值"
            value={row.is_secret ? null : row.value}
            emptyHint={row.is_secret ? '私密 · 值对读者屏蔽(限知)' : '—'}
            entityLabel={`${entLocal}·${row.attribute || ''}`}
            fieldKey="value"
            emptyAsk={!row.is_secret}
          />
          {row.is_secret && (
            <div className="py-1 text-f13 text-faint inline-flex items-center gap-1.5"><Lock size={13} />限知私密命题</div>
          )}
        </div>

        <div className="mt-5 pt-3 border-t border-line flex items-center gap-3 flex-wrap">
          <button type="button" data-testid="proposition-supersede-chief"
            onClick={() => seedChiefCodexWrite('facts', seedBase,
              `请超越命题「${entLocal}·${row.attribute || ''}」:关闭现开区间并自指定章写入新值(旧值封存)。`)}
            className="text-meta text-brand hover:text-brand/80 cursor-pointer inline-flex items-center gap-1">
            <History size={13} />让主编超越
          </button>
          <button type="button" data-testid="proposition-forget-chief"
            onClick={() => seedChiefCodexWrite('facts', seedBase,
              `请为命题「${entLocal}·${row.attribute || ''}」设置 knower 遗忘(默认 reader,指定 until_chapter)。`)}
            className="text-meta text-brand hover:text-brand/80 cursor-pointer inline-flex items-center gap-1">
            <EyeOff size={13} />让主编设遗忘
          </button>
          <button onClick={openDelete} disabled={delLoading} className="ml-auto text-f12 text-faint hover:text-danger cursor-pointer inline-flex items-center gap-1 transition-colors duration-150 disabled:opacity-40">
            {delLoading ? <Loader2 size={13} className="animate-spin" /> : <Trash2 size={13} />}删除命题
          </button>
        </div>
      </div>
      <ConfirmDialog
        open={delOpen}
        title={deleteImpact?.recommended_action === 'archive' ? '确认归档命题?' : '确认删除命题?'}
        body={lifecycleDeleteBody(deleteImpact, `将删除「${entLocal}·${row.attribute}」,此操作不可撤销。`)}
        danger={deleteImpact?.recommended_action !== 'archive'}
        confirmText={deleteImpact?.recommended_action === 'archive' ? '归档' : '删除'}
        onConfirm={doDelete}
        onClose={() => setDelOpen(false)}
      />
    </div>
  )
}

/**
 * 素材叶节点的中间栏详情卡:复用 CodexView 的 DetailView(角色档案/通用字段表/弧光/关系),
 * 自己负责按 node 懒加载该条全字段 + 落库回写。
 */

// 伏笔生命周期特化块(断头修复#21):埋→收状态一览 + 回收 + 线索增删——
// 入口 title 承诺"埋/收/线索/编辑",此前详情面只有埋/编辑,收与线索要绕道仪表盘。
// 伏笔生命周期:只读 + 主编(去 Card 外壳,与档案同一政策)
function PromiseLifecycle({ row }) {
  const clues = Array.isArray(row.clues) ? row.clues : []
  return (
    <div className="mt-6 pt-4 border-t border-line space-y-2" data-testid="promise-lifecycle">
      <div className="flex items-center gap-2 flex-wrap">
        <span className="text-meta text-faint uppercase tracking-wider">生命周期</span>
        <span className="text-f13 text-ink">
          埋第{row.setup_chapter ?? '—'}章
          {row.payoff_chapter != null ? ` → 收第${row.payoff_chapter}章` : ' → 待收'}
          {row.status ? ` (${row.status})` : ''}
        </span>
        <button
          type="button"
          data-testid="promise-ask-chief"
          onClick={() => seedChiefCodexWrite('promises', row,
            '请处理伏笔生命周期:标记回收(closed)与/或增删草蛇灰线线索;用对应写工具提交审批。')}
          className="ml-auto text-meta text-brand hover:text-brand/80 cursor-pointer"
        >
          让主编维护
        </button>
      </div>
      <div className="space-y-1">
        <div className="text-meta text-faint">草蛇灰线线索({clues.length})</div>
        {clues.length === 0 ? <Empty>尚无线索</Empty> : clues.map((c, i) => (
          <div key={i} className="flex items-center gap-2 text-f13 text-ink py-0.5 px-1 rounded hover:bg-soft/40">
            <span className="text-meta text-faint shrink-0">第{c.chapter ?? '?'}章</span>
            <span className="flex-1 min-w-0 truncate">{c.note || String(c)}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

// 物品状态:引导主编记录历史链(表单直填已禁用)
function ItemStateChange({ name }) {
  return (
    <div className="mt-6 pt-4 border-t border-line" data-testid="item-state-change">
      <div className="flex items-center gap-2 flex-wrap">
        <span className="text-meta text-faint uppercase tracking-wider">状态变更</span>
        <span className="text-meta text-faint">入历史链 · 禁止表单直填</span>
        <button
          type="button"
          data-testid="item-state-ask-chief"
          onClick={() => seedChiefCodexWrite('items', { name },
            `请记录物品「${name}」状态变更(active/lost/destroyed/unknown)+ 发生章与缘由,写入 state_history。`)}
          className="ml-auto text-meta text-brand hover:text-brand/80 cursor-pointer"
        >
          让主编记录
        </button>
      </div>
    </div>
  )
}

// ═══ FactionRelations(CX-Task 7):势力详情页「关系」区 ═══
// 通用实体关系表(entity_relation,CX-Task 5)——与角色专属的 DynamicRelations
// (character_relation,CodexView.jsx)是两套独立后端表,互不影响。核心诉求(作者原话):
// "秘会看天龙座 vs 天龙座看秘会,而且对方的认知可能是错的"——故双向并排展示
// perception_a/perception_b,不对哪边"更真实"做任何判断。truth 字段后端默认掩码
// (GET reveal_secret 缺省 false)——本组件不提供 reveal 入口,原样显示后端返回值
// (掩码时就是掩码占位符,与其余 secret 字段的既有处理方式一致,不额外发明"解锁"通道)。
// 势力关系:只读 ghost 行 + 主编写入(与角色关系同皮)
function FactionRelations({ name }) {
  const myRef = `faction:${name}`
  const [rows, setRows] = useState(null)   // null=加载中

  useEffect(() => {
    setRows(null)
    api.entityRelations(myRef)
      .then((r) => setRows(Array.isArray(r) ? r : []))
      .catch(() => setRows([]))
  }, [name])  // eslint-disable-line react-hooks/exhaustive-deps

  if (rows === null) return <div className="mt-6 pt-4 border-t border-line text-f12 text-faint/50">关系加载中…</div>

  return (
    <div className="mt-6 pt-4 border-t border-line" data-testid="faction-relations">
      <SectionTitle icon={Heart} right={
        <span className="inline-flex items-center gap-2 normal-case tracking-normal font-normal">
          <span className="text-meta text-faint tnum">{rows.length}条</span>
          <button type="button" data-testid="faction-rel-ask-chief"
            onClick={() => seedChiefCodexWrite('factions', { name },
              '请维护势力关系(entity_relation):对方实体、关系类型、双方认知与建立章;用对应写工具提交审批。')}
            className="text-meta text-brand hover:text-brand/80 cursor-pointer inline-flex items-center gap-0.5">
            <Plus size={12} />让主编维护关系
          </button>
        </span>
      }>关系 · 双方认知</SectionTitle>

      {rows.length === 0 ? (
        <Empty>尚无关系记录——势力/角色对彼此的认知由主编登记(允许双方认知不对称甚至相互矛盾)。</Empty>
      ) : (
        <div className="space-y-1">
          {rows.map((r) => {
            const mine = r.a === myRef
            const otherRef = mine ? r.b : r.a
            const myPerception = mine ? r.perception_a : r.perception_b
            const otherPerception = mine ? r.perception_b : r.perception_a
            return (
              <div key={`${r.a}->${r.b}->${r.relation_type}`} className="py-2 px-1.5 rounded hover:bg-soft/40 transition-colors">
                <div className="flex items-center gap-2 mb-1 flex-wrap">
                  <span className="text-f13 font-medium text-ink">{otherRef}</span>
                  <Tag tone="brand">{r.relation_type}</Tag>
                  {r.since_chapter != null && <span className="text-meta text-faint">第{r.since_chapter}章建立</span>}
                  {r.until_chapter != null && <span className="text-meta text-danger">第{r.until_chapter}章结束</span>}
                </div>
                <div className="grid grid-cols-2 gap-3 text-f13">
                  <div>
                    <div className="text-meta text-faint uppercase tracking-wider mb-0.5">我方认知</div>
                    <div className="text-ink leading-relaxed">{myPerception || '—'}</div>
                  </div>
                  <div>
                    <div className="text-meta text-faint uppercase tracking-wider mb-0.5">对方认知(可能不对称/错误)</div>
                    <div className="text-ink leading-relaxed">{otherPerception || '—'}</div>
                  </div>
                </div>
                {r.truth && (
                  <div className="mt-1.5 pt-1.5 border-t border-line/50 text-meta text-faint inline-flex items-center gap-1">
                    <Lock size={10} />真相(主编独知):{r.truth}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

export function CodexDetail({ node, onDeleted }) {
  const [row, setRow] = useState(null)
  const [loading, setLoading] = useState(true)
  const [loadErr, setLoadErr] = useState('')
  const [delOpen, setDelOpen] = useState(false)
  const [delLoading, setDelLoading] = useState(false)
  const [deleteImpact, setDeleteImpact] = useState(null)
  const detailType = TYPE_MAP[node?.type]

  // 已有档案只读 + 主编种子;字段 REST 写路径已拆除(Policy 1A)。
  const reload = () => {
    if (!node || !detailType) { setLoading(false); return }
    setLoading(true); setLoadErr('')
    loadRows(node.type)
      .then((rows) => {
        setRow(pickRow(node.type, rows, node.ref) || null)
        setLoading(false)
      })
      .catch((e) => { setRow(null); setLoadErr(e?.body?.detail || e?.message || '加载失败'); setLoading(false) })
  }
  useEffect(() => { setDeleteImpact(null); reload() }, [node?.id]) // eslint-disable-line react-hooks/exhaustive-deps

  if (!detailType) return <div className="p-6 text-f13 text-faint">未知设定类型:{node?.type}</div>
  if (loading) return <div className="flex items-center justify-center py-12 text-faint"><Loader2 size={20} className="animate-spin mr-2" />加载中…</div>
  if (loadErr) return (
    <div className="p-4">
      <AsyncState state="error" title="设定加载失败" message={loadErr} onRetry={reload} />
    </div>
  )
  if (!row) return <div className="p-6 text-f13 text-faint">未找到该条目(可能已删除)。</div>

  const openDelete = async () => {
    if (detailType !== 'chars') { setDelOpen(true); return }
    if (delLoading) return
    setDelLoading(true)
    try {
      const impact = await api.objectImpact('role', localOf(row))
      setDeleteImpact(impact || null)
      setDelOpen(true)
    } catch (e) {
      showToast(e?.body?.detail || e?.message || '读取删除影响失败', { tone: 'danger' })
    } finally {
      setDelLoading(false)
    }
  }

  const doDelete = async () => {
    try {
      if (detailType === 'chars') {
        if (deleteImpact?.recommended_action === 'archive') await api.archiveObject('role', localOf(row))
        else await api.deleteObject('role', localOf(row), deleteImpact?.confirm_impact_token || '')
      }
      else await remove(detailType, row)
      onDeleted?.()
    }
    catch (e) { showToast(e?.body?.detail || e?.message || (deleteImpact?.recommended_action === 'archive' ? '归档失败' : '删除失败'), { tone: 'danger' }) }
  }

  return (
    <div className="h-full overflow-y-auto bg-canvas">
      <div className="max-w-2xl mx-auto px-5 py-4">
        <DetailView
          type={detailType}
          row={row}
          isNew={false}
          onBack={null}
          onUpdate={undefined}
          onDelete={openDelete}
        />
        {/* 伏笔专属(断头修复#21):收 + 草蛇灰线线索 */}
        {detailType === 'promises' && row?.id && <PromiseLifecycle row={row} />}
        {detailType === 'items' && row?.name && <ItemStateChange name={row.name} />}
        {detailType === 'factions' && row?.name && <FactionRelations name={row.name} />}
        {detailType === 'chars' && row?.id && <CharArcAnchors characterId={row.id} characterName={row.name} />}
        {detailType === 'chars' && row?.id && <CharVoice characterId={row.id} characterName={row.name} />}
      </div>
      <ConfirmDialog
        open={delOpen}
        title="确认删除?"
        body={detailType === 'chars'
          ? lifecycleDeleteBody(deleteImpact, `将删除「${row.name || row.text || node.ref}」,此操作不可撤销。`)
          : `将删除「${row.name || row.text || node.ref}」,此操作不可撤销。`}
        danger={detailType !== 'chars' || deleteImpact?.recommended_action !== 'archive'}
        confirmText={detailType === 'chars' && deleteImpact?.recommended_action === 'archive' ? '归档' : '删除'}
        onConfirm={doDelete}
        onClose={() => setDelOpen(false)}
      />
    </div>
  )
}
