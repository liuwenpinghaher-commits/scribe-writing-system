import { useEffect, useMemo, useState } from 'react'
import { api } from '../api'
import { wcLabel } from '../outlineColors'
import { showToast } from '../ui/Toast'
import { Btn, Input, Textarea, SectionTitle } from '../ui.jsx'
import { seedChiefNarrativeWrite } from '../lib/chiefSeed.js'
import { buildAddVolumeSeed, buildPatchVolumeSeed } from '../lib/volumeSeed.js'
import { loadIaDensity, volumeReviewVisible } from '../lib/iaDensity.js'
import { volumeReviewPlain } from '../lib/volumeSoftHint.js'
import {
  chapterAccountLine,
  introLooksLikeOneChapterNight,
  pendingOutlineLine,
  volumePendingHuman,
  volumeRemainingWork,
} from '../lib/volumeLedger.js'
import { parseVolumeCharter } from '../lib/volumeCharter.js'

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

function CharterLine({ item }) {
  const main = item.oid || item.key || item.what
  const sub = item.why || (item.key && item.what ? item.what : '')
  return (
    <li className="text-f12 leading-relaxed text-ink">
      <span>{main}</span>
      {sub ? <span className="text-faint"> · {sub}</span> : null}
    </li>
  )
}

function CharterReadout({ charter }) {
  const c = parseVolumeCharter(charter)
  if (!c) {
    return (
      <section data-testid="volume-charter-readout" className="text-f12 text-faint leading-relaxed">
        这一卷还没有契约。作者看不见的机制等于不存在。
      </section>
    )
  }
  return (
    <section data-testid="volume-charter-readout" className="space-y-3">
      <SectionTitle>卷契约</SectionTitle>
      {c.duty ? <p className="text-f13 leading-relaxed text-ink">{c.duty}</p> : null}
      {c.introduces.length ? (
        <div>
          <div className="text-meta text-faint uppercase tracking-wider mb-1">引入</div>
          <ul className="grid gap-0.5">{c.introduces.map((item, i) => <CharterLine key={`i${i}`} item={item} />)}</ul>
        </div>
      ) : null}
      {c.thickens.length ? (
        <div>
          <div className="text-meta text-faint uppercase tracking-wider mb-1">写厚</div>
          <ul className="grid gap-0.5">{c.thickens.map((item, i) => <CharterLine key={`t${i}`} item={item} />)}</ul>
        </div>
      ) : null}
      {c.pays.length ? (
        <div>
          <div className="text-meta text-faint uppercase tracking-wider mb-1">收线</div>
          <ul className="grid gap-0.5">{c.pays.map((p, i) => <li key={`p${i}`} className="text-f12 text-ink">{p}</li>)}</ul>
        </div>
      ) : null}
      {c.mustKnow.length ? (
        <div>
          <div className="text-meta text-faint uppercase tracking-wider mb-1">卷末须知</div>
          <ul className="grid gap-0.5">{c.mustKnow.map((item, i) => <CharterLine key={`k${i}`} item={item} />)}</ul>
        </div>
      ) : null}
      {c.mustNotKnow.length ? (
        <div>
          <div className="text-meta text-faint uppercase tracking-wider mb-1">卷末不许知</div>
          <ul className="grid gap-0.5">{c.mustNotKnow.map((item, i) => <CharterLine key={`n${i}`} item={item} />)}</ul>
        </div>
      ) : null}
    </section>
  )
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
  const [gaps, setGaps] = useState(null)

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

  useEffect(() => {
    let alive = true
    if (typeof api.codexCompleteness !== 'function') {
      setGaps(null)
      return undefined
    }
    api.codexCompleteness()
      .then((r) => { if (alive) setGaps(r) })
      .catch(() => { if (alive) setGaps(null) })
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
    const introChanged = String(form.intro || '') !== String(savedSnap?.intro || '')
    const seed = buildPatchVolumeSeed({
      volumeId: vid,
      title: form.title,
      color: form.color,
      sort_order: form.sort_order,
      ...(introChanged ? { intro: form.intro } : {}),
      chapters,
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
      chapters,
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
              卷纲要对着这一卷每一章各写一笔账，禁止只写其中一章的夜。
              下方是本地草稿，不会直接入库；点「让主编写入」经主编审批后才会落库。
            </p>
            {introLooksLikeOneChapterNight(form.intro, chapters) ? (
              <p className="mb-2 text-f12 text-warn leading-relaxed" data-testid="volume-intro-one-night">
                这一卷有好几章，卷纲现在读起来像只写了其中一章的夜。可以先存，但最好按章把各办哪一件写清。
              </p>
            ) : null}
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
                  placeholder="按本卷每一章各写一笔账，禁止只写其中一章的夜。"
                  className="min-h-40"
                />
              </FieldLabel>
            </div>
            <p className="mt-2 text-meta text-faint">
              volume_id=<code className="text-meta">{vid}</code>
              {' · '}无 REST 叙事直写 · WRITE_GATED
            </p>
          </section>

          <CharterReadout charter={volume.charter} />

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
                  className="grid w-full grid-cols-[minmax(0,1fr)_auto_auto_auto] items-start gap-3 py-2 text-left text-f13 hover:bg-soft/50 cursor-pointer"
                >
                  <span className="min-w-0">
                    <span className="block truncate font-medium text-ink">{`${chapter.seq} ${chapter.title || ''}`.trim()}</span>
                    <span className="block text-f12 text-faint mt-0.5 leading-snug">{chapterAccountLine(chapter)}</span>
                    {String(chapter.settled_note || '').trim() ? (
                      <span className="block text-f12 text-ink mt-0.5 leading-snug" data-testid="chapter-settled-note">{chapter.settled_note}</span>
                    ) : null}
                  </span>
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
          <section data-testid="volume-pending-human">
            <div className="text-meta text-faint uppercase tracking-wider mb-2">纲改过还没核完的</div>
            <div className="space-y-1.5">
              {volumePendingHuman(outline, vid).length === 0 ? (
                <div className="text-faint">这一卷眼下没有要你核的章。</div>
              ) : (
                <>
                  {volumePendingHuman(outline, vid).map((ch) => (
                    <div key={ch.seq} className="text-ink leading-snug">
                      {pendingOutlineLine(ch)}
                    </div>
                  ))}
                  <div className="text-faint leading-snug">对话里续写不拦，那是逃生口。正规写演绎和草稿，核完了对主编说冻回这一卷。</div>
                </>
              )}
            </div>
          </section>
          <section data-testid="volume-remaining-later">
            <div className="text-meta text-faint uppercase tracking-wider mb-2">本卷还要办的</div>
            <div className="space-y-1.5">
              {volumeRemainingWork(outline, vid).length === 0 ? (
                <div className="text-faint">这一卷眼下没有还没办的章。</div>
              ) : volumeRemainingWork(outline, vid).map((ch) => (
                <div key={ch.seq} className="text-ink leading-snug">
                  第{ch.seq}章《{ch.title || ''}》
                </div>
              ))}
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
          <section data-testid="volume-setting-gaps">
            <div className="text-meta text-faint uppercase tracking-wider mb-2">设定还缺什么</div>
            <div className="space-y-1.5">
              {!(gaps?.report?.missing_dimensions || []).length && !(gaps?.report?.char_issues || []).length ? (
                <div className="text-faint">眼下没报缺口。缺什么只告诉你，不挡开写。</div>
              ) : (
                <>
                  {(gaps?.report?.missing_dimensions || []).map((line) => (
                    <div key={line} className="text-ink leading-snug">{line}</div>
                  ))}
                  {(gaps?.report?.char_issues || []).map((row) => (
                    <div key={row.name} className="text-ink leading-snug">
                      {row.name}：{(row.issues || []).join('、')}
                    </div>
                  ))}
                </>
              )}
            </div>
          </section>
        </aside>
      </div>
    </section>
  )
}
