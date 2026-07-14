import { useEffect, useId, useRef, useState } from 'react'
import { Loader2, GitBranch, Trash2, Plus, AudioLines, Check, X, Boxes, Lock, History, EyeOff, Heart } from 'lucide-react'
import { api } from './api'
import { DetailView, stripSecretMask } from './views/CodexView'
import { ConfirmDialog } from './ui/Dialog.jsx'
import { AsyncState } from './ui/AsyncState.jsx'
import { showToast } from './ui/Toast'
import { Btn, SectionTitle, Empty, Tag } from './ui'
import { isChapterNum } from './lib/utils'

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

async function persist(detailType, updated) {
  // 防线2(API 边界):掩码占位符绝不回写——把值等于 SECRET_MASK 掩码的字段剔除,
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

function CharArcAnchors({ characterId }) {
  const uid = useId()   // 锚字段 label↔textarea/select 关联(此前 label 只是视觉文本)
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
  // 统一 ui.jsx 标准风格(rounded-lg/h-9/px-3,与 Input/Textarea 一致)
  const ta = 'w-full rounded-lg border border-line bg-canvas px-3 py-2 text-f13 text-ink leading-relaxed outline-none transition-colors focus:border-brand placeholder:text-faint/60 resize-y'
  const inp = 'h-9 rounded-lg border border-line bg-canvas px-3 text-f13 text-ink outline-none transition-colors focus:border-brand placeholder:text-faint/60'
  return (
    <div className="mt-6 pt-4 border-t border-line">
      <SectionTitle icon={GitBranch}>弧光锚 · 角色内核</SectionTitle>
      <div className="space-y-2.5">
        {ANCHOR_TEXT.map(([k, label, ph]) => (
          <div key={k}>
            <label htmlFor={`${uid}-${k}`} className="block text-meta text-faint uppercase tracking-wider mb-0.5">{label}</label>
            <textarea id={`${uid}-${k}`} rows={2} value={form?.[k] ?? ''} onChange={(e) => setField(k, e.target.value)} placeholder={ph} className={ta} />
          </div>
        ))}
        <div>
          <label htmlFor={`${uid}-arc-type`} className="block text-meta text-faint uppercase tracking-wider mb-0.5">弧型(Arc type)</label>
          <select id={`${uid}-arc-type`} value={form?.arc_type ?? ''} onChange={(e) => setField('arc_type', e.target.value)}
            className="w-full h-9 rounded-lg border border-line bg-canvas px-3 text-f13 text-ink outline-none transition-colors focus:border-brand cursor-pointer">
            <option value="">—</option>
            {ARC_TYPES.map((t) => <option key={t.v} value={t.v}>{t.label}</option>)}
          </select>
        </div>
        <div>
          <label htmlFor={`${uid}-private-agenda`} className="block text-meta text-faint uppercase tracking-wider mb-0.5">私密日程(Private agenda)</label>
          <textarea id={`${uid}-private-agenda`} rows={2} value={form?.private_agenda ?? ''} onChange={(e) => setField('private_agenda', e.target.value)}
            placeholder="角色背地里在推进的目标(喂『待激活角色』心跳)" className={ta} />
        </div>
      </div>
      <div className="mt-3 flex items-center gap-2">
        <Btn variant="primary" size="sm" onClick={save} disabled={!dirty || saving}>
          {saving && <Loader2 size={13} className="animate-spin" />}保存弧光锚
        </Btn>
        {dirty && <span className="text-meta text-faint">有未保存改动</span>}
      </div>

      {/* 弧光里程碑(arc_plan):目标章 + 该拍应到达的信奉度 */}
      <div className="mt-5">
        <div className="flex items-center gap-2 mb-2">
          <span className="text-meta text-faint uppercase tracking-wider">弧光里程碑</span>
          <span className="text-meta text-faint/50">{arcPlan.length} 个节拍</span>
          {!beat && <button onClick={() => { setBeat({ beat_name: '', target_chapter: '', lie_belief_target: '', trigger_event: '' }); setBeatErr('') }}
            className="ml-auto text-meta text-brand hover:text-brand/80 cursor-pointer inline-flex items-center gap-0.5"><Plus size={12} />加节拍</button>}
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
            {beatErr && <div className="text-meta text-danger">{beatErr}</div>}
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
                <span className="text-meta text-faint tnum shrink-0">第{b.target_chapter}章</span>
                <span className="text-f13 text-ink min-w-0 truncate">{b.beat_name}</span>
                {typeof b.lie_belief_target === 'number' && <span className="text-meta text-brand shrink-0">信奉度→{b.lie_belief_target}</span>}
                {b.trigger_event && <span className="text-meta text-faint/60 truncate">· {b.trigger_event}</span>}
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
// 注意 无 GET voice_profile 端点——初次加载只能拉 flags;声线指纹在「一键折叠」成功后由 fold 响应展示。
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
            <span className="text-meta text-brand uppercase tracking-wider">声线指纹</span>
            {profile?.version != null && <span className="text-meta text-faint/60">v{profile.version}</span>}
          </div>
          {profileFields.map(([k, label]) => (
            <div key={k}>
              <div className="text-meta text-faint uppercase tracking-wider mb-0.5">{label}</div>
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
              <span className="text-meta text-faint tnum shrink-0 mt-0.5">第{f.trigger_chapter}章</span>
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
        {openCount > 0 && <span className="text-meta text-faint">把待折叠变化演化进声线指纹</span>}
      </div>
    </div>
  )
}

// ═══ 命题详情(批D 件1):限知引擎核心素材的独立详情块 ═══
// 注意 GET /facts 有损:私密命题 value 被后端屏蔽为 null(_facts),且不回 valid_from/valid_to/leak_markers,
// 亦无单条 reveal 端点 —— 故此处【不做整行 PATCH 回写】(会把私密值 null 掉/抹掉 leak_markers,同 F-1/F-2 坑),
// 改为时态正确的三动作:超越(改值·保历史)/ 让 knower 遗忘(知识边)/ 删除。全字段生产在「+ 新建命题」。
const FACT_SCAN_CHAPTER = 100000

export function PropositionDetail({ node, onChanged, onDeleted }) {
  const [row, setRow] = useState(null)
  const [loading, setLoading] = useState(true)
  const [loadErr, setLoadErr] = useState('')
  const [panel, setPanel] = useState(null)          // 'supersede' | 'forget' | null
  const [sup, setSup] = useState({ value: '', since_chapter: '', secret: false })
  const [forget, setForget] = useState({ knower_id: 'reader', until_chapter: '' })
  const [busy, setBusy] = useState(false)
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
      // 请求失败 ≠ 命题被超越/删除:如实报错并给重试,不复用 not-found 文案
      .catch((e) => { setRow(null); setLoadErr(e?.body?.detail || e?.message || '加载失败'); setLoading(false) })
  }
  useEffect(() => { setPanel(null); setDeleteImpact(null); reload() }, [node?.id])

  const doSupersede = async () => {
    // 批D Minor①:生效章须 ≥1(旧 === '' 守卫漏拦 0/负数;valid_from 语义 1-based)。
    if (!sup.value.trim() || !isChapterNum(sup.since_chapter)) { showToast('新值必填,生效章须为 ≥1 的章号', { tone: 'danger' }); return }
    setBusy(true)
    try {
      await api.supersedeFact({ entity_id: row.entity, attribute: row.attribute,
        value: sup.value.trim(), since_chapter: Number(sup.since_chapter), secret: sup.secret })
      showToast('命题已超越(旧值封存于历史,新值生效)', { tone: 'ok' })
      setPanel(null); setSup({ value: '', since_chapter: '', secret: false })
      onChanged?.()   // 新命题 oid 已生成、旧命题转闭区间 → 通知重拉树
      // 批D Minor③:超越后本详情栏原会陈旧(node.id 未变,[node.id] effect 不重触)——
      // 补自身 reload:旧命题已转闭区间,facts(100000) 查不到 → 显示「已被超越」(诚实,非旧值残留)。
      reload()
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
  // 统一 ui.jsx 标准风格(rounded-lg/h-9/px-3,与 Input/Textarea 一致)
  const inp = 'h-9 rounded-lg border border-line bg-canvas px-3 text-f13 text-ink outline-none transition-colors focus:border-brand placeholder:text-faint/60'
  const ta = 'w-full rounded-lg border border-line bg-canvas px-3 py-2 text-f13 text-ink leading-relaxed outline-none transition-colors focus:border-brand placeholder:text-faint/60 resize-y'

  return (
    <div className="h-full overflow-y-auto" data-testid="proposition-detail">
      <div className="max-w-2xl mx-auto px-6 py-5">
        <SectionTitle icon={Boxes}>命题详情</SectionTitle>
        <div className="space-y-2.5 mt-2">
          <div><div className="text-meta text-faint uppercase tracking-wider mb-0.5">主体</div><div className="text-f14 text-ink prose-serif">{entLocal}</div></div>
          <div><div className="text-meta text-faint uppercase tracking-wider mb-0.5">属性</div><div className="text-f13 text-ink">{row.attribute || '—'}</div></div>
          <div>
            <div className="text-meta text-faint uppercase tracking-wider mb-0.5">值</div>
            {row.is_secret
              ? <div className="inline-flex items-center gap-1.5 text-f13 text-faint"><Lock size={13} />私密 · 值对读者屏蔽(限知)</div>
              : <div className="text-f13 text-ink leading-relaxed whitespace-pre-wrap">{row.value || '—'}</div>}
          </div>
        </div>

        {/* 动作条:超越改值 / 让读者遗忘 / 删除 */}
        <div className="mt-5 pt-3 border-t border-line flex items-center gap-2 flex-wrap">
          <Btn variant={panel === 'supersede' ? 'primary' : 'ghost'} size="sm" onClick={() => setPanel(panel === 'supersede' ? null : 'supersede')}><History size={13} />超越(改值)</Btn>
          <Btn variant={panel === 'forget' ? 'primary' : 'ghost'} size="sm" onClick={() => setPanel(panel === 'forget' ? null : 'forget')}><EyeOff size={13} />让读者遗忘</Btn>
          <button onClick={openDelete} disabled={delLoading} className="ml-auto text-f12 text-faint hover:text-danger cursor-pointer inline-flex items-center gap-1 transition-colors duration-150 disabled:opacity-40">
            {delLoading ? <Loader2 size={13} className="animate-spin" /> : <Trash2 size={13} />}删除命题
          </button>
        </div>

        {panel === 'supersede' && (
          <div className="mt-3 p-3 rounded-lg border border-brand/30 bg-brand/[0.02] space-y-2">
            <div className="text-meta text-faint">超越 = 关闭「{entLocal}·{row.attribute}」现开区间命题,自指定章起写入新值(旧值封存为历史,不破坏时态)。</div>
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
            <div className="text-meta text-faint">令某 knower(默认 reader 读者帧)自指定章起不再知晓此命题(设知识边 until_chapter)。</div>
            <div className="flex items-center gap-2 flex-wrap">
              <input value={forget.knower_id} onChange={(e) => setForget({ ...forget, knower_id: e.target.value })} placeholder="knower(reader 或 role:名)" className={`w-56 ${inp}`} />
              <input type="number" value={forget.until_chapter} onChange={(e) => setForget({ ...forget, until_chapter: e.target.value })} placeholder="自第几章失效" className={`w-32 ${inp}`} />
              <Btn variant="primary" size="sm" onClick={doForget} disabled={busy}>{busy && <Loader2 size={13} className="animate-spin" />}确认遗忘</Btn>
            </div>
          </div>
        )}
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
function PromiseLifecycle({ row, onChanged }) {
  const [payoff, setPayoff] = useState('')
  const [clue, setClue] = useState({ note: '', chapter: '' })
  const [busy, setBusy] = useState(false)
  const clues = Array.isArray(row.clues) ? row.clues : []
  const act = async (fn, okMsg) => {
    setBusy(true)
    try { await fn(); showToast(okMsg, { tone: 'ok' }); onChanged?.() }
    catch (e) { showToast(e?.body?.detail || e?.message || '操作失败', { tone: 'danger' }) }
    finally { setBusy(false) }
  }
  return (
    <div className="mt-5 rounded-xl border border-line bg-canvas p-3 space-y-2.5">
      <div className="text-f12 font-medium text-ink">生命周期 · 埋第{row.setup_chapter ?? '—'}章
        {row.payoff_chapter != null ? ` → 收第${row.payoff_chapter}章` : ' → 待收'}
        {row.status ? `(${row.status})` : ''}</div>
      {row.payoff_chapter == null && (
        <div className="flex items-center gap-2">
          <input value={payoff} onChange={(e) => setPayoff(e.target.value)} placeholder="回收章号" aria-label="回收章号"
            className="w-24 h-7 px-2 rounded-lg border border-line bg-surface text-f12" />
          <button disabled={busy || !/^\d+$/.test(payoff)}
            onClick={() => act(() => api.advancePromise(row.id, Number(payoff)), '已回收(closed)')}
            className="h-7 px-2.5 rounded-lg border border-line text-f12 text-ink hover:bg-soft cursor-pointer disabled:opacity-40">标记回收</button>
        </div>
      )}
      <div className="space-y-1">
        <div className="text-meta text-faint">草蛇灰线线索({clues.length})</div>
        {clues.map((c, i) => (
          <div key={i} className="flex items-center gap-2 text-f12 text-ink">
            <span className="text-faint shrink-0">第{c.chapter ?? '?'}章</span>
            <span className="flex-1 min-w-0 truncate">{c.note || String(c)}</span>
            <button disabled={busy} onClick={() => act(() => api.removePromiseClue(row.id, i), '线索已删')}
              className="text-meta text-faint hover:text-ink cursor-pointer shrink-0">删</button>
          </div>
        ))}
        <div className="flex items-center gap-2">
          <input value={clue.chapter} onChange={(e) => setClue({ ...clue, chapter: e.target.value })} aria-label="线索章号"
            placeholder="章" className="w-14 h-7 px-2 rounded-lg border border-line bg-surface text-f12" />
          <input value={clue.note} onChange={(e) => setClue({ ...clue, note: e.target.value })} aria-label="线索内容"
            placeholder="线索内容(不点破的中途暗示)" className="flex-1 h-7 px-2 rounded-lg border border-line bg-surface text-f12" />
          <button disabled={busy || !clue.note.trim() || !/^\d+$/.test(clue.chapter)}
            onClick={() => act(async () => { await api.addPromiseClue(row.id, clue.note.trim(), Number(clue.chapter)); setClue({ note: '', chapter: '' }) }, '线索已加')}
            className="h-7 px-2.5 rounded-lg border border-line text-f12 text-ink hover:bg-soft cursor-pointer disabled:opacity-40">+ 线索</button>
        </div>
      </div>
    </div>
  )
}

// 物品状态变更特化块(断头修复 P1-9):走 POST /items/{name}/state 记 state_history——
// 通用编辑的 symbolic_state 直改不留痕,历史链此前在前端无入口。
function ItemStateChange({ name, onChanged }) {
  const [f, setF] = useState({ state: 'lost', chapter: '', reason: '' })
  const [busy, setBusy] = useState(false)
  return (
    <div className="mt-5 rounded-xl border border-line bg-canvas p-3 space-y-2">
      <div className="text-f12 font-medium text-ink">记录状态变更(入历史链,区别于直接改档案)</div>
      <div className="flex items-center gap-2">
        <select value={f.state} onChange={(e) => setF({ ...f, state: e.target.value })} aria-label="新状态"
          className="h-7 px-1.5 rounded-lg border border-line bg-surface text-f12">
          {['active', 'lost', 'destroyed', 'unknown'].map((s) => <option key={s}>{s}</option>)}
        </select>
        <input value={f.chapter} onChange={(e) => setF({ ...f, chapter: e.target.value })} aria-label="发生章"
          placeholder="发生章" className="w-20 h-7 px-2 rounded-lg border border-line bg-surface text-f12" />
        <input value={f.reason} onChange={(e) => setF({ ...f, reason: e.target.value })} aria-label="缘由"
          placeholder="缘由(如:铜炉在乱岗被夺)" className="flex-1 h-7 px-2 rounded-lg border border-line bg-surface text-f12" />
        <button disabled={busy || !/^\d+$/.test(f.chapter)}
          onClick={async () => {
            setBusy(true)
            try {
              await api.itemState(name, f.state, Number(f.chapter), f.reason.trim())
              showToast('状态变更已记录', { tone: 'ok' }); setF({ state: 'lost', chapter: '', reason: '' }); onChanged?.()
            } catch (e) { showToast(e?.body?.detail || e?.message || '记录失败', { tone: 'danger' }) }
            finally { setBusy(false) }
          }}
          className="h-7 px-2.5 rounded-lg border border-line text-f12 text-ink hover:bg-soft cursor-pointer disabled:opacity-40">记录</button>
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
const ENTITY_RELATION_TYPES_FE = ['臣服', '敌对', '渗透', '无视', '共生', '结盟', '利用', '未知']
// ↑ 与后端 codex_schema.ENTITY_RELATION_TYPES 手抄同源(该常量注释写明:migration 085 的
// DB 侧 ASSERT 是静态 .surql 文本,没法 import Python 常量,前端更是隔着语言,只能手抄同一份
// 词表;越界值 422)——与本文件之上 CodexView.jsx 的 REL_VOCAB 对 character_relation
// 词表的既有写法同款,非本次新发明的模式。

function FactionRelations({ name }) {
  const myRef = `faction:${name}`
  const [rows, setRows] = useState(null)   // null=加载中
  const [adding, setAdding] = useState(false)
  const [form, setForm] = useState({ other: '', relation_type: '臣服', perception_a: '', perception_b: '', since_chapter: '' })

  const reload = () => api.entityRelations(myRef)
    .then((r) => setRows(Array.isArray(r) ? r : []))
    .catch(() => setRows([]))
  useEffect(() => { setRows(null); reload() }, [name])   // eslint-disable-line react-hooks/exhaustive-deps

  const submitAdd = async () => {
    if (!form.other.trim() || !form.relation_type) {
      showToast('对方实体与关系类型必填(对方实体如 faction:天龙座 / role:某角色)', { tone: 'danger' })
      return
    }
    try {
      await api.addEntityRelation({
        a: myRef,
        b: form.other.trim(),
        relation_type: form.relation_type,
        perception_a: form.perception_a || null,
        perception_b: form.perception_b || null,
        since_chapter: form.since_chapter === '' ? null : Number(form.since_chapter),
      })
      showToast('关系已建立', { tone: 'ok' })
      setAdding(false)
      setForm({ other: '', relation_type: '臣服', perception_a: '', perception_b: '', since_chapter: '' })
      reload()
    } catch (e) { showToast(e?.body?.detail || e?.message || '建立失败', { tone: 'danger' }) }
  }

  const removeRelation = async (r) => {
    try {
      await api.delEntityRelation(r.a, r.b)
      showToast('关系已删除', { tone: 'ok' })
      reload()
    } catch (e) { showToast(e?.body?.detail || e?.message || '删除失败', { tone: 'danger' }) }
  }

  const inp = 'h-8 rounded-md border border-line bg-canvas px-2 text-f12 text-ink outline-none focus:border-brand'

  if (rows === null) return <div className="mt-6 pt-4 border-t border-line text-f12 text-faint/50">关系加载中…</div>

  return (
    <div className="mt-6 pt-4 border-t border-line" data-testid="faction-relations">
      <SectionTitle icon={Heart} right={`${rows.length}条`}>关系 · 双方认知</SectionTitle>

      {adding ? (
        <div className="mb-3 p-3 rounded-lg border border-brand/30 bg-brand/[0.02] space-y-2" onClick={(e) => e.stopPropagation()}>
          <div className="flex gap-2 flex-wrap">
            <input value={form.other} onChange={(e) => setForm({ ...form, other: e.target.value })}
              placeholder="对方实体(如 faction:天龙座 / role:某角色)" className={`flex-1 min-w-[160px] ${inp}`} />
            <select value={form.relation_type} onChange={(e) => setForm({ ...form, relation_type: e.target.value })}
              className={`${inp} cursor-pointer`}>
              {ENTITY_RELATION_TYPES_FE.map((t) => <option key={t} value={t}>{t}</option>)}
            </select>
            <input type="number" value={form.since_chapter} onChange={(e) => setForm({ ...form, since_chapter: e.target.value })}
              placeholder="建立章(可选)" className={`w-28 ${inp}`} />
          </div>
          <input value={form.perception_a} onChange={(e) => setForm({ ...form, perception_a: e.target.value })}
            placeholder="我方认知(如:虚与委蛇,视为台阶)" className={`w-full ${inp}`} />
          <input value={form.perception_b} onChange={(e) => setForm({ ...form, perception_b: e.target.value })}
            placeholder="对方认知(可能不对称/错误,如:视其为地球代理人)" className={`w-full ${inp}`} />
          <div className="flex gap-2">
            <button onClick={submitAdd} className="px-3 h-7 rounded-lg bg-brand text-brandfg text-f12 cursor-pointer">保存</button>
            <button onClick={() => setAdding(false)} className="px-3 h-7 rounded-lg text-faint text-f12 cursor-pointer">取消</button>
          </div>
        </div>
      ) : (
        <button onClick={() => setAdding(true)} className="mb-2 text-meta text-brand hover:text-brand/80 cursor-pointer inline-flex items-center gap-0.5">
          <Plus size={12} />新增关系
        </button>
      )}

      {rows.length === 0 ? (
        <Empty>尚无关系记录——势力/角色对彼此的认知可在此登记(允许双方认知不对称甚至相互矛盾)。</Empty>
      ) : (
        <div className="space-y-2">
          {rows.map((r) => {
            const mine = r.a === myRef
            const otherRef = mine ? r.b : r.a
            const myPerception = mine ? r.perception_a : r.perception_b
            const otherPerception = mine ? r.perception_b : r.perception_a
            return (
              <div key={`${r.a}->${r.b}->${r.relation_type}`} className="p-2.5 rounded-lg border border-line">
                <div className="flex items-center gap-2 mb-1.5 flex-wrap">
                  <span className="text-f13 font-medium text-ink">{otherRef}</span>
                  <Tag tone="brand">{r.relation_type}</Tag>
                  {r.since_chapter != null && <span className="text-meta text-faint">第{r.since_chapter}章建立</span>}
                  {r.until_chapter != null && <span className="text-meta text-danger">第{r.until_chapter}章结束</span>}
                  {/* aria-label 与本页"删除势力"按钮(FactionSchemaView,同为"删除"文案)区分开,
                      避免两个同名"删除"按钮的可访问名称撞在一起(屏读/测试都无法区分) */}
                  <button onClick={() => removeRelation(r)} aria-label={`删除与${otherRef}的关系`}
                    className="ml-auto text-meta text-faint hover:text-danger cursor-pointer">删除</button>
                </div>
                <div className="grid grid-cols-2 gap-3 text-f12">
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

export function CodexDetail({ node, onChanged, onDeleted }) {
  const [row, setRow] = useState(null)
  const [loading, setLoading] = useState(true)
  const [loadErr, setLoadErr] = useState('')
  const [delOpen, setDelOpen] = useState(false)
  const [delLoading, setDelLoading] = useState(false)
  const [deleteImpact, setDeleteImpact] = useState(null)
  // 保存状态机(saving/saved/error):失焦保存此前只有失败 toast,成功/进行中无反馈
  const [saveState, setSaveState] = useState('idle')
  const [saveErr, setSaveErr] = useState('')
  const lastPayloadRef = useRef(null)
  const detailType = TYPE_MAP[node?.type]

  // silent=true:后台对账刷新,不翻 loading、不进 error 态,且找不到时不清空 row。
  // 保存成功走这条(Issue 1):否则 setLoading(true) 会触发 `if (loading) return <spinner>`
  // 早返回,把整个表单(含 saving/saved 状态条)闪成居中 spinner,每改一字段抖一下。
  const reload = (silent = false) => {
    if (!node || !detailType) { if (!silent) setLoading(false); return }
    if (!silent) { setLoading(true); setLoadErr('') }
    loadRows(node.type)
      .then((rows) => {
        const found = pickRow(node.type, rows, node.ref) || null
        // 静默刷新只在命中时对账;命中不到不摧毁乐观值(如非角色改名后按旧 ref 查不到)
        if (silent) { if (found) setRow(found); return }
        setRow(found); setLoading(false)
      })
      // 请求失败 ≠ 条目不存在:进 error 态给真实错误 + 重试,不谎称「可能已删除」(静默刷新则吞掉,不污染已保存视图)
      .catch((e) => { if (!silent) { setRow(null); setLoadErr(e?.body?.detail || e?.message || '加载失败'); setLoading(false) } })
  }
  useEffect(() => { setDeleteImpact(null); setSaveState('idle'); setSaveErr(''); reload() }, [node?.id])

  const doPersist = async (updated) => {
    lastPayloadRef.current = updated
    setSaveState('saving'); setSaveErr('')
    try {
      await persist(detailType, updated)
      // 乐观合并:updated 已是整行(DetailView 用 {...row,[k]:v} 上抛,仅剔除掩码字段),
      // 立即合并到 prev(掩码字段用 prev 值保底)→ 新值即时可见、不经 loading 守卫闪 spinner。
      setRow((prev) => ({ ...prev, ...updated }))
      setSaveState('saved')
      reload(true)   // 静默后台与服务端对账(规范化/触发器),不翻 loading
      onChanged?.()
    } catch (e) {
      setSaveState('error'); setSaveErr(e?.body?.detail || e?.message || '保存失败')
    }
  }

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
    <div className="h-full overflow-y-auto">
      <div className="max-w-2xl mx-auto px-6 py-5">
        {/* 保存状态行:saving/saved 用 status,error 用 alert + 真实错误 + 重试(重发最后一次 payload) */}
        {saveState !== 'idle' && (
          <div role={saveState === 'error' ? 'alert' : 'status'}
            className={`mb-3 flex items-center gap-2 text-meta ${saveState === 'error' ? 'text-danger' : 'text-faint'}`}>
            {saveState === 'saving' && <><Loader2 size={13} className="animate-spin" />保存中…</>}
            {saveState === 'saved' && <><Check size={13} className="text-ok" />已保存</>}
            {saveState === 'error' && (
              <>
                <span>保存失败:{saveErr}</span>
                <Btn size="xs" variant="soft" onClick={() => doPersist(lastPayloadRef.current)}>重试保存</Btn>
              </>
            )}
          </div>
        )}
        <DetailView
          type={detailType}
          row={row}
          isNew={false}
          onBack={null}
          onUpdate={doPersist}
          onDelete={openDelete}
        />
        {/* 伏笔专属(断头修复#21):收 + 草蛇灰线线索 */}
        {detailType === 'promises' && row?.id && (
          <PromiseLifecycle row={row} onChanged={() => { reload(); onChanged?.() }} />
        )}
        {/* 物品专属(断头修复 P1-9):状态变更入历史链 */}
        {detailType === 'items' && row?.name && (
          <ItemStateChange name={row.name} onChanged={() => { reload(); onChanged?.() }} />
        )}
        {/* 势力专属(CX-Task 7):关系区——双方认知并排展示(entity_relation,与角色关系表是两套独立表) */}
        {detailType === 'factions' && row?.name && (
          <FactionRelations name={row.name} />
        )}
        {/* 角色专属:弧光锚编辑 + 里程碑 + 信奉度曲线(独立 PATCH /char-anchors,不碰角色档案回写) */}
        {detailType === 'chars' && row?.id && <CharArcAnchors characterId={row.id} />}
        {/* 角色专属:声音演变后半环(P1-11)——voice flags 列表 + 一键折叠 + 折叠后声线指纹(独立 /voice-flags/*,不碰角色档案) */}
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
