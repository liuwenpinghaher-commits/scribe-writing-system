import { useEffect, useMemo, useState } from 'react'
import { api } from '../api'
import { wcLabel } from '../outlineColors'
import { showToast } from '../ui/Toast'
import { Btn, Input, Textarea, SectionTitle } from '../ui.jsx'
import { seedChiefNarrativeWrite } from '../lib/chiefSeed.js'
import { buildAddVolumeSeed, buildPatchVolumeSeed } from '../lib/volumeSeed.js'
import { loadIaDensity, volumeReviewVisible } from '../lib/iaDensity.js'
import { volumeReviewPlain } from '../lib/volumeSoftHint.js'

function volumeIdOf(node) {
  if (node?.ref != null) return node.ref
  const id = String(node?.id || '')
  if (!id.startsWith('vol:')) return null
  const raw = id.slice(4)
  return raw && raw !== 'null' ? raw : null
}

function chapterNode(chapter) {
  return {
    id: `ch:${chapter.seq}`,
    type: 'chapter',
    ref: chapter.seq,
    label: `${chapter.seq} ${chapter.title || ''}`.trim(),
    phase: 'outline',
  }
}

function FieldLabel({ children }) {
  return <label className="grid gap-1 text-meta text-faint uppercase tracking-wider">{children}</label>
}

export function VolumeDetailPane({ node, onSelectNode, onChanged }) {
  const vid = volumeIdOf(node)
  const [outline, setOutline] = useState(null)
  const [loading, setLoading] = useState(true)
  const [err, setErr] = useState('')
  const [saving, setSaving] = useState(false)
  // 本地草稿缓冲（正式卷/未分卷共用 form；落库仅走主编种子）
  const [form, setForm] = useState({ title: '', intro: '', color: '', sort_order: 0 })
  const [savedSnap, setSavedSnap] = useState(null)
  const [kr4, setKr4] = useState(null)

  const reload = () => {
    setLoading(true)
    setErr('')
    return api.outline()
      .then((data) => {
        const nextOutline = data || { volumes: [], chapters: [] }
        const nextVolume = (nextOutline.volumes || [])
          .find((v) => String(v.id) === String(vid)) || null
        setOutline(nextOutline)
        if (vid == null) {
          setForm({ title: '', intro: '', color: '', sort_order: 0 })
          setSavedSnap(null)
        } else {
          const nextForm = {
            title: nextVolume?.title || node?.label || '未命名卷',
            intro: nextVolume?.intro || '',
            color: nextVolume?.color || '',
            sort_order: nextVolume?.sort_order ?? 0,
          }
          setForm(nextForm)
          setSavedSnap({ ...nextForm })
        }
        setErr('')
      })
      .catch((e) => {
        setOutline(null)
        setErr(e?.body?.detail || e?.message || '卷信息加载失败')
      })
      .finally(() => setLoading(false))
  }

  useEffect(() => { reload() }, [vid]) // eslint-disable-line react-hooks/exhaustive-deps

  // full 密度：可选挂 GET /volume/review（复用现网，无新路由）
  useEffect(() => {
    if (vid == null || !volumeReviewVisible(loadIaDensity())) {
      setKr4(null)
      return undefined
    }
    let alive = true
    if (typeof api.volumeReview !== 'function') {
      setKr4(null)
      return undefined
    }
    api.volumeReview(vid)
      .then((r) => { if (alive) setKr4(r) })
      .catch(() => { if (alive) setKr4(null) })
    return () => { alive = false }
  }, [vid])

  const volume = useMemo(() => {
    const volumes = outline?.volumes || []
    return volumes.find((v) => String(v.id) === String(vid)) || null
  }, [outline, vid])

  const chapters = useMemo(() => {
    const rows = outline?.chapters || []
    return rows.filter((c) => String(c.volume ?? '') === String(vid ?? ''))
  }, [outline, vid])

  const dirty = useMemo(() => {
    if (vid == null || !savedSnap) return false
    return (
      String(form.title || '') !== String(savedSnap.title || '')
      || String(form.intro || '') !== String(savedSnap.intro || '')
      || String(form.color || '') !== String(savedSnap.color || '')
      || String(form.sort_order ?? '') !== String(savedSnap.sort_order ?? '')
    )
  }, [form, savedSnap, vid])

  const totalWords = chapters.reduce((sum, c) => sum + (c.word_count || 0), 0)
  const statusCounts = chapters.reduce((map, c) => {
    const key = c.label || '未设'
    map[key] = (map[key] || 0) + 1
    return map
  }, {})

  /** 正式卷：种子必须含 s3_patch_volume + volume_id（S4） */
  const askChiefVolume = () => {
    if (vid == null) return
    const seed = buildPatchVolumeSeed({
      volumeId: vid,
      title: form.title,
      intro: form.intro,
      color: form.color,
      sort_order: form.sort_order,
    })
    seedChiefNarrativeWrite(
      'volume',
      `分卷「${volume?.title || form.title || vid}」`,
      seed,
    )
  }

  // 结构创建禁止 REST 直写;主编 s3_add_chapter / s3_add_volume 审批
  const createChapter = () => {
    if (saving) return
    const volHint = vid != null
      ? `请归属 volume_id=${vid}（卷「${volume?.title || form.title || vid}」）。`
      : '可不指定卷。'
    seedChiefNarrativeWrite(
      'chapter',
      '新建章节',
      `请用 s3_add_chapter 新建一章。${volHint}未获批准不得声称已落库。`,
    )
  }

  const createFromUnassigned = () => {
    if (vid != null || saving) return
    const title = form.title.trim()
    if (!title) {
      showToast('请先填写新卷名', { tone: 'warn' })
      return
    }
    const maxOrder = (outline?.volumes || []).reduce((max, v) => Math.max(max, v.sort_order ?? 0), 0)
    const seed = buildAddVolumeSeed({
      title,
      intro: form.intro,
      color: form.color,
      sort_order: maxOrder + 1,
      chapterSeqs: chapters.map((c) => c.seq),
    })
    seedChiefNarrativeWrite(
      'volume',
      `从「未分卷」创建正式分卷「${title}」`,
      seed,
    )
  }

  const resetDraft = () => {
    if (savedSnap) setForm({ ...savedSnap })
  }

  if (loading) return <div className="p-8 text-f13 text-faint/60">加载卷信息…</div>
  if (err) {
    return (
      <div className="h-full grid place-items-center px-6 text-center">
        <div role="alert" className="max-w-md rounded-lg border border-danger/30 bg-danger/5 px-4 py-3 text-f13 text-danger">
          <div>{err}</div>
          <Btn variant="soft" size="sm" className="mt-3" onClick={reload}>重试</Btn>
        </div>
      </div>
    )
  }

  if (vid == null) {
    return (
      <section data-testid="volume-detail-pane" className="h-full min-h-0 overflow-y-auto bg-canvas">
        <header className="border-b border-line/40 px-5 py-2.5">
          <div className="text-meta text-faint">手稿 / 未分卷</div>
          <div className="mt-0.5 flex min-w-0 items-baseline gap-3">
            <h2 className="min-w-0 flex-1 truncate type-section text-ink">{node?.label || '未分卷'}</h2>
            <span className="text-meta text-faint shrink-0">{chapters.length} 章 · {wcLabel(totalWords)} 字</span>
          </div>
        </header>
        <div className="grid gap-8 px-5 py-4 lg:grid-cols-[minmax(0,1fr)_14rem]">
          <section>
            <SectionTitle>创建正式分卷</SectionTitle>
            <div className="mb-4 text-f12 leading-relaxed text-faint">
              未分卷只是暂存分组。创建正式分卷后,这些章节会归入新卷,卷纲保存到新卷档案。
            </div>
            <div className="grid gap-3">
              <FieldLabel>
                新卷名
                <Input variant="bordered" aria-label="新卷名" value={form.title}
                  onChange={(e) => setForm((f) => ({ ...f, title: e.target.value }))} placeholder="第一卷" />
              </FieldLabel>
              <FieldLabel>
                标识色
                <Input variant="bordered" value={form.color}
                  onChange={(e) => setForm((f) => ({ ...f, color: e.target.value }))} placeholder="#2f7563" />
              </FieldLabel>
              <FieldLabel>
                卷排序
                <Input variant="bordered" aria-label="卷排序" type="number" min="0" step="1" value={form.sort_order}
                  onChange={(e) => setForm((f) => ({ ...f, sort_order: e.target.value }))} />
              </FieldLabel>
              <FieldLabel>
                新卷卷纲
                <Textarea variant="bordered" aria-label="新卷卷纲" value={form.intro}
                  onChange={(e) => setForm((f) => ({ ...f, intro: e.target.value }))} rows={8}
                  placeholder="写这个新分卷的主冲突、角色弧线、伏笔收束。" className="min-h-40" />
              </FieldLabel>
              <div className="flex justify-end">
                <Btn variant="primary" data-testid="volume-create-from-unassigned"
                  onClick={createFromUnassigned} disabled={saving}>
                  让主编创建分卷
                </Btn>
              </div>
            </div>
          </section>
          <aside className="border-t border-line pt-4 lg:border-t-0 lg:border-l lg:pl-5 lg:pt-0">
            <SectionTitle>将收纳章节</SectionTitle>
            <div className="grid gap-0.5">
              {chapters.length === 0 ? (
                <div className="text-f12 text-faint">暂无未分卷章节。</div>
              ) : chapters.map((chapter) => (
                <button
                  key={chapter.seq}
                  type="button"
                  onClick={() => onSelectNode?.(chapterNode(chapter))}
                  className="grid w-full grid-cols-[minmax(0,1fr)_auto] items-center gap-3 rounded-md px-2 py-1.5 text-left text-f12 hover:bg-soft cursor-pointer"
                >
                  <span className="min-w-0 truncate text-ink">{`${chapter.seq} ${chapter.title || ''}`.trim()}</span>
                  <span className="text-faint">{wcLabel(chapter.word_count)} 字</span>
                </button>
              ))}
            </div>
          </aside>
        </div>
      </section>
    )
  }

  if (!volume) {
    return (
      <div className="h-full grid place-items-center px-6 text-center text-f13 text-faint/60">
        该分卷还没有可编辑的卷记录。
      </div>
    )
  }

  return (
    <section data-testid="volume-detail-pane" className="h-full min-h-0 overflow-y-auto bg-canvas">
      <header className="border-b border-line/40 px-5 py-2.5">
        <div className="text-meta text-faint">手稿 / 分卷 · 按需后建卷</div>
        <div className="mt-0.5 flex min-w-0 items-baseline gap-3">
          <h2 className="min-w-0 flex-1 truncate type-section text-ink">{volume.title || node.label || '未命名卷'}</h2>
          <span className="text-meta text-faint shrink-0">{chapters.length} 章 · {wcLabel(totalWords)} 字</span>
        </div>
      </header>

      <div className="grid gap-8 px-5 py-4 lg:grid-cols-[minmax(0,1fr)_14rem]">
        <div className="min-w-0 space-y-6">
          {/* 正式卷：本地草稿缓冲 + 主编 s3_patch_volume（无 REST 叙事保存） */}
          <section data-testid="volume-meta-draft">
            <div className="flex flex-wrap items-center justify-between gap-3 mb-2">
              <SectionTitle>卷信息 / 卷纲</SectionTitle>
              <div className="flex flex-wrap items-center gap-2">
                {dirty && (
                  <span className="text-meta text-warn" data-testid="volume-draft-dirty">有未提交草稿</span>
                )}
                {dirty && (
                  <Btn variant="ghost" size="sm" data-testid="volume-draft-reset" onClick={resetDraft}>
                    还原库中值
                  </Btn>
                )}
                <Btn variant="primary" size="sm" data-testid="volume-ask-chief" onClick={askChiefVolume}>
                  让主编写入
                </Btn>
              </div>
            </div>
            <p className="mb-2 text-f12 text-faint leading-relaxed" data-testid="volume-intro-hint">
              卷纲是整卷备忘，不是单章大纲：写本章时系统可能摘一小段当背景；空则跳过。
              下方是本地草稿，不会直接入库；点「让主编写入」经主编审批后才会落库。
            </p>
            <div className="grid gap-3" data-testid="volume-meta-fields">
              <FieldLabel>
                卷名
                <Input
                  variant="bordered"
                  aria-label="卷名"
                  data-testid="volume-draft-title"
                  value={form.title}
                  onChange={(e) => setForm((f) => ({ ...f, title: e.target.value }))}
                />
              </FieldLabel>
              <FieldLabel>
                标识色
                <Input
                  variant="bordered"
                  aria-label="标识色"
                  data-testid="volume-draft-color"
                  value={form.color}
                  onChange={(e) => setForm((f) => ({ ...f, color: e.target.value }))}
                  placeholder="#2f7563"
                />
              </FieldLabel>
              <FieldLabel>
                卷排序
                <Input
                  variant="bordered"
                  aria-label="卷排序"
                  type="number"
                  min="0"
                  step="1"
                  data-testid="volume-draft-sort"
                  value={form.sort_order}
                  onChange={(e) => setForm((f) => ({ ...f, sort_order: e.target.value }))}
                />
              </FieldLabel>
              <FieldLabel>
                卷纲
                <Textarea
                  variant="bordered"
                  aria-label="卷纲"
                  data-testid="volume-draft-intro"
                  value={form.intro}
                  onChange={(e) => setForm((f) => ({ ...f, intro: e.target.value }))}
                  rows={8}
                  placeholder="本卷主冲突、角色弧、应付的账（这是卷纲，不是单章大纲/节拍）。"
                  className="min-h-40"
                />
              </FieldLabel>
            </div>
            <p className="mt-2 text-meta text-faint">
              volume_id=<code className="text-meta">{vid}</code>
              {' · '}无 REST 叙事直写 · WRITE_GATED
            </p>
          </section>

          <section>
            <SectionTitle right={
              <span className="inline-flex items-center gap-2 normal-case tracking-normal font-normal">
                <Btn variant="ghost" size="xs" data-testid="volume-create-chapter"
                  onClick={createChapter} disabled={saving}>让主编新建章</Btn>
              </span>
            }>本卷章节</SectionTitle>
            <div className="divide-y divide-line/40">
              {chapters.length === 0 ? (
                <div className="py-6 text-f13 text-faint">本卷暂无章节。</div>
              ) : chapters.map((chapter) => (
                <button
                  key={chapter.seq}
                  type="button"
                  onClick={() => onSelectNode?.(chapterNode(chapter))}
                  className="grid w-full grid-cols-[minmax(0,1fr)_auto_auto_auto] items-center gap-3 py-2 text-left text-f13 hover:bg-soft/50 cursor-pointer"
                >
                  <span className="min-w-0 truncate font-medium text-ink">{`${chapter.seq} ${chapter.title || ''}`.trim()}</span>
                  <span className="text-meta text-faint">{chapter.label || '未设'}</span>
                  {!String(chapter.synopsis || '').trim() ? (
                    <span className="text-meta text-warn" title="本章还没有写大纲">缺大纲</span>
                  ) : (
                    <span className="text-meta text-faint" aria-hidden>·</span>
                  )}
                  <span className="text-meta text-faint">{wcLabel(chapter.word_count)} 字</span>
                </button>
              ))}
            </div>
          </section>
        </div>

        <aside className="min-w-0 space-y-5 text-f12">
          <section>
            <div className="text-meta text-faint uppercase tracking-wider mb-2">卷概览</div>
            <div className="space-y-1.5">
              <div className="flex justify-between gap-3"><span className="text-faint">章节</span><span className="text-ink tnum">{chapters.length}</span></div>
              <div className="flex justify-between gap-3"><span className="text-faint">字数</span><span className="text-ink">{wcLabel(totalWords)}</span></div>
              <div className="flex justify-between gap-3"><span className="text-faint">排序</span><span className="text-ink tnum">{volume.sort_order ?? '—'}</span></div>
            </div>
          </section>
          <section>
            <div className="text-meta text-faint uppercase tracking-wider mb-2">状态</div>
            <div className="space-y-1.5">
              {Object.keys(statusCounts).length === 0 ? (
                <div className="text-faint">—</div>
              ) : Object.entries(statusCounts).map(([label, count]) => (
                <div key={label} className="flex justify-between gap-3">
                  <span className="text-faint">{label}</span>
                  <span className="text-ink tnum">{count}</span>
                </div>
              ))}
            </div>
          </section>
          {volumeReviewPlain(kr4) ? (
            <section data-testid="volume-kr4-review">
              <div className="text-meta text-faint uppercase tracking-wider mb-2">这几章还欠什么</div>
              <p className="text-faint leading-snug break-words">{volumeReviewPlain(kr4)}</p>
            </section>
          ) : null}
        </aside>
      </div>
    </section>
  )
}
