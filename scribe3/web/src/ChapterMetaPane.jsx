import { useEffect, useMemo, useState } from 'react'
import { api } from './api'
import { useToast } from './ui/Toast.jsx'
import { Btn } from './ui.jsx'
import { ReadOnlyText } from './ui/EditableText.jsx'
import {
  seedChiefNarrativeWrite,
  seedChapterOutline,
  seedChapterBeats,
} from './lib/chiefSeed.js'
import {
  evaluateChapterContract,
  contractSoftSummary,
  executionSoftSummary,
} from './lib/chapterContractGate.js'
import { softGateIssues } from './lib/deduceGate.js'

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
    Promise.all([api.chapter(seq, work), api.listVolumes()])
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

  const volTitle = volumes.find((v) => String(v.id) === String(volume))?.title || volume || '未分卷'
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
    seedChiefNarrativeWrite(
      'deduce',
      `第 ${seq} 章场景真相`,
      `请填写/完善第 ${seq} 章 scene_truth（场景真相）。当前:\n${sceneTruth || '（空）'}`,
    )
  }

  const askEventDrive = () => {
    const ds = driveSummary || {}
    seedChiefNarrativeWrite(
      'chapter-event-drive',
      `第 ${seq} 章事件驱动`,
      `请按冲突/事件补全第 ${seq} 章：大纲 stakes 标签、对白对立、引爆/对立/章末钩。` +
        `当前驱动：引爆=${ds.inciting || '（空）'}；对立=${ds.opposition || '（空）'}；钩子=${ds.end_hook || '（空）'}。` +
        (execSoft?.soft_fulfill?.gaps?.length
          ? ` 执行 soft gaps：${(execSoft.soft_fulfill.gaps || []).join(', ')}。`
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
          <h3 className="type-section text-ink">章节信息（章前契约）</h3>
          <p className="mt-1 text-f13 text-faint">
            第 {seq} 章 · {title || '未命名'} · {labelText} · 卷 {volTitle}
          </p>
          <p className="mt-0.5 text-f12 text-faint">
            只读合成；大纲/节拍/真相与写作台同源。写入走主编审批，不表单直写。
          </p>
        </div>
        <Btn variant="ghost" size="sm" onClick={onClose}>返回写作</Btn>
      </div>

      <section
        className="mb-5 rounded-lg border border-line/60 bg-surface/60 px-3 py-3"
        data-testid="chapter-contract-checklist"
        aria-label="写前齐套"
      >
        <div className="flex items-center justify-between gap-2 mb-2">
          <h4 className="text-f13 font-medium text-ink">写前齐套（对齐 GATE-B）</h4>
          {contract.hasError ? (
            <span className="text-f12 text-danger" data-testid="contract-attention">
              不建议开写
            </span>
          ) : (
            <span className="text-f12 text-ok">契约可开写</span>
          )}
        </div>
        <ul className="space-y-1.5 text-f13 text-ink">
          <li className="flex items-center gap-2">
            <StatusDot
              ok={contract.synopsisOk && !contract.issues.some((i) => i.id === 'shortSynopsis')}
              warn={contract.synopsisOk && contract.issues.some((i) => i.id === 'shortSynopsis')}
            />
            <span>大纲 synopsis{!contract.synopsisOk ? ' · 空' : contract.issues.some((i) => i.id === 'shortSynopsis') ? ' · 偏短' : ''}</span>
          </li>
          <li className="flex items-center gap-2">
            <StatusDot ok={contract.beatsOk} />
            <span>节拍 beats · {contract.beatCount}/3 条非空</span>
          </li>
          <li className="flex items-center gap-2">
            <StatusDot
              ok={contract.sceneTruthOk && !contract.issues.some((i) => i.id === 'shortSceneTruth')}
              warn={contract.sceneTruthOk && contract.issues.some((i) => i.id === 'shortSceneTruth')}
            />
            <span>场景真相 scene_truth{!contract.sceneTruthOk ? ' · 空' : ''}</span>
          </li>
          <li className="flex items-center gap-2" data-testid="contract-stakes-row">
            <StatusDot
              ok={contract.stakesOk}
              warn={!contract.stakesOk && contract.stakes?.highPressure}
            />
            <span>
              赌注 stakes
              {!contract.stakes?.highPressure
                ? ' · 非高压（可选）'
                : contract.stakesOk
                  ? ` · 已标${contract.stakes?.stakes ? `：${clip(contract.stakes.stakes, 24)}` : ''}`
                  : ' · 高压缺标签（建议）'}
            </span>
          </li>
          <li className="flex items-center gap-2 text-faint">
            <span className="w-2 shrink-0" aria-hidden />
            <span>
              演绎：{doneDeduce}/{involved.length}
              {deduce.stale?.length ? ` · stale ${deduce.stale.length}` : ''}
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
          以上为写前建议，不阻断进入正文或对话生成。
          存实质正文时工艺门仍可能硬拦缺大纲/节拍/场景真相。
        </p>
      </section>

      <section
        className="mb-5 rounded-lg border border-line/60 bg-surface/60 px-3 py-3"
        data-testid="chapter-event-drive"
        aria-label="本章事件驱动"
      >
        <div className="flex items-center justify-between gap-2 mb-2">
          <h4 className="text-f13 font-medium text-ink">本章事件驱动</h4>
          <Btn variant="ghost" size="xs" data-testid="contract-seed-event-drive" onClick={askEventDrive}>
            让主编按驱动补 stakes/对白
          </Btn>
        </div>
        {driveSummary?.present ? (
          <ul className="space-y-1.5 text-f13 text-ink">
            <li><span className="text-faint">引爆 · </span>{driveSummary.inciting || '（空）'}</li>
            <li><span className="text-faint">对立 · </span>{driveSummary.opposition || '（空）'}</li>
            <li><span className="text-faint">钩子 · </span>{driveSummary.end_hook || '（空）'}</li>
            {driveSummary.scene_turn ? (
              <li><span className="text-faint">转折 · </span>{driveSummary.scene_turn}</li>
            ) : null}
          </ul>
        ) : (
          <p className="text-f13 text-faint">
            尚未合成事件驱动 · 可进大纲补 stakes/冲突，或跑 pilot / ensure 后刷新。
          </p>
        )}
        <p className="mt-2 text-f11 text-faint">只读 · 真源 narrative_drive；引导优先，不默认硬 park。</p>
      </section>

      <section
        className="mb-5 rounded-lg border border-line/60 bg-surface/60 px-3 py-3"
        data-testid="chapter-execution-soft"
        aria-label="写后执行对照"
      >
        <h4 className="text-f13 font-medium text-ink mb-2">写后执行对照</h4>
        {!execSoft ? (
          <p className="text-f13 text-faint">加载中或暂不可用…</p>
        ) : !execSoft.has_prose ? (
          <p className="text-f13 text-faint">尚无正文 · 成稿后显示 soft 对白/长度 gaps 与 drift（advisory）。</p>
        ) : (
          <div className="space-y-1.5 text-f13 text-ink">
            {execSoft.soft_fulfill ? (
              <>
                <p>
                  <span className="text-faint">状态 · </span>
                  {execSoft.soft_fulfill.ok_soft
                    ? 'soft 通过'
                    : `建议关注：${(execSoft.soft_fulfill.gaps || []).map(gapLabel).join('、') || '未达标'}`}
                  <span className="text-faint"> · {execSoft.soft_fulfill.severity || 'advisory'}</span>
                </p>
                <p className="text-faint tnum">
                  引号 {execSoft.soft_fulfill.quotes ?? '—'}
                  {execSoft.soft_fulfill.prose_cn != null ? ` · 可见字 ${execSoft.soft_fulfill.prose_cn}` : ''}
                </p>
              </>
            ) : (
              <p className="text-faint">无 soft_fulfill 数据</p>
            )}
            {execSoft.drift?.drift ? (
              <p className="text-warn" data-testid="chapter-execution-drift">
                drift · {execSoft.drift.advisory || '事件驱动相对成稿已变，建议【强制重写】核对（不自动清稿）'}
              </p>
            ) : (
              <p className="text-faint">drift · 无（或尚未打 stamp）</p>
            )}
            {executionSoftSummary(execSoft) ? (
              <p className="text-f12 text-warn" data-testid="chapter-execution-soft-summary">
                {executionSoftSummary(execSoft)}
              </p>
            ) : null}
          </div>
        )}
        <p className="mt-2 text-f11 text-faint">
          与 full_check soft_fulfill 同源 · 仅 advisory，不阻断生成。
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
