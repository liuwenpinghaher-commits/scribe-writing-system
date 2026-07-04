import { useEffect, useState } from 'react'
import { Loader2, GitBranch, Trash2, Plus, AudioLines, Check, X, Boxes, Lock, History, EyeOff } from 'lucide-react'
import { api } from './api'
import { DetailView, stripSecretMask } from './views/CodexView'
import { ConfirmDialog } from './ui/Dialog.jsx'
import { showToast } from './ui/Toast'
import { Btn, SectionTitle, Empty } from './ui'

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
  // 防线2(API 边界):掩码占位符绝不回写——把值等于 `🔒 私密` 的字段剔除,
  // 避免整行回传销毁真实私密(角色 backstory / 势力 private_operation,F-1/F-2)。
  const payload = stripSecretMask(updated)
  if (detailType === 'chars') await api.editChar(localOf(payload), payload)
  else if (detailType === 'rules') await api.post('/world-rules', payload)
  else if (detailType === 'factions') await api.post('/factions', payload)
  else if (detailType === 'items') await api.post('/items', payload)
  else if (detailType === 'terms') await api.post('/terms', payload)
  else if (detailType === 'promises') await api.editPromise(payload.id, payload)
  else if (detailType === 'motifs') await api.editMotif(payload.id, payload)
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
        <span className="text-f11 text-faint uppercase tracking-wider">信奉度曲线(Lie belief)</span>
        <span className="text-f10 text-faint/60">{useActual ? '实测' : '计划轨迹'} · {pts.length} 点</span>
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

function CharArcAnchors({ characterId }) {
  const [anchors, setAnchors] = useState(null)   // null=加载中
  const [arcPlan, setArcPlan] = useState([])
  const [states, setStates] = useState([])
  const [form, setForm] = useState(null)
  const [dirty, setDirty] = useState(false)
  const [saving, setSaving] = useState(false)
  const [beat, setBeat] = useState(null)   // 新增里程碑草稿 或 null
  const [beatErr, setBeatErr] = useState('')

  const reload = () => {
    api.charAnchors(characterId)
      .then((r) => { const a = r?.anchors || {}; setAnchors(a); setForm(a); setArcPlan(Array.isArray(r?.arc_plan) ? r.arc_plan : []); setDirty(false) })
      .catch(() => { setAnchors({}); setForm({}); setArcPlan([]) })
    api.charStates(characterId).then((s) => setStates(Array.isArray(s) ? s : [])).catch(() => setStates([]))
  }
  useEffect(() => { setAnchors(null); reload() }, [characterId])

  const setField = (k, v) => { setForm((f) => ({ ...f, [k]: v })); setDirty(true) }
  const save = async () => {
    setSaving(true)
    try {
      // 只回传锚七键(白名单),空串保留为清空;后端 set_char_anchors 只写传入键。
      const payload = {}
      for (const k of ['ghost', 'lie', 'truth', 'want', 'need', 'arc_type', 'private_agenda']) payload[k] = form?.[k] ?? ''
      await api.patchCharAnchors(characterId, payload)
      setAnchors(form); setDirty(false)
      showToast('弧光锚已保存', { tone: 'ok' })
    } catch (e) {
      showToast(e?.body?.detail || e?.message || '弧光锚保存失败', { tone: 'danger' })
    } finally { setSaving(false) }
  }

  const addBeat = async () => {
    const b = beat
    if (!b?.beat_name?.trim() || b.target_chapter === '' || b.target_chapter == null) { setBeatErr('里程碑名与目标章必填'); return }
    const lbt = b.lie_belief_target === '' || b.lie_belief_target == null ? null : Number(b.lie_belief_target)
    if (lbt != null && (Number.isNaN(lbt) || lbt < 0 || lbt > 100)) { setBeatErr('信奉度目标须为 0-100'); return }
    try {
      await api.postArcBeat({ character_id: characterId, beat_name: b.beat_name.trim(), target_chapter: Number(b.target_chapter), lie_belief_target: lbt, trigger_event: b.trigger_event || '' })
      setBeat(null); setBeatErr(''); reload()
    } catch (e) { setBeatErr(e?.body?.detail || e?.message || '里程碑保存失败') }
  }
  const delBeat = async (id) => {
    try { await api.delArcBeat(id); reload() }
    catch (e) { showToast(e?.body?.detail || e?.message || '里程碑删除失败', { tone: 'danger' }) }
  }

  if (anchors === null) return <div className="mt-6 text-f12 text-faint/50">弧光锚加载中…</div>
  const ta = 'w-full rounded-md border border-line bg-canvas px-2.5 py-1.5 text-f13 text-ink leading-relaxed outline-none focus:border-brand resize-y'
  const inp = 'h-8 rounded-md border border-line bg-canvas px-2 text-f12 text-ink outline-none focus:border-brand'
  return (
    <div className="mt-6 pt-4 border-t border-line">
      <SectionTitle icon={GitBranch}>弧光锚 · 角色内核</SectionTitle>
      <div className="space-y-2.5">
        {ANCHOR_TEXT.map(([k, label, ph]) => (
          <div key={k}>
            <div className="text-f11 text-faint uppercase tracking-wider mb-0.5">{label}</div>
            <textarea rows={2} value={form?.[k] ?? ''} onChange={(e) => setField(k, e.target.value)} placeholder={ph} className={ta} />
          </div>
        ))}
        <div>
          <div className="text-f11 text-faint uppercase tracking-wider mb-0.5">弧型(Arc type)</div>
          <select value={form?.arc_type ?? ''} onChange={(e) => setField('arc_type', e.target.value)}
            className="w-full h-9 rounded-md border border-line bg-canvas px-2.5 text-f13 text-ink outline-none focus:border-brand cursor-pointer">
            <option value="">—</option>
            {ARC_TYPES.map((t) => <option key={t.v} value={t.v}>{t.label}</option>)}
          </select>
        </div>
        <div>
          <div className="text-f11 text-faint uppercase tracking-wider mb-0.5">私密日程(Private agenda)</div>
          <textarea rows={2} value={form?.private_agenda ?? ''} onChange={(e) => setField('private_agenda', e.target.value)}
            placeholder="角色背地里在推进的目标(喂『待激活角色』心跳)" className={ta} />
        </div>
      </div>
      <div className="mt-3 flex items-center gap-2">
        <Btn variant="primary" size="sm" onClick={save} disabled={!dirty || saving}>
          {saving && <Loader2 size={13} className="animate-spin" />}保存弧光锚
        </Btn>
        {dirty && <span className="text-f11 text-faint">有未保存改动</span>}
      </div>

      {/* 弧光里程碑(arc_plan):目标章 + 该拍应到达的信奉度 */}
      <div className="mt-5">
        <div className="flex items-center gap-2 mb-2">
          <span className="text-f11 text-faint uppercase tracking-wider">弧光里程碑</span>
          <span className="text-f11 text-faint/50">{arcPlan.length} 个节拍</span>
          {!beat && <button onClick={() => { setBeat({ beat_name: '', target_chapter: '', lie_belief_target: '', trigger_event: '' }); setBeatErr('') }}
            className="ml-auto text-f11 text-brand hover:text-brand/80 cursor-pointer inline-flex items-center gap-0.5"><Plus size={12} />加节拍</button>}
        </div>
        {beat && (
          <div className="mb-3 p-2.5 rounded-lg border border-brand/30 bg-brand/[0.02] space-y-1.5">
            <div className="flex gap-1.5">
              <input value={beat.beat_name} onChange={(e) => setBeat({ ...beat, beat_name: e.target.value })} placeholder="节拍名(如:识破谎言)" className={`flex-1 ${inp}`} />
              <input type="number" value={beat.target_chapter} onChange={(e) => setBeat({ ...beat, target_chapter: e.target.value })} placeholder="目标章" className={`w-20 ${inp}`} />
            </div>
            <div className="flex gap-1.5">
              <input type="number" value={beat.lie_belief_target} onChange={(e) => setBeat({ ...beat, lie_belief_target: e.target.value })} placeholder="信奉度目标 0-100(可空)" className={`w-40 ${inp}`} />
              <input value={beat.trigger_event} onChange={(e) => setBeat({ ...beat, trigger_event: e.target.value })} placeholder="触发事件(可空)" className={`flex-1 ${inp}`} />
            </div>
            {beatErr && <div className="text-f11 text-danger">{beatErr}</div>}
            <div className="flex gap-2">
              <Btn variant="primary" size="xs" onClick={addBeat}>保存节拍</Btn>
              <Btn variant="ghost" size="xs" onClick={() => { setBeat(null); setBeatErr('') }}>取消</Btn>
            </div>
          </div>
        )}
        {arcPlan.length === 0 ? <Empty>尚无里程碑——加节拍规划弧光行进(目标章 + 信奉度)</Empty> : (
          <div className="space-y-1">
            {arcPlan.map((b) => (
              <div key={b.id} className="group flex items-center gap-2 py-1 px-1.5 rounded hover:bg-soft/40">
                <span className="text-f11 text-faint tnum shrink-0">第{b.target_chapter}章</span>
                <span className="text-f13 text-ink min-w-0 truncate">{b.beat_name}</span>
                {typeof b.lie_belief_target === 'number' && <span className="text-f10 text-brand shrink-0">信奉度→{b.lie_belief_target}</span>}
                {b.trigger_event && <span className="text-f11 text-faint/60 truncate">· {b.trigger_event}</span>}
                <button onClick={() => delBeat(b.id)} className="ml-auto opacity-0 group-hover:opacity-100 text-faint hover:text-danger cursor-pointer transition-opacity" title="删除节拍"><Trash2 size={12} /></button>
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
// ⚠ 无 GET voice_profile 端点——初次加载只能拉 flags;声线指纹在「一键折叠」成功后由 fold 响应展示。
// voice_profile 9 节字段(store.set_voice_profile):string 段直出,list 段逐行列。
const VOICE_FIELDS = [
  ['style_summary', '风格速写'],
  ['catchphrases', '口头禅'],
  ['sentence_patterns', '句式特征'],
  ['vocabulary_profile', '用词偏好'],
  ['tone_rules', '语气规则'],
  ['internal_monologue_style', '内心独白'],
  ['ooc_signals', 'OOC 破音信号'],
  ['reference_lines', '参考台词'],
]
const hasVoiceVal = (v) => Array.isArray(v) ? v.length > 0 : (v != null && String(v).trim() !== '')

// characterId=row.id(带前缀 role:xxx,fold 用它,后端 _split 依赖冒号);
// characterName=row.name(裸名,主书历史 flag 的 character 存的是裸名,过滤兼容两种约定)。
function CharVoice({ characterId, characterName }) {
  const [flags, setFlags] = useState(null)   // null=加载中
  const [profile, setProfile] = useState(null)   // fold 后展示;无 GET 端点故初次为 null
  const [folding, setFolding] = useState(false)
  const [resolvingId, setResolvingId] = useState('')

  // flag.character 可能是 role:单嫣(规范)或 单嫣(主书历史裸名),两者都归到本角色。
  const mine = (f) => {
    const c = f?.character
    return c === characterId || c === characterName
      || c === (characterId || '').split(':').slice(1).join(':')
  }
  const loadFlags = () => api.voiceFlags()
    .then((all) => setFlags((Array.isArray(all) ? all : []).filter(mine)))
    .catch(() => setFlags([]))
  useEffect(() => { setFlags(null); setProfile(null); loadFlags() }, [characterId])

  const resolveOne = async (fid) => {
    setResolvingId(fid)
    try {
      await api.resolveVoiceFlag(fid)
      setFlags((fs) => (fs || []).filter((f) => f.id !== fid))
      showToast('已标记该声音变化为已处理', { tone: 'ok' })
    } catch (e) {
      showToast(e?.body?.detail || e?.message || '处理失败', { tone: 'danger' })
    } finally { setResolvingId('') }
  }

  const fold = async () => {
    setFolding(true)
    try {
      const r = await api.foldVoiceFlags(characterId)   // 用带前缀 id,防 _split 500
      if (r?.folded > 0 && r?.profile) {
        setProfile(r.profile)
        showToast(`已折叠 ${r.folded} 条声音变化 → 声线指纹已更新`, { tone: 'ok' })
        loadFlags()   // 已 resolve,列表应清空
      } else if (r?.degraded) {
        showToast('声音演变解析失败(soft,未改动),请稍后重试', { tone: 'danger' })
      } else {
        showToast('无待折叠的声音变化', { tone: 'info' })
      }
    } catch (e) {
      showToast(e?.body?.detail || e?.message || '折叠失败', { tone: 'danger' })
    } finally { setFolding(false) }
  }

  if (flags === null) return <div className="mt-6 text-f12 text-faint/50">声音演变加载中…</div>
  const openCount = flags.length
  const profileFields = profile ? VOICE_FIELDS.filter(([k]) => hasVoiceVal(profile[k])) : []

  return (
    <div className="mt-6 pt-4 border-t border-line" data-testid="char-voice">
      <SectionTitle icon={AudioLines} right={openCount > 0 ? `${openCount} 条待折叠` : null}>
        声音演变 · 角色声线
      </SectionTitle>

      {/* 声线指纹(voice_profile):无独立 GET 端点,折叠成功后由 fold 响应展示 */}
      {profileFields.length > 0 && (
        <div className="mb-4 p-3 rounded-lg border border-line bg-soft/20 space-y-2" data-testid="voice-profile">
          <div className="flex items-center gap-2">
            <span className="text-f11 text-brand uppercase tracking-wider">声线指纹</span>
            {profile?.version != null && <span className="text-f10 text-faint/60">v{profile.version}</span>}
          </div>
          {profileFields.map(([k, label]) => (
            <div key={k}>
              <div className="text-f11 text-faint uppercase tracking-wider mb-0.5">{label}</div>
              {Array.isArray(profile[k])
                ? <ul className="list-disc pl-4 space-y-0.5">{profile[k].map((v, i) => <li key={i} className="text-f13 text-ink leading-relaxed">{typeof v === 'string' ? v : JSON.stringify(v)}</li>)}</ul>
                : <div className="text-f13 text-ink leading-relaxed">{profile[k]}</div>}
            </div>
          ))}
        </div>
      )}

      {/* 待折叠 flags 列表:哪章何事件触发的声音变化 */}
      {openCount > 0 ? (
        <div className="space-y-1.5">
          {flags.map((f) => (
            <div key={f.id} className="group flex items-start gap-2 py-1.5 px-2 rounded-lg hover:bg-soft/40">
              <span className="text-f11 text-faint tnum shrink-0 mt-0.5">第{f.trigger_chapter}章</span>
              <span className="text-f13 text-ink min-w-0 flex-1 leading-relaxed">{f.reason}</span>
              <button onClick={() => resolveOne(f.id)} disabled={resolvingId === f.id}
                className="shrink-0 opacity-0 group-hover:opacity-100 text-faint hover:text-danger cursor-pointer transition-opacity disabled:opacity-40"
                title="忽略此条(标记已处理,不折进声线)">
                {resolvingId === f.id ? <Loader2 size={13} className="animate-spin" /> : <X size={13} />}
              </button>
            </div>
          ))}
        </div>
      ) : profileFields.length === 0 ? (
        <Empty>暂无声音演变记录——写作中标记「影响声音」的角色质变会在此累积,可一键折叠进声线指纹。</Empty>
      ) : null}

      <div className="mt-3 flex items-center gap-2">
        <Btn variant="primary" size="sm" onClick={fold} disabled={folding || openCount === 0}>
          {folding ? <Loader2 size={13} className="animate-spin" /> : <Check size={13} />}
          一键折叠{openCount > 0 ? `(${openCount})` : ''}
        </Btn>
        {openCount > 0 && <span className="text-f11 text-faint">把待折叠变化演化进声线指纹</span>}
      </div>
    </div>
  )
}

// ═══ 命题详情(批D 件1):限知引擎核心素材的独立详情块 ═══
// ⚠ GET /facts 有损:私密命题 value 被后端屏蔽为 null(_facts),且不回 valid_from/valid_to/leak_markers,
// 亦无单条 reveal 端点 —— 故此处【不做整行 PATCH 回写】(会把私密值 null 掉/抹掉 leak_markers,同 F-1/F-2 坑),
// 改为时态正确的三动作:超越(改值·保历史)/ 让 knower 遗忘(知识边)/ 删除。全字段生产在「+ 新建命题」。
const FACT_SCAN_CHAPTER = 100000

export function PropositionDetail({ node, onChanged, onDeleted }) {
  const [row, setRow] = useState(null)
  const [loading, setLoading] = useState(true)
  const [panel, setPanel] = useState(null)          // 'supersede' | 'forget' | null
  const [sup, setSup] = useState({ value: '', since_chapter: '', secret: false })
  const [forget, setForget] = useState({ knower_id: 'reader', until_chapter: '' })
  const [busy, setBusy] = useState(false)
  const [delOpen, setDelOpen] = useState(false)

  const reload = () => {
    setLoading(true)
    api.facts(FACT_SCAN_CHAPTER)
      .then((rows) => {
        const r = (rows || []).find((x) => x.id === `fact:${node.ref}`
          || String(x.id || '').split(':').pop() === node.ref)
        setRow(r || null); setLoading(false)
      })
      .catch(() => { setRow(null); setLoading(false) })
  }
  useEffect(() => { setPanel(null); reload() }, [node?.id])

  const doSupersede = async () => {
    if (!sup.value.trim() || sup.since_chapter === '') { showToast('新值与生效章必填', { tone: 'danger' }); return }
    setBusy(true)
    try {
      await api.supersedeFact({ entity_id: row.entity, attribute: row.attribute,
        value: sup.value.trim(), since_chapter: Number(sup.since_chapter), secret: sup.secret })
      showToast('命题已超越(旧值封存于历史,新值生效)', { tone: 'ok' })
      setPanel(null); setSup({ value: '', since_chapter: '', secret: false })
      onChanged?.()   // 新命题 oid 已生成、旧命题转闭区间 → 通知重拉树
    } catch (e) { showToast(e?.body?.detail || e?.message || '超越失败', { tone: 'danger' }) }
    finally { setBusy(false) }
  }

  const doForget = async () => {
    if (forget.until_chapter === '' || !forget.knower_id.trim()) { showToast('knower 与失效章必填', { tone: 'danger' }); return }
    setBusy(true)
    try {
      await api.forgetKnowledge({ knower_id: forget.knower_id.trim(),
        proposition_id: `fact:${node.ref}`, until_chapter: Number(forget.until_chapter) })
      showToast('已设置遗忘(该 knower 自此章起不再知此命题)', { tone: 'ok' })
      setPanel(null); setForget({ knower_id: 'reader', until_chapter: '' })
    } catch (e) { showToast(e?.body?.detail || e?.message || '遗忘设置失败', { tone: 'danger' }) }
    finally { setBusy(false) }
  }

  const doDelete = async () => {
    try { await api.delFact(node.ref); onDeleted?.() }
    catch (e) { showToast(e?.body?.detail || e?.message || '删除失败', { tone: 'danger' }) }
  }

  if (loading) return <div className="flex items-center justify-center py-12 text-faint"><Loader2 size={20} className="animate-spin mr-2" />加载命题…</div>
  if (!row) return <div className="p-6 text-f13 text-faint">未找到该命题(可能已被超越或删除)。项目树只投影仍处开区间的命题。</div>

  const entLocal = String(row.entity || '').split(':').pop() || '—'
  const inp = 'h-8 rounded-md border border-line bg-canvas px-2 text-f12 text-ink outline-none focus:border-brand'
  const ta = 'w-full rounded-md border border-line bg-canvas px-2.5 py-1.5 text-f13 text-ink leading-relaxed outline-none focus:border-brand resize-y'

  return (
    <div className="h-full overflow-y-auto" data-testid="proposition-detail">
      <div className="max-w-2xl mx-auto px-6 py-5">
        <SectionTitle icon={Boxes}>命题详情</SectionTitle>
        <div className="space-y-2.5 mt-2">
          <div><div className="text-f11 text-faint uppercase tracking-wider mb-0.5">主体</div><div className="text-f14 text-ink prose-serif">{entLocal}</div></div>
          <div><div className="text-f11 text-faint uppercase tracking-wider mb-0.5">属性</div><div className="text-f13 text-ink">{row.attribute || '—'}</div></div>
          <div>
            <div className="text-f11 text-faint uppercase tracking-wider mb-0.5">值</div>
            {row.is_secret
              ? <div className="inline-flex items-center gap-1.5 text-f13 text-faint"><Lock size={13} />私密 · 值对读者屏蔽(限知)</div>
              : <div className="text-f13 text-ink leading-relaxed whitespace-pre-wrap">{row.value || '—'}</div>}
          </div>
        </div>

        {/* 动作条:超越改值 / 让读者遗忘 / 删除 */}
        <div className="mt-5 pt-3 border-t border-line flex items-center gap-2 flex-wrap">
          <Btn variant={panel === 'supersede' ? 'primary' : 'ghost'} size="sm" onClick={() => setPanel(panel === 'supersede' ? null : 'supersede')}><History size={13} />超越(改值)</Btn>
          <Btn variant={panel === 'forget' ? 'primary' : 'ghost'} size="sm" onClick={() => setPanel(panel === 'forget' ? null : 'forget')}><EyeOff size={13} />让读者遗忘</Btn>
          <button onClick={() => setDelOpen(true)} className="ml-auto text-f12 text-faint hover:text-danger cursor-pointer inline-flex items-center gap-1 transition-colors duration-150"><Trash2 size={13} />删除命题</button>
        </div>

        {panel === 'supersede' && (
          <div className="mt-3 p-3 rounded-lg border border-brand/30 bg-brand/[0.02] space-y-2">
            <div className="text-f11 text-faint">超越 = 关闭「{entLocal}·{row.attribute}」现开区间命题,自指定章起写入新值(旧值封存为历史,不破坏时态)。</div>
            <textarea value={sup.value} onChange={(e) => setSup({ ...sup, value: e.target.value })} rows={2} placeholder="新值…" className={ta} />
            <div className="flex items-center gap-2 flex-wrap">
              <input type="number" value={sup.since_chapter} onChange={(e) => setSup({ ...sup, since_chapter: e.target.value })} placeholder="自第几章生效" className={`w-32 ${inp}`} />
              <label className="flex items-center gap-1.5 text-f12 text-faint cursor-pointer select-none">
                <input type="checkbox" checked={sup.secret} onChange={(e) => setSup({ ...sup, secret: e.target.checked })} className="w-3.5 h-3.5 accent-brand cursor-pointer" />新值私密
              </label>
              <Btn variant="primary" size="sm" onClick={doSupersede} disabled={busy}>{busy && <Loader2 size={13} className="animate-spin" />}确认超越</Btn>
            </div>
          </div>
        )}

        {panel === 'forget' && (
          <div className="mt-3 p-3 rounded-lg border border-brand/30 bg-brand/[0.02] space-y-2">
            <div className="text-f11 text-faint">令某 knower(默认 reader 读者帧)自指定章起不再知晓此命题(设知识边 until_chapter)。</div>
            <div className="flex items-center gap-2 flex-wrap">
              <input value={forget.knower_id} onChange={(e) => setForget({ ...forget, knower_id: e.target.value })} placeholder="knower(reader 或 role:名)" className={`w-56 ${inp}`} />
              <input type="number" value={forget.until_chapter} onChange={(e) => setForget({ ...forget, until_chapter: e.target.value })} placeholder="自第几章失效" className={`w-32 ${inp}`} />
              <Btn variant="primary" size="sm" onClick={doForget} disabled={busy}>{busy && <Loader2 size={13} className="animate-spin" />}确认遗忘</Btn>
            </div>
          </div>
        )}
      </div>
      <ConfirmDialog open={delOpen} title="确认删除命题?" body={`将删除「${entLocal}·${row.attribute}」,此操作不可撤销。`} danger confirmText="删除" onConfirm={doDelete} onClose={() => setDelOpen(false)} />
    </div>
  )
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

  if (!detailType) return <div className="p-6 text-f13 text-faint">未知设定类型:{node?.type}</div>
  if (loading) return <div className="flex items-center justify-center py-12 text-faint"><Loader2 size={20} className="animate-spin mr-2" />加载中…</div>
  if (!row) return <div className="p-6 text-f13 text-faint">未找到该条目(可能已删除)。</div>

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
        {/* 角色专属:弧光锚编辑 + 里程碑 + 信奉度曲线(独立 PATCH /char-anchors,不碰角色档案回写) */}
        {detailType === 'chars' && row?.id && <CharArcAnchors characterId={row.id} />}
        {/* 角色专属:声音演变后半环(P1-11)——voice flags 列表 + 一键折叠 + 折叠后声线指纹(独立 /voice-flags/*,不碰角色档案) */}
        {detailType === 'chars' && row?.id && <CharVoice characterId={row.id} characterName={row.name} />}
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
