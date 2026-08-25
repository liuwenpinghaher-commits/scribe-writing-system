/**
 * 图谱节点戏剧操作台（PR-A）。
 * 三层：顶栏身份/度数 · 分类型中部 · 底栏 CTA。
 */
import { useEffect, useMemo, useState } from 'react'
import { X, Crosshair, Lock, MessageSquare, BookOpen, Loader2 } from 'lucide-react'
import { api } from '../../api'
import {
  atlasNavType,
  neighborsOf,
  knowledgeDiffSubgraph,
  displayNodeLabel,
  formatArcLine,
  resolveExpandCharacterId,
  edgeLabel,
  propositionListLabel,
  humanizeFactId,
  SECRET_PLACEHOLDER,
} from '../../lib/atlasNodeDetail.js'
import { seedAtlasDiscuss, seedAtlasNextStroke } from '../../lib/atlasChiefSeed.js'
import { InputDialog } from '../../ui/Dialog.jsx'
import { withFeedback } from '../../lib/withFeedback.js'

const ALIGN_ZH = {
  overdue_miss: '逾期·偏离',
  overdue_unmeasured: '逾期·未测',
  overdue_no_target: '逾期·无目标',
  due: '本章应达',
  approaching: '临近',
  no_plan: '无里程碑',
  passed_all: '节拍已过完',
  cold: '冷启动',
}

function typeLabel(t) {
  if (t === 'character') return '角色'
  if (t === 'faction') return '势力'
  if (t === 'item') return '物件'
  if (t === 'proposition') return '命题'
  return t || '节点'
}

function typeDot(type, secret) {
  if (type === 'character') return 'var(--color-brand)'
  if (type === 'faction') return 'var(--color-secret)'
  if (type === 'item') return 'var(--color-line)'
  if (secret) return 'var(--color-secret)'
  return 'var(--color-irony)'
}

export function NodeDetail({
  node,
  focus,
  hop = 1,
  edges = [],
  nodes = [],
  focusLabel = '',
  sliceChapter = null,
  maxChapter = 0,
  layout = 'overlay',
  onExpand,
  onHopBoost,
  onOpenNode,
  onClose,
}) {
  const [arc, setArc] = useState(null) // { loading, line, err }
  const [stateDlg, setStateDlg] = useState(false)
  const [stateBusy, setStateBusy] = useState(false)
  const nodeId = node?.id

  const nb = useMemo(
    () => (nodeId ? neighborsOf(nodeId, edges, nodes, focus) : null),
    [nodeId, edges, nodes, focus],
  )
  const diff = useMemo(
    () => (nodeId && focus
      ? knowledgeDiffSubgraph(nodeId, focus, edges, nodes, { hop })
      : null),
    [nodeId, focus, edges, nodes, hop],
  )

  // 角色弧光一行 fail-soft
  useEffect(() => {
    if (!node || atlasNavType(node) !== 'character') {
      setArc(null)
      return
    }
    let alive = true
    setArc({ loading: true })
    const nextCh = sliceChapter != null
      ? Number(sliceChapter) + 1
      : (maxChapter > 0 ? maxChapter + 1 : 1)
    const p = typeof api.charAnchors === 'function'
      ? api.charAnchors(node.id, { next_ch: nextCh })
      : Promise.resolve(null)
    p.then((r) => {
      if (!alive) return
      const line = formatArcLine(r?.alignment, r?.anchors)
      setArc({ loading: false, line, raw: r })
    }).catch((e) => {
      if (!alive) return
      setArc({ loading: false, err: e?.message || '弧光加载失败' })
    })
    return () => { alive = false }
  }, [node?.id, node?.type, sliceChapter, maxChapter])

  if (!node || !nb) return null

  const t = atlasNavType(node)
  const title = displayNodeLabel(node)
  const expandId = resolveExpandCharacterId(node, edges, nodes)

  const openCodex = () => {
    onOpenNode?.({
      id: node.id,
      type: t,
      label: node.secret ? SECRET_PLACEHOLDER : (node.label || node.id),
      secret: !!node.secret,
    })
  }

  const askChief = () => {
    const relSummary = (nb.relEdges || []).slice(0, 4)
      .map((r) => `${r.relLabel}→${r.peerLabel}`)
      .join('；')
    seedAtlasDiscuss(node, {
      hop,
      focusId: focus,
      focusLabel: focusLabel || focus,
      degree: nb.degree,
      arcLine: arc?.line?.text,
      relSummary,
    })
  }

  const askNextStroke = () => {
    seedAtlasNextStroke(node, {
      chapter: sliceChapter,
      focusId: focus,
      focusLabel: focusLabel || focus,
      onlyFocus: diff?.onlyFocus,
      onlySelf: diff?.isSelfFocus ? diff.focusKnownPreview : diff?.onlySelf,
    })
  }

  return (
    <div
      data-testid="atlas-node-detail"
      className={layout === 'pane'
        ? 'w-80 sm:w-96 shrink-0 h-full overflow-y-auto border-l border-line/70 bg-surface p-3.5 flex flex-col gap-2.5'
        : 'absolute top-3 right-3 z-20 w-80 sm:w-96 max-w-[calc(100%-1.5rem)] rounded-md border border-line/70 bg-surface/95 backdrop-blur p-3.5 flex flex-col gap-2.5 shadow-[var(--shadow-card)]'}
    >
      {/* 顶栏 */}
      <div className="flex items-start gap-2">
        <span className="text-f14 font-medium text-ink leading-snug flex-1 break-words min-w-0">
          {node.secret
            ? <span className="inline-flex items-center gap-1"><Lock size={13} />{SECRET_PLACEHOLDER}</span>
            : title}
        </span>
        <button type="button" onClick={onClose} className="text-faint hover:text-ink shrink-0 mt-0.5" aria-label="关闭详情">
          <X size={14} />
        </button>
      </div>
      <div className="flex flex-wrap items-center gap-2 text-f12 text-faint">
        <span className="inline-flex items-center gap-1.5">
          <i className="w-2.5 h-2.5 rounded-full inline-block" style={{ background: typeDot(t, node.secret) }} />
          {typeLabel(t)}
          {node.id === focus && <span className="text-brand">· 中心</span>}
        </span>
        <span
          className="tnum"
          title={`关系 ${nb.relDegree} · 知情 ${nb.knowsDegree}`}
        >
          度数 {nb.degree}
        </span>
      </div>

      {/* 中部 */}
      <div className="max-h-[min(50vh,360px)] overflow-y-auto flex flex-col gap-2.5 text-f12 border-t border-line/40 pt-2">
        {t === 'character' && (
          <CharacterFacet
            node={node}
            focus={focus}
            hop={hop}
            nb={nb}
            diff={diff}
            arc={arc}
            onHopBoost={onHopBoost}
          />
        )}
        {t === 'proposition' && (
          <PropositionFacet node={node} nb={nb} />
        )}
        {(t === 'faction' || t === 'item') && (
          <EntityFacet type={t} nb={nb} />
        )}
      </div>

      {/* 底栏 CTA */}
      <div className="flex flex-col gap-1.5 border-t border-line/40 pt-2">
        <button
          type="button"
          data-testid="atlas-ask-chief"
          onClick={askChief}
          className="inline-flex items-center justify-center gap-1.5 h-8 rounded-lg bg-brand text-brandfg text-f13 font-medium hover:opacity-90 cursor-pointer"
        >
          <MessageSquare size={13} /> 问主编
        </button>
        <button
          type="button"
          data-testid="atlas-next-stroke"
          onClick={askNextStroke}
          className="inline-flex items-center justify-center gap-1.5 h-8 rounded-lg border border-line text-f13 text-ink hover:border-brand cursor-pointer"
        >
          用这个信息差写下一笔
        </button>
        <button
          type="button"
          data-testid="atlas-open-codex"
          onClick={openCodex}
          className="inline-flex items-center justify-center gap-1.5 h-8 rounded-lg text-f13 text-ink hover:bg-soft cursor-pointer"
        >
          <BookOpen size={13} /> 打开设定
        </button>
        {t === 'character' && (
          <button
            type="button"
            data-testid="atlas-mark-char-state"
            disabled={stateBusy}
            onClick={() => setStateDlg(true)}
            className="inline-flex items-center justify-center gap-1.5 h-8 rounded-lg border border-line text-f13 text-ink hover:border-brand cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed"
          >
            标记状态变化
          </button>
        )}
        <InputDialog
          open={stateDlg}
          title="标记状态变化"
          placeholder="这一刻他怎么变了？（一句话）"
          confirmText="记下"
          onClose={() => setStateDlg(false)}
          onConfirm={async (summary) => {
            const text = String(summary || '').trim()
            if (!text) return
            setStateBusy(true)
            try {
              await withFeedback(
                api.addCharState({
                  character_id: node.id,
                  chapter: Number(sliceChapter || maxChapter || 1),
                  change_type: 'state',
                  summary: text,
                }),
                { ok: '状态已标记', fail: '标记失败' },
              )
            } catch { /* toast 已报 */ }
            finally { setStateBusy(false) }
          }}
        />
        {t === 'character' && expandId && (
          <button
            type="button"
            data-testid="atlas-expand-center"
            onClick={() => onExpand?.(expandId)}
            className="inline-flex items-center justify-center gap-1.5 h-8 rounded-lg border border-line text-f13 text-ink hover:border-brand cursor-pointer"
          >
            <Crosshair size={13} /> 以此为中心展开
          </button>
        )}
        {t !== 'character' && (
          <button
            type="button"
            data-testid="atlas-expand-center"
            disabled={!expandId}
            onClick={() => expandId && onExpand?.(expandId)}
            className="inline-flex items-center justify-center gap-1.5 h-8 rounded-lg border border-line text-f13 text-ink hover:border-brand cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed"
          >
            <Crosshair size={13} />
            {t === 'proposition' ? '以知情人展开' : '以关联角色展开'}
          </button>
        )}
      </div>
    </div>
  )
}

function CharacterFacet({ node, focus, hop, nb, diff, arc, onHopBoost }) {
  const peerName = node.label || node.id
  return (
    <>
      {/* 弧光一行 */}
      <section data-testid="atlas-arc-line">
        <div className="text-meta text-faint uppercase tracking-wider mb-0.5">弧光</div>
        {arc?.loading && (
          <div className="text-faint inline-flex items-center gap-1"><Loader2 size={12} className="animate-spin" />加载…</div>
        )}
        {arc?.err && <div className="text-faint">{arc.err}</div>}
        {arc?.line && (
          <div className={arc.line.kind === 'cold' ? 'text-amber-800/90 bg-amber-500/10 rounded px-1.5 py-1' : 'text-ink'}>
            {arc.line.kind === 'ok' && ALIGN_ZH[arc.raw?.alignment?.status]
              ? `${ALIGN_ZH[arc.raw.alignment.status]} · ${arc.line.text}`
              : arc.line.text}
          </div>
        )}
      </section>

      {/* 与中心 */}
      <section>
        <div className="text-meta text-faint uppercase tracking-wider mb-0.5">与中心</div>
        {node.id === focus ? (
          <div className="text-faint">当前即为图中心</div>
        ) : (nb.sharedWithFocus || []).length === 0 ? (
          <div className="text-faint">子图内无直连</div>
        ) : (
          <ul className="space-y-0.5">
            {nb.sharedWithFocus.map((s, i) => (
              <li key={i} className="text-ink">{s.relLabel || edgeLabel(s.rel)}</li>
            ))}
          </ul>
        )}
      </section>

      {/* 知情差 */}
      {diff && (
        <section data-testid="atlas-knowledge-diff">
          <div className="text-meta text-faint uppercase tracking-wider mb-0.5">知情差（子图）</div>
          {diff.isSelfFocus ? (
            <div className="text-ink space-y-1">
              <div>本中心已知命题 {diff.selfKnowsCount} 条（子图内）</div>
              <ul className="space-y-0.5 text-faint">
                {(diff.focusKnownPreview || []).map((r) => (
                  <li key={r.id} className="truncate">{r.secret ? SECRET_PLACEHOLDER : r.label}</li>
                ))}
              </ul>
            </div>
          ) : (
            <div className="space-y-1.5">
              {(diff.onlyFocus || []).length > 0 && (
                <div>
                  <div className="text-faint">中心独知</div>
                  <ul className="space-y-0.5">
                    {diff.onlyFocus.map((r) => (
                      <li key={r.id} className="truncate text-ink">{r.label}</li>
                    ))}
                  </ul>
                </div>
              )}
              {(diff.onlySelf || []).length > 0 && (
                <div>
                  <div className="text-faint">{peerName} 独知（子图可见）</div>
                  <ul className="space-y-0.5">
                    {diff.onlySelf.map((r) => (
                      <li key={r.id} className="truncate text-ink">{r.label}</li>
                    ))}
                  </ul>
                  {diff.showHopBoost && (
                    <div className="text-meta text-faint mt-0.5">以下仅子图内可见，可能不全</div>
                  )}
                </div>
              )}
              {diff.showHopBoost && (
                <div data-testid="atlas-hop-boost-block" className="rounded bg-soft/80 px-2 py-1.5 space-y-1">
                  <p className="text-faint leading-snug">
                    当前 {hop} 跳子图无法保证看到「{peerName}」的全部独知命题（其独知内容常在 2 跳外）。
                  </p>
                  {/* 禁止假绿：不写「双方完全一致」 */}
                  <button
                    type="button"
                    data-testid="atlas-hop-boost"
                    onClick={() => onHopBoost?.(2)}
                    className="h-7 px-2 rounded-lg bg-brand/10 text-brand text-f12 font-medium hover:bg-brand/20 cursor-pointer"
                  >
                    升到 2 跳以查看对方知情
                  </button>
                </div>
              )}
              {!diff.showHopBoost && (diff.onlySelf || []).length === 0 && (diff.onlyFocus || []).length === 0 && (
                <div className="text-faint">
                  子图内可见范围内，双方知情差为空（仍非全书）。
                </div>
              )}
              <div className="text-meta text-faint/80">仅当前子图 · {hop} 跳内，非全书知情帧</div>
            </div>
          )}
        </section>
      )}

      {/* 关系邻域 */}
      <section>
        <div className="text-meta text-faint uppercase tracking-wider mb-0.5">关系邻域</div>
        {(nb.relEdges || []).length === 0 ? (
          <div className="text-faint">无非知情关系边</div>
        ) : (
          <ul className="space-y-0.5">
            {nb.relEdges.slice(0, 6).map((r, i) => (
              <li key={i} className="truncate text-ink">
                <span className="text-faint">{r.relLabel}</span>
                {' '}{r.peerLabel}
              </li>
            ))}
          </ul>
        )}
      </section>

      {/* 已知命题：正文反哺的「他知道什么」短摘要，不是设定库标题 */}
      {(nb.knowsOut || []).length > 0 && (
        <section data-testid="atlas-known-props">
          <div className="text-meta text-faint uppercase tracking-wider mb-0.5">他知道的事</div>
          <p className="text-meta text-faint/80 leading-snug mb-1">
            正文反哺抽取的知识摘要（图上截短显示）。完整句子请点「打开设定」。
          </p>
          <ul className="space-y-1">
            {nb.knowsOut.slice(0, 5).map((r) => {
              const main = r.secret
                ? SECRET_PLACEHOLDER
                : propositionListLabel({
                    label: r.peerLabel,
                    peerLabel: r.peerLabel,
                    peerId: r.peerId,
                    id: r.peerId,
                    secret: r.secret,
                    type: 'proposition',
                  })
              const tech = String(r.peerId || '')
              return (
                <li key={r.peerId} className="min-w-0">
                  <div className="text-ink leading-snug break-words">{main}</div>
                  {tech.startsWith('fact:') && !r.secret && (
                    <div className="text-meta text-faint/60 tnum truncate" title={tech}>
                      {humanizeFactId(tech)}
                    </div>
                  )}
                </li>
              )
            })}
          </ul>
        </section>
      )}
    </>
  )
}

function PropositionFacet({ node, nb }) {
  return (
    <>
      <section>
        <div className="text-meta text-faint uppercase tracking-wider mb-0.5">摘要</div>
        {node.secret ? (
          <div className="text-faint leading-relaxed">该命题为私密内容，图谱中不展示明文。全文请在设定库中按权限查看。</div>
        ) : (
          <div className="text-ink break-words">{node.label || node.id}</div>
        )}
      </section>
      <section>
        <div className="text-meta text-faint uppercase tracking-wider mb-0.5">谁知道</div>
        {(nb.knowsIn || []).length === 0 ? (
          <div className="text-faint">子图内无知情人</div>
        ) : (
          <ul className="space-y-0.5">
            {nb.knowsIn.slice(0, 8).map((r) => (
              <li key={r.peerId} className="truncate text-ink">{r.peerLabel}</li>
            ))}
          </ul>
        )}
      </section>
    </>
  )
}

function EntityFacet({ type, nb }) {
  const relWant = type === 'faction' ? 'member' : 'held_by'
  const rows = (nb.relEdges || []).filter((r) => r.rel === relWant)
  return (
    <section>
      <div className="text-meta text-faint uppercase tracking-wider mb-0.5">
        {type === 'faction' ? '成员' : '持有者'}
      </div>
      {rows.length === 0 ? (
        <div className="text-faint">子图内无关联角色边</div>
      ) : (
        <ul className="space-y-0.5">
          {rows.slice(0, 8).map((r, i) => (
            <li key={i} className="truncate text-ink">{r.peerLabel}</li>
          ))}
        </ul>
      )}
      {(nb.relEdges || []).filter((r) => r.rel !== relWant).length > 0 && (
        <div className="mt-2">
          <div className="text-meta text-faint mb-0.5">其它边</div>
          <ul className="space-y-0.5">
            {nb.relEdges.filter((r) => r.rel !== relWant).slice(0, 4).map((r, i) => (
              <li key={i} className="truncate"><span className="text-faint">{r.relLabel}</span> {r.peerLabel}</li>
            ))}
          </ul>
        </div>
      )}
    </section>
  )
}

export default NodeDetail
