import { useEffect, useMemo, useState } from 'react'
import { api } from './api'
import { useToast } from './ui/Toast.jsx'
import { Btn } from './ui.jsx'
import { ReadOnlyText } from './ui/EditableText.jsx'
import {
  seedChiefNarrativeWrite,
  seedChapterOutline,
  seedChapterBeats,
  seedChapterDeduce,
  seedChiefMovePlan,
  seedChiefHookType,
} from './lib/chiefSeed.js'
import {
  evaluateChapterContract,
  contractSoftSummary,
  executionSoftSummary,
} from './lib/chapterContractGate.js'
import { softGateIssues } from './lib/deduceGate.js'
import { loadIaDensity, volumeMetaPeekVisible } from './lib/iaDensity.js'
import { ChapterSoftCards } from './ChapterSoftCards.jsx'
import { StageBoard } from './StageBoard.jsx'
import { ScenePaper } from './ScenePaper.jsx'

/** 本地三行摘要（chapter.narrative_drive 直读；与后端 format_drive_three_lines 同形） */
function driveThreeFromChapter(drive) {
  const d = drive && typeof drive === 'object' ? drive : {}
  const inc = d.inciting_force && typeof d.inciting_force === 'object' ? d.inciting_force : {}
  const opp = d.opposition && typeof d.opposition === 'object' ? d.opposition : {}
  const inciting = String(inc.summary || '').trim()
  const who = String(opp.who_or_what || '').trim()
  const wants = String(opp.wants || '').trim()
  const opposition = [who, wants ? `要 ${wants}` : ''].filter(Boolean).join(' ').trim()
  const end_hook = String(d.end_hook || '').trim()
  const scene_turn = String(d.scene_turn || '').trim()
  return {
    present: Boolean(inciting || opposition || end_hook || scene_turn),
    inciting,
    opposition,
    end_hook,
    scene_turn,
  }
}

function gapLabel(g) {
  const map = {
    dialogue_low: '对白偏少',
    short_and_dialogue_low: '短稿且对白不足',
    weak_opener: '开篇外力弱',
    missing_event: '事件推进弱',
  }
  return map[g] || g
}

const LABEL_OPTIONS = [
  ['idea', '想法'],
  ['beat', '节拍'],
  ['draft', '草稿'],
  ['revise', '修订'],
  ['done', '完成'],
]

const SYNOPSIS_PREVIEW = 280
const TRUTH_PREVIEW = 280
const BEATS_PREVIEW = 5

function StatusDot({ ok, warn }) {
  const tone = ok ? 'bg-ok' : warn ? 'bg-warn' : 'bg-danger'
  return (
    <span
      className={`inline-block w-2 h-2 rounded-full ${tone} shrink-0`}
      aria-hidden
    />
  )
}

function ThisCircleBlock({ seq, work, chapter, toast, setChapter }) {
  const plan = (chapter?.beats_meta && chapter.beats_meta.story_move_plan) || chapter?.story_move_plan || {}
  const hookType = chapter?.beats_meta?.chapter_hook_type || ''
  const [benyi, setBenyi] = useState(plan.benyi || '')
  const [moveId, setMoveId] = useState(plan.move_id || plan.slug || 'triangle_info')
  const [moves, setMoves] = useState([])
  useEffect(() => {
    api.storyMoves?.(work).then((r) => {
      const rows = (r.moves || []).filter((c) => (c.status || 'approved') === 'approved')
      setMoves(rows)
    }).catch(() => setMoves([]))
  }, [work])
  const save = () => {
    api.saveStoryMovePlan?.(seq, { benyi, move_id: moveId, approved: true }, work)
      .then((r) => {
        const next = r.plan || { benyi, move_id: moveId, approved: true }
        setChapter?.((ch) => {
          const cur = ch || {}
          const bm = { ...(cur.beats_meta || {}), story_move_plan: next }
          return { ...cur, beats_meta: bm }
        })
        toast(next.approved ? '这一圈已登记' : '已记下，本意或招式还缺', { tone: next.approved ? 'ok' : 'warn' })
      })
      .catch((e) => toast(e?.message || '保存失败', { tone: 'danger' }))
  }
  return (
    <section className="mb-4" data-testid="chapter-this-circle">
      <h4 className="text-f13 font-medium text-ink mb-1">这一圈</h4>
      <div className="rounded-md border border-line/40 bg-canvas/50 px-3 py-2 text-f13 space-y-2">
        <p className="text-ink">
          {plan.approved
            ? `${plan.move_id || plan.slug || '招式'} · 本意 ${plan.benyi || '—'}`
            : <span className="text-faint">还没画。本意×绕法，不是完成灯。</span>}
        </p>
        <label className="block text-f12">本意
          <input className="mt-0.5 w-full rounded border border-line px-2 py-1 bg-canvas" value={benyi}
            maxLength={40} onChange={(e) => setBenyi(e.target.value)} placeholder="这一圈要让人感到什么" />
        </label>
        <label className="block text-f12">招式
          <select className="mt-0.5 w-full rounded border border-line px-2 py-1 bg-canvas" value={moveId}
            onChange={(e) => setMoveId(e.target.value)}>
            {(moves.length ? moves : [{ slug: 'triangle_info', name: '三角信息法' }]).map((c) => (
              <option key={c.slug} value={c.slug}>{c.name || c.slug}</option>
            ))}
          </select>
        </label>
        <div className="flex flex-wrap gap-1">
          <Btn variant="soft" size="xs" data-testid="save-this-circle" onClick={save}>登记这一圈</Btn>
          <Btn variant="ghost" size="xs" data-testid="seed-draw-triangle" onClick={() => seedChiefMovePlan(seq, benyi)}>让主编画</Btn>
          <Btn variant="ghost" size="xs" onClick={() => seedChiefHookType(seq, hookType)}>钩类型{hookType ? ` · ${hookType}` : ''}</Btn>
        </div>
      </div>
    </section>
  )
}

function clip(text, n) {
  const s = String(text || '').trim()
  if (!s) return ''
  return s.length > n ? `${s.slice(0, n)}…` : s
}

/**
 * 章前契约页：元数据 + synopsis/beats/scene_truth 摘要 + 齐套 + 主编种子 + 跳阶段。
 * 禁止 api.patchChapter 叙事直写。
 */
export function ChapterMetaPane({
  seq,
  work,
  onClose,
  onNavigatePhase,
  onOpenAux,
}) {
  const toast = useToast()
  const [loading, setLoading] = useState(true)
  const [volumes, setVolumes] = useState([])
  const [chapter, setChapter] = useState(null)
  const [briefHint, setBriefHint] = useState(null)
  const [execSoft, setExecSoft] = useState(null)

  useEffect(() => {
    let alive = true
    setLoading(true)
    setExecSoft(null)
    Promise.all([api.chapter(seq, work, { includeSuggest: true }), api.listVolumes()])
      .then(([ch, rows]) => {
        if (!alive) return
        setChapter(ch || {})
        setVolumes(Array.isArray(rows) ? rows : [])
      })
      .catch((e) => {
        if (alive) toast(e?.body?.detail || e?.message || '章节信息加载失败', { tone: 'danger' })
      })
      .finally(() => { if (alive) setLoading(false) })

    if (typeof api.chapterBrief === 'function') {
      api.chapterBrief(seq, work)
        .then((b) => {
          if (!alive || !b) return
          const ops = b?.ops?.length ?? b?.must?.length ?? null
          if (ops != null) setBriefHint(`${ops} 项操作`)
          else if (b?.title || b?.summary) setBriefHint('已生成')
        })
        .catch(() => { if (alive) setBriefHint(null) })
    }
    // 执行 soft：同源 API，失败静默（不挡契约页）
    if (typeof api.executionSoftStatus === 'function') {
      api.executionSoftStatus(seq, work)
        .then((s) => { if (alive) setExecSoft(s || null) })
        .catch(() => { if (alive) setExecSoft(null) })
    }
    return () => { alive = false }
  }, [seq, work])

  const title = chapter?.title || ''
  const label = chapter?.label || ''
  const volume = chapter?.volume || ''
  const synopsis = chapter?.synopsis || ''
  const beats = Array.isArray(chapter?.beats) ? chapter.beats : []
  const sceneTruth = chapter?.scene_truth || ''

  const volRow = volumes.find((v) => String(v.id) === String(volume))
  const volTitle = volRow?.title || volume || '未分卷'
  const volIntro = String(volRow?.intro || '').trim()
  const showVolPeek = Boolean(volume && volIntro && volumeMetaPeekVisible(loadIaDensity()))
  const labelText = LABEL_OPTIONS.find(([v]) => v === label)?.[1] || label || '未标记'

  const contract = useMemo(() => evaluateChapterContract(chapter), [chapter])
  const deduce = contract.deduce || softGateIssues(chapter || {})
  const involved = Array.isArray(chapter?.involved_characters) ? chapter.involved_characters : []
  const doneDeduce = Math.max(0, involved.length - (deduce.missing?.length || 0))

  const driveSummary = useMemo(() => {
    if (execSoft?.drive_summary?.present || execSoft?.drive_summary?.inciting) {
      return execSoft.drive_summary
    }
    return driveThreeFromChapter(chapter?.narrative_drive)
  }, [chapter, execSoft])

  const goPhase = (phase) => {
    if (typeof onNavigatePhase === 'function') {
      onNavigatePhase(phase)
      return
    }
    onClose?.()
  }

  const askMeta = () => seedChiefNarrativeWrite(
    'chapter-meta',
    `第 ${seq} 章信息`,
    `请更新第 ${seq} 章 title/label/volume。当前: title=${title || '（空）'}; label=${label || '（空）'}; volume=${volume || '（空）'}。`,
  )

  const askOutline = () => seedChapterOutline(seq, synopsis)
  const askBeats = () => seedChapterBeats(seq, beats)
  const askTruth = () => {
    if (typeof onNavigatePhase === 'function') {
      onNavigatePhase('deduce')
      return
    }
    seedChapterDeduce(seq, sceneTruth)
  }

  const askEventDrive = () => {
    const ds = driveSummary || {}
    seedChiefNarrativeWrite(
      'chapter-event-drive',
      `第 ${seq} 章事件驱动`,
      `请按冲突与事件补全第 ${seq} 章：大纲里写清「谁会付出什么代价」、对白对立、引爆/对立/章末钩。` +
        `当前驱动：引爆=${ds.inciting || '（空）'}；对立=${ds.opposition || '（空）'}；钩子=${ds.end_hook || '（空）'}。` +
        (execSoft?.soft_fulfill?.gaps?.length
          ? ` 写后对照缺口：${(execSoft.soft_fulfill.gaps || []).map(gapLabel).join('、')}。`
          : ''),
    )
  }

  if (loading) return <div className="p-5 text-f13 text-faint">加载章节信息…</div>

  const beatTexts = beats
    .map((b) => (typeof b === 'string' ? b : b?.text || ''))
    .map((t) => String(t || '').trim())
    .filter(Boolean)

  return (
    <div className="w-full max-w-[42rem] mx-auto px-5 py-5" data-testid="chapter-meta-pane">
      <div className="flex items-start justify-between gap-3 mb-4">
        <div className="min-w-0">
          <h3 className="type-section text-ink">章节信息</h3>
          <p className="mt-1 text-f13 text-faint">
            第 {seq} 章 · {title || '未命名'} · {labelText} · 卷 {volTitle}
          </p>
          <p className="mt-0.5 text-f12 text-faint">
            材料参考（只读）。改场面请点「跟主编定这场」，不要在这里填表。
          </p>
        </div>
        <Btn variant="ghost" size="sm" onClick={onClose}>返回写作</Btn>
      </div>

      {/* 阶段机唯一常驻入口：与写作台顶栏五阶段页签分工——
          页签 = 切编辑面；此处 = 服务端 stage 进度 / 推进 / 本地-服务端同步。 */}
      <section className="mb-4" data-testid="chapter-meta-stage-board">
        <div className="text-meta text-faint mb-1.5">写作进度（推进到下一阶段；上方页签才是切换编辑面）</div>
        <StageBoard
          seq={seq}
          work={work}
          onPhaseChange={(p) => goPhase(p)}
        />
      </section>

      <section className="mb-4">
        <ChapterSoftCards
          seq={seq}
          work={work}
          synopsis={synopsis}
          beats={beats}
        />

      <ThisCircleBlock seq={seq} work={work} chapter={chapter} toast={toast} setChapter={setChapter} />
      </section>

      {showVolPeek && (
        <section
          className="mb-4 rounded-lg border border-line/50 bg-soft/30 px-3 py-2"
          data-testid="chapter-volume-intro-peek"
          aria-label="本卷卷纲摘要"
        >
          <div className="text-meta text-faint mb-1">本卷卷纲摘要（写章时的背景参考，不是本章大纲）</div>
          <p className="text-f13 text-ink leading-snug break-words whitespace-pre-wrap">
            {clip(volIntro, 120)}
          </p>
        </section>
      )}

      <div className="mb-4">
        <ScenePaper chapter={chapter} seq={seq} />
      </div>
      <details
        className="mb-5 rounded-lg border border-line/60 bg-surface/60 px-3 py-3"
        data-testid="chapter-contract-checklist"
        aria-label="材料备忘"
      >
        <summary className="flex items-center gap-2 mb-2 cursor-pointer list-none">
          <h4 className="text-f13 font-medium text-ink">材料备忘</h4>
          {contract.hasError ? (
            <span className="text-f12 text-faint" data-testid="contract-attention">
              材料参考未齐（不挡先写日子）
            </span>
          ) : (
            <span className="text-f12 text-ok">材料参考齐</span>
          )}
        </summary>
        <ul className="space-y-1.5 text-f13 text-ink">
          <li className="flex items-center gap-2">
            <StatusDot
              ok={contract.synopsisOk && !contract.issues.some((i) => i.id === 'shortSynopsis')}
              warn={contract.synopsisOk && contract.issues.some((i) => i.id === 'shortSynopsis')}
            />
            <span>本章大纲{!contract.synopsisOk ? ' · 还没写' : contract.issues.some((i) => i.id === 'shortSynopsis') ? ' · 偏短' : ''}</span>
          </li>
          <li className="flex items-center gap-2">
            <StatusDot ok={contract.beatsOk} />
            <span>节拍 · {contract.beatCount}/3 条（建议至少 3 条）</span>
          </li>
          <li className="flex items-center gap-2">
            <StatusDot
              ok={contract.sceneTruthOk && !contract.issues.some((i) => i.id === 'shortSceneTruth')}
              warn={contract.sceneTruthOk && contract.issues.some((i) => i.id === 'shortSceneTruth')}
            />
            <span>场景真相（本章客观事实）{!contract.sceneTruthOk ? ' · 还没写' : ''}</span>
          </li>
          <li className="flex items-center gap-2" data-testid="contract-stakes-row">
            <StatusDot
              ok={contract.stakesOk}
              warn={!contract.stakesOk && contract.stakes?.highPressure}
            />
            <span>
              会付出什么代价
              {!contract.stakes?.highPressure
                ? ' · 普通章可先不写'
                : contract.stakesOk
                  ? ` · 已写清${contract.stakes?.stakes ? `：${clip(contract.stakes.stakes, 24)}` : ''}`
                  : ' · 高压章建议写清（失败会失去什么）'}
            </span>
          </li>
          <li className="flex items-center gap-2 text-faint">
            <span className="w-2 shrink-0" aria-hidden />
            <span>
              演绎：{doneDeduce}/{involved.length}
              {deduce.stale?.length ? ` · ${deduce.stale.length} 人需重演` : ''}
            </span>
          </li>
        </ul>
        {(contract.hasError || contract.needsAttention) && (
          <p className="mt-2 text-f12 text-warn" data-testid="contract-soft-summary">
            {contractSoftSummary(chapter)}
          </p>
        )}
        <div className="mt-3 flex flex-wrap gap-2">
          <Btn variant="soft" size="sm" data-testid="contract-go-outline" onClick={() => goPhase('outline')}>去补大纲</Btn>
          <Btn variant="soft" size="sm" data-testid="contract-go-beats" onClick={() => goPhase('beats')}>去补节拍</Btn>
          <Btn variant="soft" size="sm" data-testid="contract-go-deduce" onClick={() => goPhase('deduce')}>去演绎</Btn>
          <Btn variant="ghost" size="sm" data-testid="contract-go-final" onClick={() => goPhase('final')}>去正文</Btn>
        </div>
        <p className="mt-2 text-f11 text-faint leading-relaxed">
          以上是写前建议，不拦你进正文或和主编聊天。
          真要保存成正式正文时，缺大纲/节拍/场景真相仍可能被拦住。
        </p>
      </details>

      <section
        className="mb-5 rounded-lg border border-line/60 bg-surface/60 px-3 py-3"
        data-testid="chapter-event-drive"
        aria-label="本章事件驱动"
      >
        <div className="flex items-center justify-between gap-2 mb-2">
          <h4 className="text-f13 font-medium text-ink">本章怎么往前推（事件驱动）</h4>
          <Btn variant="ghost" size="xs" data-testid="contract-seed-event-drive" onClick={askEventDrive}>
            让主编补代价与对白
          </Btn>
        </div>
        {driveSummary?.present ? (
          <ul className="space-y-1.5 text-f13 text-ink">
            <li><span className="text-faint">引爆 · </span>{driveSummary.inciting || '（空）'}</li>
            <li><span className="text-faint">对立 · </span>{driveSummary.opposition || '（空）'}</li>
            <li><span className="text-faint">章末钩 · </span>{driveSummary.end_hook || '（空）'}</li>
            {driveSummary.scene_turn ? (
              <li><span className="text-faint">转折 · </span>{driveSummary.scene_turn}</li>
            ) : null}
          </ul>
        ) : (
          <p className="text-f13 text-faint">
            还没有事件驱动摘要 · 可去「大纲」写清冲突与代价，或让主编按驱动补一版后再回来看。
          </p>
        )}
        <p className="mt-2 text-f11 text-faint">只读摘要，用来提醒你章里冲突怎么走；不会自动清空正文。</p>
      </section>

      <section
        className="mb-5 rounded-lg border border-line/60 bg-surface/60 px-3 py-3"
        data-testid="chapter-execution-soft"
        aria-label="写后执行对照"
      >
        <h4 className="text-f13 font-medium text-ink mb-2">写完对照（正文是否写到点子上）</h4>
        {!execSoft ? (
          <p className="text-f13 text-faint">加载中或暂不可用…</p>
        ) : !execSoft.has_prose ? (
          <p className="text-f13 text-faint">还没有正文 · 成稿后会提示对白、长度、是否偏离大纲等建议。</p>
        ) : (
          <div className="space-y-1.5 text-f13 text-ink">
            {execSoft.soft_fulfill ? (
              <>
                <p>
                  <span className="text-faint">状态 · </span>
                  {execSoft.soft_fulfill.ok_soft
                    ? '对照通过（仅建议）'
                    : `建议关注：${(execSoft.soft_fulfill.gaps || []).map(gapLabel).join('、') || '未达标'}`}
                  <span className="text-faint"> · 仅建议，不强制</span>
                </p>
                <p className="text-faint tnum">
                  引号 {execSoft.soft_fulfill.quotes ?? '—'}
                  {execSoft.soft_fulfill.prose_cn != null ? ` · 可见字 ${execSoft.soft_fulfill.prose_cn}` : ''}
                </p>
              </>
            ) : (
              <p className="text-faint">暂无对照数据</p>
            )}
            {execSoft.drift?.drift ? (
              <p className="text-warn" data-testid="chapter-execution-drift">
                与大纲/驱动有偏差 · {execSoft.drift.advisory || '事件安排相对成稿已变，建议【强制重写】核对（不会自动清空正文）'}
              </p>
            ) : (
              <p className="text-faint">与大纲/驱动基本一致（或尚未正式定稿对照）</p>
            )}
            {executionSoftSummary(execSoft) ? (
              <p className="text-f12 text-warn" data-testid="chapter-execution-soft-summary">
                {executionSoftSummary(execSoft)}
              </p>
            ) : null}
          </div>
        )}
        <p className="mt-2 text-f11 text-faint">
          只作提醒，不拦你继续生成；要正式定稿时再按提示补齐。
        </p>
      </section>

      <section className="mb-5 space-y-3">
        <div className="flex items-center justify-between gap-2">
          <h4 className="text-f13 font-medium text-ink">元数据</h4>
          <Btn variant="primary" size="sm" data-testid="chapter-meta-ask-chief" onClick={askMeta}>
            让主编写元数据
          </Btn>
        </div>
        <ReadOnlyText label="章节标题" value={title} emptyHint="（空 · 由主编审批写入）" entityLabel={`第 ${seq} 章`} fieldKey="title" />
        <ReadOnlyText label="章节标签" value={labelText} emptyHint="（空 · 由主编审批写入）" entityLabel={`第 ${seq} 章`} fieldKey="label" />
        <ReadOnlyText label="所属卷" value={volTitle} emptyHint="（空 · 由主编审批写入）" entityLabel={`第 ${seq} 章`} fieldKey="volume" />
      </section>

      <section className="mb-5 space-y-4" data-testid="chapter-contract-summaries">
        <div>
          <div className="flex items-center justify-between gap-2 mb-1">
            <h4 className="text-f13 font-medium text-ink">本章大纲</h4>
            <div className="flex gap-1">
              <Btn variant="ghost" size="xs" data-testid="contract-seed-outline" onClick={askOutline}>让主编写大纲</Btn>
              <Btn variant="ghost" size="xs" onClick={() => goPhase('outline')}>深编</Btn>
            </div>
          </div>
          <p className="text-f13 text-ink whitespace-pre-wrap leading-relaxed min-h-[2rem] rounded-md border border-line/40 bg-canvas/50 px-3 py-2">
            {clip(synopsis, SYNOPSIS_PREVIEW) || (
              <span className="text-faint">（空 · 写前建议补齐大纲）</span>
            )}
          </p>
        </div>

        <div>
          <div className="flex items-center justify-between gap-2 mb-1">
            <h4 className="text-f13 font-medium text-ink">节拍（{beatTexts.length} 条）</h4>
            <div className="flex gap-1">
              <Btn variant="ghost" size="xs" data-testid="contract-seed-beats" onClick={askBeats}>让主编写节拍</Btn>
              <Btn variant="ghost" size="xs" onClick={() => goPhase('beats')}>深编</Btn>
            </div>
          </div>
          {beatTexts.length === 0 ? (
            <p className="text-f13 text-faint px-1">（空 · 建议至少 3 条非空节拍）</p>
          ) : (
            <ol className="list-decimal list-inside space-y-1 text-f13 text-ink">
              {beatTexts.slice(0, BEATS_PREVIEW).map((t, i) => (
                <li key={i} className="truncate" title={t}>{t}</li>
              ))}
              {beatTexts.length > BEATS_PREVIEW && (
                <li className="list-none text-faint pl-0">
                  …另有 {beatTexts.length - BEATS_PREVIEW} 条，点「深编」查看
                </li>
              )}
            </ol>
          )}
        </div>

        <div>
          <div className="flex items-center justify-between gap-2 mb-1">
            <h4 className="text-f13 font-medium text-ink">场景真相</h4>
            <div className="flex gap-1">
              <Btn variant="ghost" size="xs" data-testid="contract-seed-truth" onClick={askTruth}>去补/写真相</Btn>
            </div>
          </div>
          <p className="text-f13 text-ink whitespace-pre-wrap leading-relaxed min-h-[2rem] rounded-md border border-line/40 bg-canvas/50 px-3 py-2">
            {clip(sceneTruth, TRUTH_PREVIEW) || (
              <span className="text-faint">（空 · 存实质正文时工艺门可能硬拦）</span>
            )}
          </p>
        </div>
      </section>

      <section className="mb-4" data-testid="chapter-contract-related">
        <h4 className="text-f13 font-medium text-ink mb-2">相关</h4>
        <div className="flex flex-wrap gap-2">
          <Btn
            variant="soft"
            size="sm"
            data-testid="contract-open-brief"
            onClick={() => {
              if (typeof onOpenAux === 'function') onOpenAux('brief')
              else onClose?.()
            }}
          >
            章前简报{briefHint ? ` · ${briefHint}` : ''}
          </Btn>
          <Btn
            variant="soft"
            size="sm"
            data-testid="contract-open-pressure"
            onClick={() => {
              if (typeof onOpenAux === 'function') onOpenAux('pressure')
              else onClose?.()
            }}
          >
            压力合同
          </Btn>
          <Btn
            variant="ghost"
            size="sm"
            data-testid="contract-open-frame"
            onClick={() => {
              if (typeof onOpenAux === 'function') onOpenAux('frame')
              else onClose?.()
            }}
          >
            视角帧
          </Btn>
        </div>
        <p className="mt-2 text-f11 text-faint">图谱/弧光请从左侧 App 轨进入；本页不内嵌编辑。</p>
      </section>

      <div className="mt-4 flex justify-end gap-2">
        <Btn variant="ghost" onClick={onClose}>关闭</Btn>
      </div>
    </div>
  )
}
