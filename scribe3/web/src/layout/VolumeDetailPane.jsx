import { useEffect, useMemo, useState } from 'react'
import { api } from '../api'
import { wcLabel } from '../outlineColors'
import { showToast } from '../ui/Toast'
import { Btn, Input, Textarea, SectionTitle } from '../ui.jsx'
import { seedChiefNarrativeWrite } from '../lib/chiefSeed.js'
import { ReadOnlyText } from '../ui/EditableText.jsx'

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
  const [form, setForm] = useState({ title: '', intro: '', color: '', sort_order: 0 })

  const reload = () => {
    setLoading(true)
    setErr('')
    return api.outline()
      .then((data) => {
        const nextOutline = data || { volumes: [], chapters: [] }
        const nextVolume = (nextOutline.volumes || [])
          .find((v) => String(v.id) === String(vid)) || null
        setOutline(nextOutline)
        setForm(vid == null
          ? { title: '', intro: '', color: '', sort_order: 0 }
          : {
              title: nextVolume?.title || node?.label || '未命名卷',
              intro: nextVolume?.intro || '',
              color: nextVolume?.color || '',
              sort_order: nextVolume?.sort_order ?? 0,
            })
        setErr('')
      })
      .catch((e) => {
        setOutline(null)
        setErr(e?.body?.detail || e?.message || '卷信息加载失败')
      })
      .finally(() => setLoading(false))
  }

  useEffect(() => { reload() }, [vid]) // eslint-disable-line react-hooks/exhaustive-deps

  const volume = useMemo(() => {
    const volumes = outline?.volumes || []
    return volumes.find((v) => String(v.id) === String(vid)) || null
  }, [outline, vid])

  const chapters = useMemo(() => {
    const rows = outline?.chapters || []
    return rows.filter((c) => String(c.volume ?? '') === String(vid ?? ''))
  }, [outline, vid])

  const totalWords = chapters.reduce((sum, c) => sum + (c.word_count || 0), 0)
  const statusCounts = chapters.reduce((map, c) => {
    const key = c.label || '未设'
    map[key] = (map[key] || 0) + 1
    return map
  }, {})

  const askChiefVolume = () => {
    seedChiefNarrativeWrite(
      'volume',
      `分卷「${volume?.title || form.title || vid}」`,
      `请更新卷 ${vid} 的 title/intro/color/sort_order。当前: title=${form.title}; color=${form.color}; sort_order=${form.sort_order}; intro:\n${form.intro || '（空）'}`,
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
    const chSeqs = chapters.map((c) => c.seq).join(', ')
    seedChiefNarrativeWrite(
      'volume',
      `从「未分卷」创建正式分卷「${title}」`,
      [
        `请用 s3_add_volume 创建卷 title=${title}, sort_order=${maxOrder + 1}`
        + (form.color ? `, color=${form.color}` : '')
        + (form.intro ? `, intro 如下:\n${form.intro}` : '。'),
        chSeqs
          ? `创建后请将未分卷章节 [${chSeqs}] 归入该卷(可用 s3_patch_chapter_meta)。`
          : '',
        '未获批准不得声称已落库。',
      ].filter(Boolean).join('\n'),
    )
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
        <header className="border-b border-line/60 bg-surface/95 px-6 py-4 backdrop-blur-sm">
          <div className="text-meta font-semibold text-faint">手稿 / 未分卷</div>
          <div className="mt-1 flex min-w-0 items-center gap-3">
            <h2 className="min-w-0 flex-1 truncate text-f24 font-semibold tracking-tight leading-tight text-ink">{node?.label || '未分卷'}</h2>
            <span className="rounded-full bg-soft px-2.5 py-1 text-meta text-faint">{chapters.length} 章</span>
            <span className="rounded-full bg-soft px-2.5 py-1 text-meta text-faint">{wcLabel(totalWords)} 字</span>
          </div>
        </header>
        <div className="grid gap-8 px-6 py-5 lg:grid-cols-[minmax(0,1fr)_18rem]">
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
      <header className="border-b border-line/60 bg-surface/95 px-6 py-4 backdrop-blur-sm">
        <div className="text-meta font-semibold text-faint">手稿 / 分卷</div>
        <div className="mt-1 flex min-w-0 items-center gap-3">
          <h2 className="min-w-0 flex-1 truncate text-f24 font-semibold tracking-tight leading-tight text-ink">{volume.title || node.label || '未命名卷'}</h2>
          <span className="rounded-full bg-brand/10 px-2.5 py-1 text-meta text-brand">{chapters.length} 章</span>
          <span className="rounded-full bg-soft px-2.5 py-1 text-meta text-faint">{wcLabel(totalWords)} 字</span>
        </div>
      </header>

      <div className="grid gap-6 px-6 py-5 lg:grid-cols-[minmax(0,1fr)_18rem]">
        <div className="min-w-0 space-y-4">
          <section className="panel-elevated p-5" data-testid="volume-meta-readonly">
            <SectionTitle>卷信息</SectionTitle>
            <div className="grid gap-3">
              <ReadOnlyText label="卷名" value={form.title} />
              <ReadOnlyText label="标识色" value={form.color} emptyHint="—" />
              <ReadOnlyText label="卷排序" value={form.sort_order} />
              <ReadOnlyText label="卷纲" value={form.intro} emptyHint="（空 · 由主编审批写入）" />
              <div className="flex justify-end">
                <Btn variant="primary" data-testid="volume-ask-chief" onClick={askChiefVolume}>
                  让主编写入卷信息
                </Btn>
              </div>
            </div>
          </section>

          <section className="panel-elevated p-5">
            <SectionTitle right={
              <span className="inline-flex items-center gap-2 normal-case tracking-normal font-normal">
                <span className="text-meta text-faint">{chapters.length} 章 · {wcLabel(totalWords)} 字</span>
                <Btn variant="primary" size="xs" data-testid="volume-create-chapter"
                  onClick={createChapter} disabled={saving}>让主编新建章</Btn>
              </span>
            }>本卷章节</SectionTitle>
            <div className="grid gap-0.5">
              {chapters.length === 0 ? (
                <div className="py-8 text-center text-f13 text-faint/60">本卷暂无章节。</div>
              ) : chapters.map((chapter) => (
                <button
                  key={chapter.seq}
                  type="button"
                  onClick={() => onSelectNode?.(chapterNode(chapter))}
                  className="grid w-full grid-cols-[minmax(0,1fr)_auto_auto] items-center gap-3 rounded-xl px-2 py-2 text-left text-f13 hover:bg-soft cursor-pointer"
                >
                  <span className="min-w-0 truncate font-medium text-ink">{`${chapter.seq} ${chapter.title || ''}`.trim()}</span>
                  <span className="text-meta text-faint">{chapter.label || '未设'}</span>
                  <span className="text-meta text-faint">{wcLabel(chapter.word_count)} 字</span>
                </button>
              ))}
            </div>
          </section>
        </div>

        <aside className="min-w-0 space-y-4">
          <section className="panel-elevated p-4">
            <SectionTitle>卷概览</SectionTitle>
            <div className="grid gap-2 text-f12">
              <div className="flex justify-between gap-3 py-1 border-b border-line/40"><span className="text-faint">章节</span><span className="text-ink">{chapters.length}</span></div>
              <div className="flex justify-between gap-3 py-1 border-b border-line/40"><span className="text-faint">字数</span><span className="text-ink">{wcLabel(totalWords)} 字</span></div>
              <div className="flex justify-between gap-3 py-1"><span className="text-faint">排序</span><span className="text-ink">{volume.sort_order ?? '未设'}</span></div>
            </div>
          </section>
          <section className="panel-elevated p-4">
            <SectionTitle>状态分布</SectionTitle>
            <div className="grid gap-1 text-f12">
              {Object.keys(statusCounts).length === 0 ? (
                <div className="text-faint">暂无章节状态。</div>
              ) : Object.entries(statusCounts).map(([label, count]) => (
                <div key={label} className="flex justify-between gap-3 py-1 border-b border-line/40 last:border-0">
                  <span className="text-faint">{label}</span>
                  <span className="text-ink">{count}</span>
                </div>
              ))}
            </div>
          </section>
        </aside>
      </div>
    </section>
  )
}
