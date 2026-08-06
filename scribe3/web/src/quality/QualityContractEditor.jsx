import { useEffect, useMemo, useState } from 'react'
import { CheckCircle2, FileCheck2, Loader2, Save } from 'lucide-react'
import { api } from '../api'
import { Btn, Card, SectionTitle } from '../ui.jsx'

const DIMENSIONS = [
  ['coherence_causality', '连贯性与因果'], ['character_truth', '人物真实性'],
  ['scene_necessity', '场景必要性'], ['structure_pacing', '结构与节奏'],
  ['suspense_payoff', '悬念与兑现'], ['emotional_effect', '情绪效力'],
  ['reading_experience', '阅读体验'], ['language_voice', '语言与声音'],
  ['theme_subtext', '主题与潜台词'], ['originality', '原创性'],
]
const SUCCESS = [
  ['character', '人物'], ['relationship', '关系'], ['structure', '结构'], ['language', '语言'], ['originality', '原创性'],
]
const splitLines = (value) => String(value || '').split('\n').map((item) => item.trim()).filter(Boolean)
const joinLines = (value) => Array.isArray(value) ? value.join('\n') : ''

function blankContract(work) {
  return {
    contractId: `quality-contract:${work}`,
    revision: 1,
    primaryGenre: '长篇小说', overlayGenres: '', customGenreDescription: '',
    targetReaders: '成年读者', readingContext: '连续阅读',
    corePromise: '让人物的每次选择都推动关系、秘密与代价发生变化。',
    intendedExperience: '好奇\n紧张\n余韵', emotionalArc: '压抑\n对峙\n余韵',
    themeQuestions: '真相是否值得代价？', allowedAmbiguities: '', prohibitedPreaching: '',
    success: Object.fromEntries(SUCCESS.map(([key, label]) => [key, `${label}必须由正文行动与可定位证据支撑。`])),
    nonNegotiables: '不得以旁白替人物完成关键选择。', allowedTradeoffs: '',
    dimensionWeights: Object.fromEntries(DIMENSIONS.map(([key]) => [key, 1])),
    weights: { author: 0.6, system: 0.25, reference: 0.15 },
    referenceTargets: '[]', milestones: ['chapter'],
    attention: { blocking: -1, major: 5, ordinary: 10 },
    completionCriteria: '十维均有冻结正文证据与作者裁决。\n所有阻断问题已处理或被作者明确接受。',
  }
}

function fromContract(contract, work) {
  const base = blankContract(work)
  return {
    ...base,
    contractId: contract.contract_id, revision: contract.revision,
    primaryGenre: contract.primary_genre, overlayGenres: joinLines(contract.overlay_genres),
    customGenreDescription: contract.custom_genre_description || '', targetReaders: contract.target_readers,
    readingContext: contract.reading_context, corePromise: contract.core_promise,
    intendedExperience: joinLines(contract.intended_experience), emotionalArc: joinLines(contract.emotional_arc),
    themeQuestions: joinLines(contract.theme_questions), allowedAmbiguities: joinLines(contract.allowed_ambiguities),
    prohibitedPreaching: joinLines(contract.prohibited_preaching),
    success: Object.fromEntries((contract.success_criteria || []).map((item) => [item.key, item.text])),
    nonNegotiables: joinLines(contract.non_negotiables), allowedTradeoffs: joinLines(contract.allowed_tradeoffs),
    dimensionWeights: Object.fromEntries((contract.dimension_weights || []).map((item) => [item.dimension, item.weight])),
    weights: contract.weights || base.weights,
    referenceTargets: JSON.stringify(contract.reference_targets || [], null, 2),
    milestones: contract.evaluation_milestones || ['chapter'], attention: contract.attention_budget || base.attention,
    completionCriteria: joinLines(contract.completion_criteria),
  }
}

function toContract(form, work) {
  let referenceTargets
  try { referenceTargets = JSON.parse(form.referenceTargets || '[]') } catch { throw new Error('参考目标必须是有效 JSON 数组') }
  if (!Array.isArray(referenceTargets)) throw new Error('参考目标必须是 JSON 数组')
  return {
    contract_id: form.contractId.trim(), work, revision: Number(form.revision),
    primary_genre: form.primaryGenre.trim(), overlay_genres: splitLines(form.overlayGenres),
    custom_genre_description: form.customGenreDescription.trim(), target_readers: form.targetReaders.trim(),
    reading_context: form.readingContext.trim(), core_promise: form.corePromise.trim(),
    intended_experience: splitLines(form.intendedExperience), emotional_arc: splitLines(form.emotionalArc),
    theme_questions: splitLines(form.themeQuestions), allowed_ambiguities: splitLines(form.allowedAmbiguities),
    prohibited_preaching: splitLines(form.prohibitedPreaching),
    success_criteria: SUCCESS.map(([key]) => ({ key, text: String(form.success[key] || '').trim() })),
    non_negotiables: splitLines(form.nonNegotiables), allowed_tradeoffs: splitLines(form.allowedTradeoffs),
    dimension_weights: DIMENSIONS.map(([dimension]) => ({ dimension, weight: Number(form.dimensionWeights[dimension]) })),
    weights: Object.fromEntries(Object.entries(form.weights).map(([key, value]) => [key, Number(value)])),
    reference_targets: referenceTargets, evaluation_milestones: form.milestones,
    attention_budget: Object.fromEntries(Object.entries(form.attention).map(([key, value]) => [key, Number(value)])),
    completion_criteria: splitLines(form.completionCriteria),
  }
}

function TextField({ label, path, value, onChange, type = 'text' }) {
  return <label className="grid gap-1 text-f12 text-faint"><span>{label}</span><input aria-label={label} data-field-path={path} type={type} value={value} onChange={(e) => onChange(e.target.value)} className="h-8 rounded-md border border-line bg-canvas px-2 text-f13 text-ink outline-none focus:border-brand" /></label>
}
function LinesField({ label, path, value, onChange, placeholder }) {
  return <label className="grid gap-1 text-f12 text-faint"><span>{label}</span><textarea aria-label={label} data-field-path={path} value={value} onChange={(e) => onChange(e.target.value)} placeholder={placeholder || '每行一项'} className="min-h-16 w-full resize-y rounded-md border border-line bg-canvas px-2 py-1.5 text-f13 text-ink outline-none focus:border-brand" /></label>
}

export function QualityContractEditor({ work }) {
  const initial = useMemo(() => blankContract(work), [work])
  const [form, setForm] = useState(initial)
  const [status, setStatus] = useState('loading')
  const [error, setError] = useState('')
  const [approved, setApproved] = useState(false)
  const [yardsticks, setYardsticks] = useState([])
  const [pickId, setPickId] = useState('')
  const [pickDim, setPickDim] = useState('language_voice')
  const patch = (key, value) => setForm((previous) => ({ ...previous, [key]: value }))

  useEffect(() => {
    let live = true
    const blank = blankContract(work)
    setForm(blank); setApproved(false); setStatus('loading'); setError('')
    api.qualityContract(blank.contractId, blank.revision, work, true)
      .then((contract) => {
        if (!live) return
        if (contract?.found === false) { setStatus('ready'); return }
        setForm(fromContract(contract, work)); setApproved(!!contract.approved); setStatus('ready')
      })
      .catch((err) => { if (live) { setStatus('ready'); if (err?.status !== 404) setError('读取质量合同失败，请检查连接后重试。') } })
    api.approvedReferenceFingerprints(work)
      .then((rows) => { if (live) setYardsticks(Array.isArray(rows) ? rows : []) })
      .catch(() => { if (live) setYardsticks([]) })
    return () => { live = false }
  }, [work])

  const addTargetFromYardstick = () => {
    const row = yardsticks.find((item) => item.fingerprint_id === pickId || item.reference_work_id === pickId)
    if (!row) return
    let current = []
    try { current = JSON.parse(form.referenceTargets || '[]') } catch { current = [] }
    if (!Array.isArray(current)) current = []
    const mechanism = (row.transferable_mechanisms_preview && row.transferable_mechanisms_preview[0]) || row.full_book_fingerprint || '已批准技法'
    current.push({
      reference_work_id: row.reference_work_id,
      dimension: pickDim,
      mode: 'inspired',
      intensity: 0.5,
      mechanism: String(mechanism).slice(0, 140),
      difference_requirement: '以本书人物与冲突重新发明，禁止仿写原句与专名',
    })
    patch('referenceTargets', JSON.stringify(current, null, 2))
  }

  const save = async () => {
    try {
      setError(''); setStatus('saving')
      const saved = await api.qualityCreateContract(toContract(form, work))
      setApproved(!!saved.approved); setStatus('ready')
    } catch (err) {
      setStatus('ready'); setError(err?.body?.detail || err?.message || '保存质量合同失败')
    }
  }
  const approve = async () => {
    try {
      setError(''); setStatus('saving')
      const saved = await api.qualityApproveContract(form.contractId, form.revision, work)
      setApproved(!!saved.approved); setStatus('ready')
    } catch (err) {
      setStatus('ready'); setError(err?.body?.detail || err?.message || '批准质量合同失败')
    }
  }
  const patchNested = (group, key, value) => setForm((previous) => ({
    ...previous, [group]: { ...previous[group], [key]: value },
  }))

  return <div className="h-full overflow-y-auto"><div className="max-w-3xl mx-auto px-6 py-5 space-y-4">
    <SectionTitle icon={FileCheck2} right={approved ? '已批准' : '草案'}>质量合同</SectionTitle>
    <p className="text-f13 text-faint leading-relaxed">合同固定每部作品的质量目标、十维权重和参考边界。保存生成不可变修订；只有作者批准的修订可启动章节评价。</p>
    {error && <div role="alert" className="rounded-md bg-danger/10 px-3 py-2 text-f13 text-danger">{error}</div>}
    <Card className="p-4 space-y-3"><h3 className="font-medium text-ink">定位与读者</h3><div className="grid sm:grid-cols-2 gap-3">
      <TextField label="合同 ID" path="contract.id" value={form.contractId} onChange={(value) => patch('contractId', value)} />
      <TextField label="修订号" path="contract.revision" type="number" value={form.revision} onChange={(value) => patch('revision', value)} />
      <TextField label="主类型" path="contract.primary_genre" value={form.primaryGenre} onChange={(value) => patch('primaryGenre', value)} />
      <TextField label="目标读者" path="contract.target_readers" value={form.targetReaders} onChange={(value) => patch('targetReaders', value)} />
      <LinesField label="叠加类型" path="contract.overlay_genres" value={form.overlayGenres} onChange={(value) => patch('overlayGenres', value)} />
      <LinesField label="自定义类型说明" path="contract.custom_genre_description" value={form.customGenreDescription} onChange={(value) => patch('customGenreDescription', value)} />
    </div><LinesField label="阅读情境" path="contract.reading_context" value={form.readingContext} onChange={(value) => patch('readingContext', value)} /><LinesField label="核心承诺" path="contract.core_promise" value={form.corePromise} onChange={(value) => patch('corePromise', value)} /></Card>
    <Card className="p-4 space-y-3"><h3 className="font-medium text-ink">体验、主题与边界</h3><div className="grid sm:grid-cols-2 gap-3">
      <LinesField label="预期体验" path="contract.intended_experience" value={form.intendedExperience} onChange={(value) => patch('intendedExperience', value)} />
      <LinesField label="情绪弧光" path="contract.emotional_arc" value={form.emotionalArc} onChange={(value) => patch('emotionalArc', value)} />
      <LinesField label="主题问题" path="contract.theme_questions" value={form.themeQuestions} onChange={(value) => patch('themeQuestions', value)} />
      <LinesField label="允许的含混" path="contract.allowed_ambiguities" value={form.allowedAmbiguities} onChange={(value) => patch('allowedAmbiguities', value)} />
      <LinesField label="禁止说教" path="contract.prohibited_preaching" value={form.prohibitedPreaching} onChange={(value) => patch('prohibitedPreaching', value)} />
      <LinesField label="不可协商项" path="contract.non_negotiables" value={form.nonNegotiables} onChange={(value) => patch('nonNegotiables', value)} />
    </div><LinesField label="允许的取舍" path="contract.allowed_tradeoffs" value={form.allowedTradeoffs} onChange={(value) => patch('allowedTradeoffs', value)} /></Card>
    <Card className="p-4 space-y-3"><h3 className="font-medium text-ink">五类成功标准</h3><div className="grid gap-3">{SUCCESS.map(([key, label]) => <LinesField key={key} label={`${label}成功标准`} path={`contract.success_criteria.${key}`} value={form.success[key] || ''} onChange={(value) => patchNested('success', key, value)} />)}</div></Card>
    <Card className="p-4 space-y-3"><h3 className="font-medium text-ink">十维与三轴</h3><div className="grid sm:grid-cols-2 gap-3">{DIMENSIONS.map(([key, label]) => <TextField key={key} label={`${label}权重`} path={`contract.dimension_weights.${key}`} type="number" value={form.dimensionWeights[key]} onChange={(value) => patchNested('dimensionWeights', key, value)} />)}</div><div className="grid sm:grid-cols-3 gap-3"><TextField label="作者权重" path="contract.weights.author" type="number" value={form.weights.author} onChange={(value) => patchNested('weights', 'author', value)} /><TextField label="系统权重" path="contract.weights.system" type="number" value={form.weights.system} onChange={(value) => patchNested('weights', 'system', value)} /><TextField label="参考权重" path="contract.weights.reference" type="number" value={form.weights.reference} onChange={(value) => patchNested('weights', 'reference', value)} /></div></Card>
    <Card className="p-4 space-y-3"><h3 className="font-medium text-ink">参考、里程碑与完成</h3>
      <div className="rounded-md border border-line bg-canvas p-3 space-y-2" data-testid="contract-yardstick-picker">
        <div className="text-f12 text-faint">从已批准技法标尺添加参考目标（主路径；JSON 仍可细调）</div>
        <div className="grid sm:grid-cols-3 gap-2">
          <label className="grid gap-1 text-f12 text-faint"><span>已批准标尺</span>
            <select aria-label="选择已批准标尺" value={pickId} onChange={(e) => setPickId(e.target.value)} className="h-8 rounded-md border border-line bg-canvas px-2 text-f13 text-ink">
              <option value="">选择…</option>
              {yardsticks.map((row) => (
                <option key={row.fingerprint_id} value={row.fingerprint_id}>{row.title || row.reference_work_id} · rev {row.revision}</option>
              ))}
            </select>
          </label>
          <label className="grid gap-1 text-f12 text-faint"><span>维度</span>
            <select aria-label="参考目标维度" value={pickDim} onChange={(e) => setPickDim(e.target.value)} className="h-8 rounded-md border border-line bg-canvas px-2 text-f13 text-ink">
              {DIMENSIONS.map(([key, label]) => <option key={key} value={key}>{label}</option>)}
            </select>
          </label>
          <div className="flex items-end"><Btn size="sm" variant="soft" onClick={addTargetFromYardstick} disabled={!pickId}>加入参考目标</Btn></div>
        </div>
        {yardsticks.length === 0 && <div className="text-meta text-faint">暂无已批准指纹。请先在技法标尺模块批准一部参考。</div>}
      </div>
      <LinesField label="参考目标（JSON 数组）" path="contract.reference_targets" value={form.referenceTargets} onChange={(value) => patch('referenceTargets', value)} placeholder='[{"reference_work_id":"…","dimension":"language_voice","mode":"inspired","intensity":0.5,"mechanism":"…","difference_requirement":"…"}]' /><div className="flex flex-wrap gap-3">{['scene', 'chapter', 'volume', 'book'].map((item) => <label key={item} className="inline-flex items-center gap-1 text-f13 text-ink"><input type="checkbox" checked={form.milestones.includes(item)} onChange={() => patch('milestones', form.milestones.includes(item) ? form.milestones.filter((value) => value !== item) : [...form.milestones, item])} data-field-path={`contract.evaluation_milestones.${item}`} />{item}</label>)}</div><div className="grid sm:grid-cols-3 gap-3"><TextField label="阻断预算" path="contract.attention_budget.blocking" type="number" value={form.attention.blocking} onChange={(value) => patchNested('attention', 'blocking', value)} /><TextField label="主要问题预算" path="contract.attention_budget.major" type="number" value={form.attention.major} onChange={(value) => patchNested('attention', 'major', value)} /><TextField label="普通问题预算" path="contract.attention_budget.ordinary" type="number" value={form.attention.ordinary} onChange={(value) => patchNested('attention', 'ordinary', value)} /></div><LinesField label="完成标准" path="contract.completion_criteria" value={form.completionCriteria} onChange={(value) => patch('completionCriteria', value)} /></Card>
    <div className="flex items-center gap-2 pb-8"><Btn onClick={save} disabled={status === 'saving'}>{status === 'saving' ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />}保存合同草案</Btn><Btn variant="bordered" onClick={approve} disabled={status === 'saving' || approved}>{approved ? <><CheckCircle2 size={14} />已批准</> : '批准本修订'}</Btn></div>
  </div></div>
}
